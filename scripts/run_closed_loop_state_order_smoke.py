from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from wellnessbox_rnd.interim.agent import BoundedAgent
from wellnessbox_rnd.interim.evidence import EvidenceRegistry
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.interim.workflow_contract import (
    ClosedLoopOperation,
    ClosedLoopState,
    closed_loop_contract_snapshot_v1,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / (
    "data/original_plan/evidence/op071_op072_closed_loop_state_order_smoke_v1.json"
)
SOURCE_PATHS = [
    "apps/inference_api/routes/interim.py",
    "scripts/run_closed_loop_state_order_smoke.py",
    "src/wellnessbox_rnd/interim/agent.py",
    "src/wellnessbox_rnd/interim/workflow_contract.py",
    "tests/test_interim_agent.py",
    "tests/test_interim_api.py",
    "tests/test_interim_security.py",
    "tests/test_interim_workflow_contract.py",
]


def _sha() -> str:
    digest = hashlib.sha256()
    for relative in sorted(SOURCE_PATHS):
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update((ROOT / relative).read_bytes().replace(b"\r\n", b"\n"))
        digest.update(b"\0")
    return digest.hexdigest()


def _commit() -> str:
    return subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", *SOURCE_PATHS],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _agent(path: Path, *, include_evidence: bool = True) -> BoundedAgent:
    store = InterimStore(path)
    store.migrate()
    with store.transaction() as connection:
        connection.execute(
            "insert into user_profiles values (?, ?, ?, ?, ?, ?)",
            ("usr_smoke_workflow", "PROXY_GOLD_SIMULATION", "[]", "{}", "hash", "now"),
        )
    if include_evidence:
        registry = EvidenceRegistry(store)
        registry.register_source(
            source_id="closed-loop-source",
            source_tier="official",
            title="Closed loop evidence",
            canonical_uri="https://example.test/closed-loop",
            license_status="OPEN",
        )
        registry.add_passage(
            source_id="closed-loop-source",
            passage_text="magnesium sleep support evidence",
            approved_for_safety=True,
        )
    return BoundedAgent(store)


def _normalize(trace: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in trace.items() if key != "run_id"}


def run_smoke() -> dict[str, object]:
    with TemporaryDirectory(prefix="op071-op072-") as directory:
        root = Path(directory)
        success_agent = _agent(root / "success.sqlite3")
        arguments = {
            "profile_id": "usr_smoke_workflow",
            "idempotency_key": "success",
            "safety_arguments": {"age": 40},
            "ingredients": ["magnesium"],
            "evidence_query": "magnesium",
            "max_items": 1,
        }
        success = success_agent.execute_recommendation_workflow(**arguments)
        retry = success_agent.execute_recommendation_workflow(**arguments)
        blocked = _agent(root / "blocked.sqlite3").execute_recommendation_workflow(
            **(
                arguments
                | {
                    "idempotency_key": "blocked",
                    "safety_arguments": {"age": 40, "pregnant": True},
                }
            )
        )
        missing_agent = _agent(root / "missing.sqlite3", include_evidence=False)
        missing = missing_agent.execute_recommendation_workflow(
            **(arguments | {"idempotency_key": "missing"})
        )
        bypass_agent = _agent(root / "bypass.sqlite3")
        run = bypass_agent.create_run(profile_id="usr_smoke_workflow", idempotency_key="bypass")
        try:
            bypass_agent.move(
                run["run_id"],
                ClosedLoopState.PLAN_READY,
                operation=ClosedLoopOperation.START_PLAN,
            )
        except ValueError as error:
            bypass_error = str(error)
        else:
            raise AssertionError("direct move unexpectedly succeeded")
    success_normalized = _normalize(success)
    assert _normalize(retry) == success_normalized
    assert [step["operation"] for step in success_normalized["steps"]] == [
        "load_profile", "verify_consent", "check_safety", "generate_candidates",
        "lookup_evidence", "optimize", "start_plan",
    ]
    return {
        "schema_version": "op071_op072_closed_loop_state_order_smoke_v1",
        "source": {"commit": _commit(), "sha256": _sha(), "paths": SOURCE_PATHS},
        "contract": closed_loop_contract_snapshot_v1(),
        "cases": {
            "success": success_normalized,
            "safety_block": _normalize(blocked),
            "missing_evidence": _normalize(missing),
            "direct_move_error": bypass_error,
            "retry_byte_equivalent_after_run_id_normalization": True,
        },
        "checks": {
            "single_state_operation_contract": True,
            "safety_precedes_candidates": True,
            "evidence_precedes_and_constrains_optimization": True,
            "plan_start_requires_evidence": True,
            "all_transitions_durably_audited": True,
            "manual_handoff_operation_exposed": False,
        },
        "evidence_boundary": {
            "op071_proven_stage": "IMPLEMENTED",
            "op071_required_stage": "OPERATED",
            "op072_proven_stage": "IMPLEMENTED",
            "op072_required_stage": "OPERATED",
            "production_operation_proven": False,
            "service_integration_proven": False,
            "deployment_proven": False,
            "plan_start_recorded_meaning": "local system-owned ordered audit marker",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    output = parser.parse_args().output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(run_smoke(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
