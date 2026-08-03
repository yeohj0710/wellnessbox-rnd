"""The integrity audit has to separate documenting a fault from committing one.

A module that warns about `safety_rules.json` in its docstring is not reading it.
A module that assigns the path to a constant is. Raw-text matching calls both a
read, which would flag the audit's own explanation as the thing it forbids.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import wellnessbox_rnd.evals.answer_key_integrity as integrity_module
from scripts import run_answer_key_workbench as workbench_cli
from scripts import seal_reference_standard as reference_seal_cli
from scripts.audit_answer_key_integrity import drafter_source_index
from wellnessbox_rnd.evals.adaptive_answer_key_review import (
    PRIMARY_AI_DRAFT_SOURCE,
)
from wellnessbox_rnd.evals.answer_key_integrity import (
    audit_declared_blinding,
    audit_drafter_source,
    audit_repository,
    audit_review_effort,
    load_registry,
    read_path_string_literals,
    sealing_readiness,
)
from wellnessbox_rnd.evals.answer_key_workbench import (
    CaseDraft,
    Workbench,
    build_provenance,
    decide,
    save_workbench,
    summarise_adjudication,
)
from wellnessbox_rnd.evals.blinded_drafters import (
    DRAFT_SOURCE_KPI4 as BLINDED_KPI4_DRAFT_SOURCE,
)
from wellnessbox_rnd.evals.reference_corpus_drafters import (
    DRAFT_SOURCE as REFERENCE_DRAFT_SOURCE,
)
from wellnessbox_rnd.evals.reference_standard import (
    load_contract,
    seal_reference_standard,
)

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "src/wellnessbox_rnd/evals"
REGISTRY = ROOT / "data/original_plan/contracts/engine_input_registry_v1.json"

pytestmark = pytest.mark.skipif(
    not REGISTRY.is_file(),
    reason="engine input registry not built; run scripts/build_engine_input_registry.py",
)


def test_registry_marks_the_engine_rule_file_as_engine_logic() -> None:
    registry = load_registry(ROOT)
    roles = {entry["path"]: entry["role"] for entry in registry["entries"]}
    assert roles["data/rules/safety_rules.json"] == "engine_logic"
    assert roles["data/catalog/ingredients.json"] == "vocabulary"


def test_docstring_mentions_are_not_counted_as_reads(tmp_path: Path) -> None:
    module = tmp_path / "documents_only.py"
    module.write_text(
        '"""This module explains that data/rules/safety_rules.json is off limits."""\n'
        "VALUE = 1\n",
        encoding="utf-8",
    )
    assert not any("safety_rules" in item for item in read_path_string_literals(module))
    assert audit_drafter_source([module], load_registry(ROOT))["verdict"] == "PASS"


def test_declaration_only_constants_are_not_counted_as_reads(tmp_path: Path) -> None:
    module = tmp_path / "declares_engine_path.py"
    module.write_text(
        'BLINDED_FROM = ("data/rules/safety_rules.json",)\n',
        encoding="utf-8",
    )
    result = audit_drafter_source([module], load_registry(ROOT))
    assert result["verdict"] == "PASS"
    assert result["reads_engine_logic"] == []


def test_declared_blinded_paths_are_violations_when_actually_read(
    tmp_path: Path,
) -> None:
    module = tmp_path / "reads_declared_paths.py"
    module.write_text(
        'from pathlib import Path\n'
        'BLINDED_FROM = ("data/rules/safety_rules.json",)\n'
        "CONTENTS = [Path(path).read_text() for path in BLINDED_FROM]\n",
        encoding="utf-8",
    )
    result = audit_drafter_source([module], load_registry(ROOT))
    assert result["verdict"] == "FAIL"
    assert result["reads_engine_logic"] == ["data/rules/safety_rules.json"]


def test_function_argument_shadows_same_named_module_path(tmp_path: Path) -> None:
    module = tmp_path / "argument_shadow.py"
    module.write_text(
        'path = "data/rules/safety_rules.json"\n'
        "def read_supplied_path(path):\n"
        "    return path.read_text()\n",
        encoding="utf-8",
    )
    result = audit_drafter_source([module], load_registry(ROOT))
    assert result["verdict"] == "PASS"


def test_builtin_open_is_counted_as_a_read(tmp_path: Path) -> None:
    module = tmp_path / "reads_engine.py"
    module.write_text(
        'RULES = "data/rules/safety_rules.json"\n'
        "with open(RULES, encoding='utf-8') as handle:\n"
        "    DATA = handle.read()\n",
        encoding="utf-8",
    )
    result = audit_drafter_source([module], load_registry(ROOT))
    assert result["verdict"] == "FAIL"
    assert "data/rules/safety_rules.json" in result["reads_engine_logic"]


def test_path_join_spelling_is_counted_as_a_read(tmp_path: Path) -> None:
    """`repo_root() / "data" / "rules" / "safety_rules.json"` must not slip past."""
    module = tmp_path / "joins_path.py"
    module.write_text(
        'from pathlib import Path\n'
        'PATH = Path("x") / "data" / "rules" / "safety_rules.json"\n'
        'DATA = PATH.read_text(encoding="utf-8")\n',
        encoding="utf-8",
    )
    assert audit_drafter_source([module], load_registry(ROOT))["verdict"] == "FAIL"


def test_reference_corpus_drafter_is_independent() -> None:
    module = EVALS / "reference_corpus_drafters.py"
    result = audit_drafter_source([module], load_registry(ROOT))
    assert result["verdict"] == "PASS"
    assert result["reads_engine_logic"] == []


def test_blinded_drafter_declarations_are_not_reads() -> None:
    module = EVALS / "blinded_drafters.py"
    result = audit_drafter_source([module], load_registry(ROOT))
    assert result["verdict"] == "PASS"
    assert result["reads_engine_logic"] == []


def test_drafter_source_index_is_indicator_specific() -> None:
    index = drafter_source_index()
    kpi4 = {
        path.name for path in index[("KPI-4", BLINDED_KPI4_DRAFT_SOURCE)]
    }
    kpi5 = {
        path.name for path in index[("KPI-5", REFERENCE_DRAFT_SOURCE)]
    }
    assert kpi4 == {"blinded_drafters.py"}
    assert kpi5 == {"reference_corpus_drafters.py"}


def test_blind_primary_ai_source_maps_to_its_import_module() -> None:
    index = drafter_source_index()
    for indicator_id in ("KPI-3", "KPI-4"):
        modules = {
            path.name
            for path in index[(indicator_id, PRIMARY_AI_DRAFT_SOURCE)]
        }
        assert modules == {"adaptive_answer_key_review.py"}
    result = audit_drafter_source(
        [EVALS / "adaptive_answer_key_review.py"],
        load_registry(ROOT),
    )
    assert result["verdict"] == "PASS"


def test_shared_corpus_sources_still_name_the_drafter_module() -> None:
    assert REFERENCE_DRAFT_SOURCE.endswith("@reference_corpus_drafters")
    assert BLINDED_KPI4_DRAFT_SOURCE.endswith("@blinded_drafters")
    assert REFERENCE_DRAFT_SOURCE != BLINDED_KPI4_DRAFT_SOURCE


def test_priors_drafter_is_not_independent() -> None:
    """Recorded so the finding stays visible if the module is edited later."""
    module = EVALS / "answer_key_drafters.py"
    result = audit_drafter_source([module], load_registry(ROOT))
    assert result["verdict"] == "FAIL"
    assert "data/rules/safety_rules.json" in result["reads_engine_logic"]


def test_impossibly_fast_review_fails() -> None:
    workbench = {
        "decisions": {
            f"case-{index:03}": {
                "action": "accepted",
                "decided_at": f"2026-07-31T08:20:{21 + index * 0.04:06.3f}Z".replace(
                    "T08:20:2", "T08:20:2"
                ),
            }
            for index in range(10)
        }
    }
    # Rebuild with real spacing: ten decisions inside half a second.
    for index, key in enumerate(workbench["decisions"]):
        workbench["decisions"][key]["decided_at"] = (
            f"2026-07-31T08:20:{21 + index * 0.04:06.3f}Z"
        )
    result = audit_review_effort(workbench)
    assert result["verdict"] == "FAIL"
    assert result["seconds_per_decision"] < 1.0


def test_paced_review_passes() -> None:
    workbench = {
        "decisions": {
            f"case-{index:03}": {
                "action": "accepted",
                "decided_at": f"2026-07-31T08:{20 + index}:00Z",
            }
            for index in range(5)
        }
    }
    assert audit_review_effort(workbench)["verdict"] == "PASS"


def test_review_with_too_few_decisions_is_not_failed() -> None:
    assert audit_review_effort({"decisions": {}})["verdict"] == "PASS"


def test_declared_blinding_requires_every_engine_logic_path() -> None:
    registry = {
        "entries": [
            {"path": "engine/policy.json", "role": "engine_logic"},
            {"path": "engine/safety.json", "role": "engine_logic"},
            {"path": "catalog.json", "role": "vocabulary"},
        ]
    }
    workbench = {
        "drafts": [
            {
                "case_id": "case-1",
                "blinded_from": ["engine/policy.json"],
            }
        ]
    }

    result = audit_declared_blinding(workbench, registry)

    assert result["verdict"] == "FAIL"
    assert result["missing_engine_logic"] == ["engine/safety.json"]


def test_recorded_durations_audit_detailed_review_but_not_batch_approval() -> None:
    workbench = {
        "decisions": {
            "detail-1": {
                "action": "accepted",
                "reviewed_in_detail": True,
                "review_duration_seconds": 2.0,
            },
            "batch-1": {
                "action": "accepted",
                "reviewed_in_detail": False,
                "decision_mode": "ai_consensus_batch_approval",
            },
        }
    }

    result = audit_review_effort(workbench)

    assert result["verdict"] == "PASS"
    assert result["detailed_decision_count"] == 1
    assert result["batch_approved_count"] == 1
    assert result["seconds_per_decision"] == 2.0


def test_pseudonymous_reviewer_without_identity_reference_fails() -> None:
    result = audit_review_effort(
        {
            "decisions": {
                "case-1": {
                    "action": "accepted",
                    "decided_by": "비식별 검토자",
                    "review_duration_seconds": 2.0,
                }
            }
        }
    )

    assert result["verdict"] == "FAIL"
    assert result["untraceable_reviewer_identity_count"] == 1


def test_pseudonymous_reviewer_with_identity_reference_passes() -> None:
    result = audit_review_effort(
        {
            "decisions": {
                "case-1": {
                    "action": "accepted",
                    "decided_by": "비식별 검토자",
                    "reviewer_identity_ref": "sha256:" + "a" * 64,
                    "review_duration_seconds": 2.0,
                }
            }
        }
    )

    assert result["verdict"] == "PASS"


def test_nonfinite_recorded_duration_fails_closed() -> None:
    result = audit_review_effort(
        {
            "decisions": {
                "case-1": {
                    "action": "accepted",
                    "reviewed_in_detail": True,
                    "review_duration_seconds": float("nan"),
                }
            }
        }
    )

    assert result["verdict"] == "FAIL"
    assert "유한한 0 이상 숫자" in result["reason"]


def test_repository_audit_passes_all_current_draft_sources() -> None:
    report = audit_repository(ROOT)

    assert report["status"] == "BLOCKED"
    assert {
        item["indicator_id"]: item["source_independence"]["verdict"]
        for item in report["indicators"]
    } == {"KPI-1": "PASS", "KPI-3": "PASS", "KPI-4": "PASS", "KPI-5": "PASS"}


def test_repository_completion_rejects_tampered_seal_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_path = (
        tmp_path
        / "data/original_plan/contracts/engine_input_registry_v1.json"
    )
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(
        json.dumps(
            {
                "entries": [
                    {"path": "engine/policy.json", "role": "engine_logic"}
                ]
            }
        ),
        encoding="utf-8",
    )
    drafter_module = tmp_path / "independent_drafter.py"
    drafter_module.write_text("VALUE = 1\n", encoding="utf-8")
    monkeypatch.setattr(
        integrity_module,
        "drafter_source_index",
        lambda _root: {("KPI-1", "independent"): {drafter_module}},
    )
    workbench = Workbench(
        "KPI-1",
        [
            CaseDraft(
                case_id=f"case-{index:03}",
                prompt=f"질문 {index}",
                draft_answer=["omega3"],
                draft_source="independent",
                drafting_agent="codex",
                blinded_from=["engine/policy.json"],
            )
            for index in range(100)
        ],
    )
    for draft in workbench.drafts:
        workbench.decisions[draft.case_id] = decide(
            draft=draft,
            final_answer=["omega3"],
            decided_by="검토자",
            decided_at="2026-08-01T01:00:00Z",
            review_duration_seconds=2.0,
        )
    workbench_file = (
        tmp_path / "data/original_plan/kpi/workbench/kpi1_workbench_v1.json"
    )
    save_workbench(workbench_file, workbench)

    before_seal = audit_repository(tmp_path, indicators=("KPI-1",))
    provenance = build_provenance(
        workbench,
        summarise_adjudication(workbench),
        system_under_test_id="engine-v1",
    )
    provenance["integrity_audit"] = before_seal["indicators"][0]
    seal = seal_reference_standard(
        indicator_id="KPI-1",
        cases={draft.case_id: ["omega3"] for draft in workbench.drafts},
        sealed_by="검토자",
        sealed_at="2026-08-01T02:00:00Z",
        contract=load_contract(ROOT),
        provenance=provenance,
    )
    seal_path = (
        tmp_path / "data/original_plan/kpi/seals/kpi1_reference_seal_v1.json"
    )
    seal_path.parent.mkdir(parents=True)
    seal_path.write_text(
        json.dumps(seal, ensure_ascii=False),
        encoding="utf-8",
    )
    assert audit_repository(
        tmp_path,
        indicators=("KPI-1",),
    )["completion_status"] == "READY"

    seal["provenance"]["role_separation"]["system_under_test_id"] = "tampered"
    seal_path.write_text(
        json.dumps(seal, ensure_ascii=False),
        encoding="utf-8",
    )
    tampered = audit_repository(tmp_path, indicators=("KPI-1",))

    assert tampered["completion_status"] == "BLOCKED"
    assert tampered["indicators"][0]["seal_intact"] is False


def test_sealing_readiness_blocks_a_failed_integrity_audit() -> None:
    result = sealing_readiness(
        indicator_audit={"indicator_id": "KPI-1", "verdict": "FAIL"},
        workbench={"drafts": [], "decisions": {}},
    )

    assert result["status"] == "BLOCKED"
    assert result["reason"] == "answer_key_integrity_audit_failed"


def test_sealing_readiness_blocks_pending_human_decisions() -> None:
    result = sealing_readiness(
        indicator_audit={"indicator_id": "KPI-1", "verdict": "PASS"},
        workbench={"drafts": [{"case_id": "case-1"}], "decisions": {}},
    )

    assert result["status"] == "BLOCKED"
    assert result["reason"] == "adjudication_incomplete"
    assert result["pending"] == 1


def test_sealing_readiness_blocks_rejected_cases_until_replaced() -> None:
    result = sealing_readiness(
        indicator_audit={"indicator_id": "KPI-1", "verdict": "PASS"},
        workbench={
            "drafts": [{"case_id": "case-1"}],
            "decisions": {"case-1": {"action": "rejected"}},
        },
    )

    assert result["status"] == "BLOCKED"
    assert result["reason"] == "rejected_cases_require_replacement"
    assert result["rejected_ids"] == ["case-1"]


def test_sealing_readiness_blocks_duplicate_draft_ids() -> None:
    result = sealing_readiness(
        indicator_audit={"indicator_id": "KPI-1", "verdict": "PASS"},
        workbench={
            "drafts": [{"case_id": "case-1"}, {"case_id": "case-1"}],
            "decisions": {"case-1": {"action": "accepted"}},
        },
    )

    assert result["status"] == "BLOCKED"
    assert result["reason"] == "draft_case_ids_must_be_unique_and_nonempty"


def test_sealing_readiness_accepts_a_complete_passed_workbench() -> None:
    result = sealing_readiness(
        indicator_audit={"indicator_id": "KPI-1", "verdict": "PASS"},
        workbench={
            "drafts": [{"case_id": "case-1"}],
            "decisions": {"case-1": {"action": "accepted"}},
        },
    )

    assert result["status"] == "READY"


def test_workbench_cli_refuses_to_write_when_the_audit_gate_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workbench = tmp_path / "workbench.json"
    destination = tmp_path / "seal.json"
    workbench.write_text(
        json.dumps(
            {
                "indicator_id": "KPI-1",
                "drafts": [
                    {
                        "case_id": "case-1",
                        "prompt": "질문",
                        "draft_answer": ["omega3"],
                        "draft_source": REFERENCE_DRAFT_SOURCE,
                    }
                ],
                "decisions": {
                    "case-1": {
                        "case_id": "case-1",
                        "action": "accepted",
                        "final_answer": ["omega3"],
                        "decided_by": "검토자",
                        "decided_at": "2026-07-31T09:00:00Z",
                        "note": "",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(workbench_cli, "workbench_path", lambda _: workbench)
    monkeypatch.setattr(workbench_cli, "seal_path", lambda _: destination)
    monkeypatch.setattr(
        workbench_cli,
        "audit_sealing_readiness",
        lambda *_: {
            "status": "BLOCKED",
            "reason": "answer_key_integrity_audit_failed",
        },
    )

    result = workbench_cli.cmd_seal(SimpleNamespace(indicator="KPI-1"))

    assert result == 2
    assert not destination.exists()


def test_reference_seal_cli_refuses_to_write_when_the_audit_gate_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases = tmp_path / "cases.json"
    destination = tmp_path / "seal.json"
    cases.write_text(json.dumps({"case-1": ["omega3"]}), encoding="utf-8")
    monkeypatch.setattr(reference_seal_cli, "seal_path", lambda _: destination)
    monkeypatch.setattr(
        reference_seal_cli,
        "audit_sealing_readiness",
        lambda *_: {
            "status": "BLOCKED",
            "reason": "answer_key_integrity_audit_failed",
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "seal_reference_standard.py",
            "seal",
            "--indicator",
            "KPI-1",
            "--cases",
            str(cases),
            "--by",
            "검토자",
        ],
    )

    result = reference_seal_cli.main()

    assert result == 2
    assert not destination.exists()


def test_reference_seal_cli_does_not_write_below_minimum_sample(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases = tmp_path / "cases.json"
    destination = tmp_path / "seal.json"
    cases.write_text(json.dumps({"case-1": ["omega3"]}), encoding="utf-8")
    monkeypatch.setattr(reference_seal_cli, "seal_path", lambda _: destination)
    monkeypatch.setattr(reference_seal_cli, "load_contract", lambda _: {})
    monkeypatch.setattr(
        reference_seal_cli,
        "audit_sealing_readiness",
        lambda *_: {"status": "READY", "integrity_audit": {"verdict": "PASS"}},
    )
    monkeypatch.setattr(reference_seal_cli, "load_workbench", lambda _: object())
    monkeypatch.setattr(
        reference_seal_cli,
        "summarise_adjudication",
        lambda _: {"reviewers": ["검토자"]},
    )
    monkeypatch.setattr(
        reference_seal_cli,
        "adjudicated_answer_key",
        lambda _: {"case-1": ["omega3"]},
    )
    monkeypatch.setattr(reference_seal_cli, "build_provenance", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(
        reference_seal_cli,
        "seal_reference_standard",
        lambda **_kwargs: {
            "case_count": 1,
            "minimum_sample_count": 100,
            "meets_minimum_sample": False,
            "seal_sha256": "abc",
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "seal_reference_standard.py",
            "seal",
            "--indicator",
            "KPI-1",
            "--cases",
            str(cases),
            "--by",
            "검토자",
            "--system-under-test-id",
            "engine-v1",
        ],
    )

    result = reference_seal_cli.main()

    assert result == 2
    assert not destination.exists()


def test_current_kpi1_and_kpi5_reviews_require_identity_attestation() -> None:
    """Imported pseudonymous reviews are not formal until identity is traceable."""
    for indicator in ("kpi1", "kpi5"):
        path = ROOT / f"data/original_plan/kpi/workbench/{indicator}_workbench_v1.json"
        if not path.is_file():
            continue
        workbench = json.loads(path.read_text(encoding="utf-8"))
        if not workbench.get("decisions"):
            continue
        assert len(workbench["decisions"]) == 100
        assert len(workbench.get("seal_disposals", [])) == 1
        assert audit_review_effort(workbench)["verdict"] == "FAIL"
