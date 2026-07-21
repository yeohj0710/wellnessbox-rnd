import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from apps.inference_api.main import app
from wellnessbox_rnd.interim.bootstrap import (
    ORIGINAL_PLAN_PAGE_26_URI,
    bootstrap_operational_evidence,
)
from wellnessbox_rnd.interim.evidence import EvidenceRegistry
from wellnessbox_rnd.interim.importer import register_retrained_package
from wellnessbox_rnd.interim.jobs import WorkflowJobQueue
from wellnessbox_rnd.interim.store import InterimStore

RETRAINED_PACKAGE_ROOT = Path("artifacts/tips/interim/retrained")


def _counseling_payload() -> dict[str, object]:
    return {
        "schema_version": "counseling_turn_request_v1",
        "service_session_id": "chat-session-op087",
        "turn_id": "turn-op087-1",
        "profile_id": "usr_1234567890abcdef",
        "query": "What should counseling say about glucosamine with warfarin?",
        "answered_at": "2026-07-21T12:00:00Z",
        "profile": {"age": 41, "goals": ["bone_joint"]},
        "consent_scopes": ["counseling:write", "recommendation:write"],
        "goals": ["bone_joint"],
        "ingredients": ["glucosamine"],
        "safety": {},
    }


def _headers() -> dict[str, str]:
    return {"x-wb-rnd-token": "test-token"}


def _seed_lifecycle_api_store(database: Path) -> None:
    store = InterimStore(database)
    store.migrate()
    now = datetime(2026, 7, 21, 12, 0, tzinfo=UTC).isoformat()
    with store.transaction() as connection:
        connection.execute(
            "insert into user_profiles values "
            "('usr_1234567890abcdef', 'PROXY_GOLD_SIMULATION', '[]', '{}', 'p', ?)",
            (now,),
        )
        connection.execute(
            "insert into consent_snapshots values "
            "('consent_lifecycle_api', 'usr_1234567890abcdef', 1, 'v1', '{}', 'c', ?)",
            (now,),
        )
        connection.execute(
            "insert into active_profile_consents values "
            "('usr_1234567890abcdef', 'consent_lifecycle_api', ?)",
            (now,),
        )
        connection.execute(
            "insert into executions values "
            "('execution_lifecycle_api', 'request_lifecycle_api', "
            "'usr_1234567890abcdef', null, 'consent_lifecycle_api', 'r', "
            "'COMPLETE', ?, ?)",
            (now, now),
        )
        connection.execute(
            """
            insert into execution_events(
              event_id, execution_id, consent_snapshot_id, event_index, event_type,
              source, idempotency_key, payload_json, payload_sha256,
              effective_payload_sha256, created_at
            ) values ('event_lifecycle_api_seed', 'execution_lifecycle_api',
              'consent_lifecycle_api', 0, 'recommendation', 'system', 'seed',
              '{"plan_id":"plan_lifecycle_api"}', 'seed', 'seed', ?)
            """,
            (now,),
        )


def test_plan_lifecycle_api_persists_transition_and_rejects_order_fields(
    tmp_path, monkeypatch
) -> None:
    database = tmp_path / "lifecycle-api.sqlite3"
    _seed_lifecycle_api_store(database)
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    client = TestClient(app)
    payload = {
        "execution_id": "execution_lifecycle_api",
        "profile_id": "usr_1234567890abcdef",
        "plan_id": "plan_lifecycle_api",
        "expected_state": "ACTIVE",
        "action": "monitor",
        "reason_code": "TEST_MONITOR",
        "idempotency_key": "api-monitor",
        "occurred_at": "2026-07-21T12:00:00Z",
    }

    response = client.post(
        "/v1/interim/plan-lifecycle/transitions", headers=_headers(), json=payload
    )
    forbidden = client.post(
        "/v1/interim/plan-lifecycle/transitions",
        headers=_headers(),
        json=payload | {"idempotency_key": "api-order", "order_status": "PAID"},
    )

    assert response.status_code == 200
    assert response.json()["state_after"] == "MONITORING"
    assert response.json()["order_state_effect"] == "NONE"
    assert forbidden.status_code == 422
    assert InterimStore(database).scalar(
        "select count(*) from execution_events where event_type='followup_evaluation'"
    ) == 1


def test_counseling_turn_binds_verified_answer_and_recommendation_to_one_session(
    tmp_path, monkeypatch
) -> None:
    database = tmp_path / "counseling.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    InterimStore(database).migrate()
    monkeypatch.setattr(
        "apps.inference_api.routes.interim.recommend_with_registered_model",
        lambda *_args, **_kwargs: SimpleNamespace(
            ingredients=("glucosamine",),
            scores=(0.91,),
            evidence_ids=("EV-OP087",),
            model_id=None,
        ),
    )
    client = TestClient(app)

    first = client.post(
        "/v1/interim/counseling/turns", headers=_headers(), json=_counseling_payload()
    )
    second = client.post(
        "/v1/interim/counseling/turns", headers=_headers(), json=_counseling_payload()
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    body = first.json()
    repeated = second.json()
    assert body["service_session_id"] == "chat-session-op087"
    assert body["verification"]["passed"] is True
    assert body["recommendation_execution"]["run_id"]
    assert repeated["agent_run_id"] == body["agent_run_id"]
    assert repeated["recommendation_execution"] == body["recommendation_execution"]
    assert repeated["deduplicated"] is True
    store = InterimStore(database)
    assert store.scalar("select count(*) from agent_runs") == 1
    assert store.scalar("select count(*) from agent_steps") == 1
    assert store.scalar("select count(*) from recommendation_runs") == 1
    binding_row = store.rows(
        "select binding_json, binding_sha256 from agent_steps where tool_name='counseling_answer'"
    )[0]
    binding = json.loads(str(binding_row["binding_json"]))
    assert binding["service_session_id"] == "chat-session-op087"
    assert binding["turn_id"] == "turn-op087-1"
    assert binding["recommendation_run_id"] == body["recommendation_execution"]["run_id"]
    assert binding_row["binding_sha256"] == body["session_binding_sha256"]


def test_counseling_turn_rejects_changed_payload_for_existing_turn(
    tmp_path, monkeypatch
) -> None:
    database = tmp_path / "counseling-conflict.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    monkeypatch.setattr(
        "apps.inference_api.routes.interim.recommend_with_registered_model",
        lambda *_args, **_kwargs: SimpleNamespace(
            ingredients=("glucosamine",),
            scores=(0.91,),
            evidence_ids=("EV-OP087",),
            model_id=None,
        ),
    )
    client = TestClient(app)
    first = client.post(
        "/v1/interim/counseling/turns", headers=_headers(), json=_counseling_payload()
    )
    changed = _counseling_payload() | {"safety": {"pregnant": True}}
    conflict = client.post(
        "/v1/interim/counseling/turns", headers=_headers(), json=changed
    )
    assert first.status_code == 200
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == "counseling_turn_payload_conflict"
    stored_profile = json.loads(
        str(InterimStore(database).scalar("select payload_json from user_profiles"))
    )
    assert "pregnant" not in stored_profile


def test_counseling_turn_concurrent_retry_creates_one_recommendation(
    tmp_path, monkeypatch
) -> None:
    database = tmp_path / "counseling-concurrent.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    InterimStore(database).migrate()
    monkeypatch.setattr(
        "apps.inference_api.routes.interim.recommend_with_registered_model",
        lambda *_args, **_kwargs: SimpleNamespace(
            ingredients=("glucosamine",),
            scores=(0.91,),
            evidence_ids=("EV-OP087",),
            model_id=None,
        ),
    )

    def request_once() -> int:
        return TestClient(app).post(
            "/v1/interim/counseling/turns",
            headers=_headers(),
            json=_counseling_payload(),
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _index: request_once(), range(2)))
    assert statuses == [200, 200]
    assert InterimStore(database).scalar("select count(*) from recommendation_runs") == 1


def test_counseling_turn_requires_internal_token(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    response = TestClient(app).post(
        "/v1/interim/counseling/turns", json=_counseling_payload()
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "constraints",
    [
        {"max_total_cost_krw": True, "max_products": 2},
        {"max_total_cost_krw": 50_000.5, "max_products": 2},
        {"max_total_cost_krw": -1, "max_products": 2},
        {"max_total_cost_krw": 50_000, "max_products": 0},
        {"max_total_cost_krw": 50_000, "max_products": 21},
        {"max_total_cost_krw": 50_000, "max_products": 2, "extra": 1},
    ],
)
def test_interim_recommendation_rejects_invalid_product_constraints(
    constraints, monkeypatch
) -> None:
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    response = TestClient(app).post(
        "/v1/interim/recommendations",
        headers=_headers(),
        json={
            "profile_id": "usr_1234567890abcdef",
            "product_constraints": constraints,
        },
    )

    assert response.status_code == 422


def test_interim_recommendation_emits_validated_product_constraints(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(tmp_path / "api.sqlite3"))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    monkeypatch.setattr(
        "apps.inference_api.routes.interim.recommend_with_registered_model",
        lambda *_args, **_kwargs: SimpleNamespace(
            ingredients=("magnesium",),
            scores=(0.91,),
            evidence_ids=("EV-OP065",),
            model_id=None,
        ),
    )
    client = TestClient(app)
    profile_id = "usr_1234567890abcdef"
    assert (
        client.post(
            "/v1/interim/profiles",
            headers=_headers(),
            json={
                "profile_id": profile_id,
                "consent_scopes": ["recommendation:read"],
                "profile": {"age": 41},
            },
        ).status_code
        == 200
    )

    response = client.post(
        "/v1/interim/recommendations",
        headers=_headers(),
        json={
            "profile_id": profile_id,
            "goals": ["sleep"],
            "ingredients": ["magnesium"],
            "safety": {"age": 41},
            "product_constraints": {
                "max_total_cost_krw": 42_000,
                "max_products": 2,
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["product_optimization_constraints"] == {
        "schema_version": "product_optimization_constraints_v1",
        "max_total_cost_krw": 42_000,
        "max_products": 2,
        "excluded_ingredient_keys": [],
        "safety_rule_ids": [],
    }


def test_interim_api_blocks_emergency_before_registered_model(tmp_path, monkeypatch) -> None:
    database = tmp_path / "api.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    monkeypatch.setattr(
        "apps.inference_api.routes.interim.recommend_with_registered_model",
        lambda *_args, **_kwargs: pytest.fail("model must not run before emergency block"),
    )
    client = TestClient(app)
    profile_id = "usr_1234567890abcdef"
    profile = client.post(
        "/v1/interim/profiles",
        headers=_headers(),
        json={
            "profile_id": profile_id,
            "consent_scopes": ["recommendation:read"],
            "profile": {"age": 52, "symptoms": []},
        },
    )
    assert profile.status_code == 200

    response = client.post(
        "/v1/interim/recommendations",
        headers=_headers(),
        json={
            "profile_id": profile_id,
            "goals": ["heart_health"],
            "ingredients": [],
            "safety": {"symptoms": ["chest pain"]},
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "BLOCKED"
    assert body["safety_action"] == "STOP_AND_ESCALATE"
    assert body["model_id"] is None
    assert body["recommendations"] == []
    assert any(finding["rule_id"] == "SAFE-EMERGENCY-001" for finding in body["findings"])


def test_current_safety_input_cannot_remove_stored_high_risk_facts(tmp_path, monkeypatch) -> None:
    database = tmp_path / "api.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    monkeypatch.setattr(
        "apps.inference_api.routes.interim.recommend_with_registered_model",
        lambda *_args, **_kwargs: pytest.fail("model must not run after stored risk block"),
    )
    client = TestClient(app)
    profile_id = "usr_abcdef1234567890"
    profile = client.post(
        "/v1/interim/profiles",
        headers=_headers(),
        json={
            "profile_id": profile_id,
            "consent_scopes": ["recommendation:read"],
            "profile": {
                "age": 41,
                "pregnant": True,
                "medications": [{"name": "warfarin"}],
                "symptoms": [],
            },
        },
    )
    assert profile.status_code == 200

    response = client.post(
        "/v1/interim/recommendations",
        headers=_headers(),
        json={
            "profile_id": profile_id,
            "goals": ["heart_health"],
            "ingredients": ["omega3"],
            "safety": {
                "pregnant": False,
                "medications": [],
                "symptoms": [],
            },
            "product_constraints": {
                "max_total_cost_krw": 35_000,
                "max_products": 3,
            },
        },
    )
    body = response.json()
    rule_ids = {finding["rule_id"] for finding in body["findings"]}

    assert response.status_code == 200
    assert body["status"] == "BLOCKED"
    assert body["recommendations"] == []
    assert {"SAFE-PREG-001", "SAFE-DDI-001"} <= rule_ids
    assert body["product_optimization_constraints"] == {
        "schema_version": "product_optimization_constraints_v1",
        "max_total_cost_krw": 35_000,
        "max_products": 3,
        "excluded_ingredient_keys": ["omega3"],
        "safety_rule_ids": ["SAFE-DDI-001", "SAFE-PREG-001"],
    }


def test_current_safety_input_cannot_remove_stored_dynamic_rule_predicate(
    tmp_path, monkeypatch
) -> None:
    database = tmp_path / "api.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    monkeypatch.setattr(
        "apps.inference_api.routes.interim.recommend_with_registered_model",
        lambda *_args, **_kwargs: pytest.fail("model must not run after dynamic rule block"),
    )
    store = InterimStore(database)
    store.migrate()
    bootstrap_operational_evidence(store)
    assert (
        store.scalar(
            "select canonical_uri from source_registry where source_id='tips-original-plan-p26'"
        )
        == ORIGINAL_PLAN_PAGE_26_URI
    )
    client = TestClient(app)
    profile_id = "usr_fedcba0987654321"
    profile = client.post(
        "/v1/interim/profiles",
        headers=_headers(),
        json={
            "profile_id": profile_id,
            "consent_scopes": ["recommendation:read"],
            "profile": {"age": 41, "hard_false_negative": True},
        },
    )
    assert profile.status_code == 200

    response = client.post(
        "/v1/interim/recommendations",
        headers=_headers(),
        json={
            "profile_id": profile_id,
            "goals": ["heart_health"],
            "ingredients": [],
            "safety": {"hard_false_negative": False},
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "BLOCKED"
    assert body["recommendations"] == []
    assert any(finding["rule_id"] == "SAFE-GATE-001" for finding in body["findings"])


def test_dynamic_rule_predicate_combines_risk_facts_across_sources(tmp_path, monkeypatch) -> None:
    database = tmp_path / "api.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    monkeypatch.setattr(
        "apps.inference_api.routes.interim.recommend_with_registered_model",
        lambda *_args, **_kwargs: pytest.fail("model must not run after split predicate block"),
    )
    store = InterimStore(database)
    store.migrate()
    bootstrap_operational_evidence(store)
    evidence_id = str(
        store.scalar(
            "select evidence_id from evidence_passages "
            "where approved_for_safety=1 order by evidence_id limit 1"
        )
    )
    EvidenceRegistry(store).activate_rule(
        rule_id="SAFE-SPLIT-RISK-001",
        version=1,
        severity="CRITICAL",
        action="BLOCK",
        predicate={"hard_false_negative": True, "above_ul": True},
        evidence_ids=[evidence_id],
        valid_from=datetime.now(UTC).isoformat(),
    )
    client = TestClient(app)
    profile_id = "usr_0011223344556677"
    profile = client.post(
        "/v1/interim/profiles",
        headers=_headers(),
        json={
            "profile_id": profile_id,
            "consent_scopes": ["recommendation:read"],
            "profile": {"age": 41, "hard_false_negative": True},
        },
    )
    assert profile.status_code == 200

    response = client.post(
        "/v1/interim/recommendations",
        headers=_headers(),
        json={
            "profile_id": profile_id,
            "goals": ["heart_health"],
            "ingredients": [],
            "safety": {"hard_false_negative": False, "above_ul": True},
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "BLOCKED"
    assert body["model_id"] is None
    assert body["recommendations"] == []
    assert any(finding["rule_id"] == "SAFE-SPLIT-RISK-001" for finding in body["findings"])


@pytest.mark.skipif(
    not RETRAINED_PACKAGE_ROOT.is_dir(),
    reason="ignored local retrained package artifacts/tips/interim/retrained is absent",
)
def test_interim_api_requires_token_and_runs_recommendation(tmp_path, monkeypatch) -> None:
    database = tmp_path / "api.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    client = TestClient(app)

    assert client.get("/v1/interim/status").status_code == 401
    status = client.get("/v1/interim/status", headers=_headers())
    assert status.status_code == 200
    assert status.json()["mode"] == "PROXY_GOLD_SIMULATION"
    register_retrained_package(
        InterimStore(database),
        Path("artifacts/tips/interim/retrained"),
        code_commit="test",
        rollback_model_id=None,
    )

    profile_id = "usr_" + hashlib.sha256(b"user-1").hexdigest()[:16]
    profile = client.post(
        "/v1/interim/profiles",
        headers=_headers(),
        json={
            "profile_id": profile_id,
            "consent_scopes": ["followup:write"],
            "profile": {"age": 41},
        },
    )
    assert profile.status_code == 200

    response = client.post(
        "/v1/interim/recommendations",
        headers=_headers(),
        json={
            "profile_id": profile_id,
            "goals": ["sleep"],
            "ingredients": ["magnesium", "theanine"],
            "safety": {"age": 41},
        },
    )
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "READY"
    assert body["simulation"] is True
    assert body["model_id"].startswith("proxy-recommendation-")
    assert len(body["recommendations"]) >= 1


def test_ordered_agent_workflow_endpoint_enforces_safety_to_plan_sequence(
    tmp_path, monkeypatch
) -> None:
    database = tmp_path / "ordered-workflow-api.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    client = TestClient(app)
    profile_id = "usr_1234567890abcdef"
    assert (
        client.post(
            "/v1/interim/profiles",
            headers=_headers(),
            json={"profile_id": profile_id, "consent_scopes": [], "profile": {"age": 41}},
        ).status_code
        == 200
    )
    registry = EvidenceRegistry(InterimStore(database))
    registry.register_source(
        source_id="workflow-api-source",
        source_tier="official",
        title="Workflow API source",
        canonical_uri="https://example.test/workflow-api",
        license_status="OPEN",
    )
    registry.add_passage(
        source_id="workflow-api-source",
        passage_text="magnesium sleep support evidence",
        approved_for_safety=True,
    )

    response = client.post(
        "/v1/interim/agent/workflow",
        headers=_headers(),
        json={
            "profile_id": profile_id,
            "idempotency_key": "api-ordered-workflow",
            "safety": {"age": 41, "ingredients": ["magnesium"]},
            "ingredients": ["magnesium"],
            "evidence_query": "magnesium",
            "max_items": 1,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PLAN_READY"
    assert body["plan_start_recorded"] is True
    assert [step["operation"] for step in body["steps"]][-5:] == [
        "check_safety",
        "generate_candidates",
        "lookup_evidence",
        "optimize",
        "start_plan",
    ]


def test_serious_ae_flow_creates_review_and_review_decision_is_immutable(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(tmp_path / "api.sqlite3"))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    client = TestClient(app)
    profile_id = "usr_1234567890abcdef"
    client.post(
        "/v1/interim/profiles",
        headers=_headers(),
        json={"profile_id": profile_id, "consent_scopes": ["ae:write"], "profile": {}},
    )
    run = client.post(
        "/v1/interim/agent/runs",
        headers=_headers(),
        params={"profile_id": profile_id, "idempotency_key": "ae-run"},
    ).json()
    store = InterimStore(tmp_path / "api.sqlite3")
    with store.transaction() as connection:
        connection.execute(
            "update agent_runs set state_after='FOLLOWUP_ACTIVE' where run_id=?",
            (run["run_id"],),
        )
        connection.execute(
            "insert into consent_snapshots values "
            "('consent_ae_api', ?, 1, 'v1', '{}', 'consent-ae-api', 'now')",
            (profile_id,),
        )
        connection.execute(
            "insert into executions values "
            "('execution_ae_api', 'request_ae_api', ?, null, 'consent_ae_api', "
            "'request-ae-api', 'COMPLETE', 'now', 'now')",
            (profile_id,),
        )
        connection.execute(
            """
            insert into execution_events(
              event_id, execution_id, consent_snapshot_id, event_index, event_type,
              source, idempotency_key, payload_json, payload_sha256,
              effective_payload_sha256, created_at
            ) values (
              'event_ae_api', 'execution_ae_api', 'consent_ae_api', 0,
              'recommendation', 'system', 'plan', '{"plan_id":"plan_ae_api"}',
              'plan-ae-api', 'plan-ae-api', 'now'
            )
            """
        )
    event = client.post(
        "/v1/interim/agent/tools",
        headers=_headers(),
        json={
            "run_id": run["run_id"],
            "tool_name": "log_adverse_event",
            "arguments": {"profile_id": profile_id, "serious": True},
            "consent_scopes": ["ae:write"],
        },
    )
    assert event.status_code == 422
    response = client.post(
        "/v1/interim/agent/adverse-events",
        headers=_headers(),
        json={
            "case_id": "ae_api_serious",
            "run_id": run["run_id"],
            "profile_id": profile_id,
            "execution_id": "execution_ae_api",
            "plan_id": "plan_ae_api",
            "serious": True,
            "observed_at": "2026-07-21T12:00:00Z",
        },
    )
    assert response.status_code == 200
    result = response.json()
    held_recommendation = client.post(
        "/v1/interim/recommendations",
        headers=_headers(),
        json={"profile_id": profile_id, "goals": ["sleep"], "ingredients": []},
    )
    assert held_recommendation.status_code == 409
    assert held_recommendation.json()["detail"] == (
        "serious_adverse_event_recommendation_hold"
    )
    held_workflow = client.post(
        "/v1/interim/agent/workflow",
        headers=_headers(),
        json={
            "profile_id": profile_id,
            "idempotency_key": "held-workflow",
            "safety": {},
            "ingredients": ["magnesium"],
            "evidence_query": "sleep",
            "max_items": 1,
        },
    )
    assert held_workflow.status_code == 422
    assert held_workflow.json()["detail"] == "serious_adverse_event_recommendation_hold"
    review_id = result["review_id"]
    queue = client.get("/v1/interim/admin/reviews?pharmacy_id=1", headers=_headers()).json()
    assert queue["items"][0]["simulation_badge"] == 1
    first = client.post(
        f"/v1/interim/admin/reviews/{review_id}/decision",
        headers=_headers(),
        json={"decision": "acknowledged", "pharmacy_id": 1},
    )
    second = client.post(
        f"/v1/interim/admin/reviews/{review_id}/decision",
        headers=_headers(),
        json={"decision": "changed", "pharmacy_id": 1},
    )
    assert first.status_code == 200
    assert first.json()["postconditions"]["serious_hold_active"] is True
    assert first.json()["postconditions"]["plan_stop_recorded"] is True
    assert len(first.json()["completion_postcondition_sha256"]) == 64
    assert second.status_code == 409


def test_due_plan_cron_endpoint_enqueues_shared_reevaluation_job(tmp_path, monkeypatch) -> None:
    database = tmp_path / "cron-api.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    monkeypatch.setenv("WB_RND_ALLOW_CRON_AS_OF_OVERRIDE", "1")
    client = TestClient(app)
    profile_id = "usr_1234567890abcdef"
    client.post(
        "/v1/interim/profiles",
        headers=_headers(),
        json={"profile_id": profile_id, "consent_scopes": [], "profile": {}},
    )
    queue = WorkflowJobQueue(InterimStore(database))
    with queue.store.transaction() as connection:
        connection.execute(
            "insert into consent_snapshots values "
            "('consent_cron_api', ?, 1, 'v1', '{}', 'consent-cron-api', 'now')",
            (profile_id,),
        )
        connection.execute(
            "insert into executions values "
            "('execution_cron_api', 'request_cron_api', ?, null, "
            "'consent_cron_api', 'request-cron-api', 'COMPLETE', 'now', 'now')",
            (profile_id,),
        )
        connection.execute(
            """
            insert into execution_events(
              event_id, execution_id, consent_snapshot_id, event_index, event_type,
              source, idempotency_key, payload_json, payload_sha256,
              effective_payload_sha256, created_at
            ) values (
              'event_cron_api', 'execution_cron_api', 'consent_cron_api', 0,
              'recommendation', 'system', 'plan', '{"plan_id":"plan_cron_api"}',
              'plan-cron-api', 'plan-cron-api', 'now'
            )
            """
        )
    queue.schedule_followup_with_reminder(
        followup_id="fu_cron_api",
        profile_id=profile_id,
        plan_id="plan_cron_api",
        execution_id="execution_cron_api",
        due_at=datetime(2026, 7, 21, 12, 0, tzinfo=UTC),
        reminder_at=datetime(2026, 7, 20, 12, 0, tzinfo=UTC),
        requested_data=["PRO"],
        now=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
    )

    response = client.post(
        "/v1/interim/agent/cron/due-plans",
        headers=_headers(),
        json={"as_of": "2026-07-21T12:00:00Z"},
    )

    assert response.status_code == 200
    assert response.json()["created_job_count"] == 1
    assert response.json()["jobs"][0]["job_type"] == "PLAN_REEVALUATION"


def test_execution_event_api_connects_conversation_and_followup_to_recommendation(
    tmp_path, monkeypatch
) -> None:
    database = tmp_path / "execution-events.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    client = TestClient(app)
    payload = {
        "request_id": "execution-api-001",
        "source_profile": {
            "schema_version": "wellnessbox.chat.UserProfile.v1",
            "subject_id": "usr_1234567890abcdef1234567890abcdef",
            "profile": {
                "age": 39,
                "sex": "female",
                "goals": ["sleep"],
            },
        },
        "user_profile": {
            "age": 39,
            "biological_sex": "female",
            "pregnant": False,
        },
        "goals": ["sleep_support"],
        "symptoms": ["difficulty_falling_asleep"],
        "conditions": [],
        "medications": [],
        "current_supplements": [],
        "input_availability": {
            "survey": True,
            "nhis": False,
            "wearable": False,
            "cgm": False,
            "genetic": False,
        },
        "data_source_consents": {
            source: {
                "use_for_recommendation": source == "survey",
                "allow_persistent_storage": source == "survey",
            }
            for source in ("survey", "nhis", "wearable", "cgm", "genetic")
        },
    }

    recommendation = client.post("/v1/recommend", json=payload)
    execution_id = recommendation.json()["execution_id"]
    conversation = client.post(
        f"/v1/interim/executions/{execution_id}/events",
        headers=_headers(),
        json={
            "event_type": "conversation",
            "source": "survey",
            "idempotency_key": "turn-1",
            "payload": {"intent": "sleep_question"},
        },
    )
    followup = client.post(
        f"/v1/interim/executions/{execution_id}/events",
        headers=_headers(),
        json={
            "event_type": "followup_evaluation",
            "source": "survey",
            "idempotency_key": "week-2",
            "payload": {"timepoint_weeks": 2, "status": "received"},
        },
    )
    trace = client.get(
        f"/v1/interim/executions/{execution_id}",
        headers=_headers(),
    )

    assert recommendation.status_code == 200
    assert conversation.status_code == 200
    assert followup.status_code == 200
    assert trace.status_code == 200
    assert [event["event_type"] for event in trace.json()["events"]] == [
        "recommendation",
        "safety",
        "optimization",
        "conversation",
        "followup_evaluation",
    ]
    assert {event["execution_id"] for event in trace.json()["events"]} == {execution_id}
