from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import scripts.run_answer_key_workbench as workbench_cli
from wellnessbox_rnd.evals.adaptive_answer_key_review import (
    approve_consensus_batch,
    build_adaptive_review_plan,
    build_blind_ai_review_packet,
    register_independent_ai_review,
)
from wellnessbox_rnd.evals.answer_key_workbench import (
    CaseDraft,
    Decision,
    Workbench,
    load_workbench,
    save_workbench,
)


def _workbench(case_count: int = 100) -> Workbench:
    return Workbench(
        "KPI-1",
        [
            CaseDraft(
                case_id=f"case-{index:03}",
                prompt=f"상황 {index}",
                draft_answer=[f"answer-{index % 7}"],
                draft_source="independent_reference",
                drafting_agent="codex",
                blinded_from=["engine/policy.json"],
            )
            for index in range(case_count)
        ],
    )


def _reviews(workbench: Workbench) -> list[dict]:
    return [
        {
            "case_id": draft.case_id,
            "proposed_answer": list(draft.draft_answer),
            "confidence": 0.95,
            "flags": [],
        }
        for draft in workbench.drafts
    ]


def _register(workbench: Workbench, cases: list[dict] | None = None) -> None:
    packet = build_blind_ai_review_packet(
        workbench,
        required_blinded_from=["engine/policy.json"],
    )
    register_independent_ai_review(
        workbench,
        reviewing_agent="claude",
        review_source="independent_claude_opinion",
        blinded_from=["engine/policy.json"],
        required_blinded_from=["engine/policy.json"],
        packet_sha256=packet["packet_sha256"],
        engine_output_consulted=False,
        cases=cases or _reviews(workbench),
    )


def test_blind_packet_omits_primary_answers_and_rationales() -> None:
    workbench = _workbench(2)

    packet = build_blind_ai_review_packet(
        workbench,
        required_blinded_from=["engine/policy.json"],
    )

    assert set(packet["cases"][0]) == {"case_id", "prompt"}
    assert packet["omitted_fields"] == [
        "draft_answer",
        "draft_rationale",
        "engine_logic",
        "engine_output",
    ]
    assert packet["answer_vocabulary"]
    assert len(packet["packet_sha256"]) == 64


def test_ai_review_is_bound_to_the_blind_packet() -> None:
    workbench = _workbench(2)

    try:
        register_independent_ai_review(
            workbench,
            reviewing_agent="claude",
            review_source="independent_claude_opinion",
            blinded_from=["engine/policy.json"],
            required_blinded_from=["engine/policy.json"],
            packet_sha256="0" * 64,
            engine_output_consulted=False,
            cases=_reviews(workbench),
        )
    except ValueError as exc:
        assert str(exc) == "ai_review_packet_sha256_mismatch"
    else:
        raise AssertionError("response with wrong packet digest was accepted")


def test_ai_review_rejects_engine_output_and_missing_blinding() -> None:
    workbench = _workbench(2)
    packet = build_blind_ai_review_packet(
        workbench,
        required_blinded_from=["engine/policy.json", "engine/safety.json"],
    )
    common = {
        "workbench": workbench,
        "reviewing_agent": "claude",
        "review_source": "independent_claude_opinion",
        "packet_sha256": packet["packet_sha256"],
        "cases": _reviews(workbench),
    }

    try:
        register_independent_ai_review(
            **common,
            blinded_from=["engine/policy.json", "engine/safety.json"],
            required_blinded_from=["engine/policy.json", "engine/safety.json"],
            engine_output_consulted=True,
        )
    except ValueError as exc:
        assert str(exc) == "ai_review_consulted_engine_output"
    else:
        raise AssertionError("engine-informed AI review was accepted")

    try:
        register_independent_ai_review(
            **common,
            blinded_from=["engine/policy.json"],
            required_blinded_from=["engine/policy.json", "engine/safety.json"],
            engine_output_consulted=False,
        )
    except ValueError as exc:
        assert str(exc) == "ai_review_missing_blinded_paths:engine/safety.json"
    else:
        raise AssertionError("AI review with incomplete blinding was accepted")


def test_all_agreements_require_only_five_detailed_reviews() -> None:
    workbench = _workbench()
    _register(workbench)

    plan = build_adaptive_review_plan(workbench)

    assert plan["status"] == "REVIEW_REQUIRED"
    assert plan["agreement_count"] == 100
    assert plan["disagreement_count"] == 0
    assert plan["sample_target_count"] == 5
    assert len(plan["required_detail_ids"]) == 5


def test_every_disagreement_and_flag_is_required() -> None:
    workbench = _workbench()
    reviews = _reviews(workbench)
    reviews[0]["proposed_answer"] = ["different"]
    reviews[1]["flags"] = ["clinical_uncertainty"]
    _register(workbench, reviews)

    plan = build_adaptive_review_plan(workbench)

    assert reviews[0]["case_id"] in plan["required_detail_ids"]
    assert reviews[1]["case_id"] in plan["required_detail_ids"]
    assert plan["disagreement_count"] == 1
    assert plan["flagged_count"] == 1


def test_one_sample_correction_expands_to_twenty() -> None:
    workbench = _workbench()
    _register(workbench)
    initial = build_adaptive_review_plan(workbench)
    corrected_id = initial["sampled_agreement_ids"][0]
    workbench.decisions[corrected_id] = Decision(
        case_id=corrected_id,
        action="edited",
        final_answer=["corrected"],
        decided_by="여형준",
        decided_at="2026-08-01T01:00:00Z",
    )

    expanded = build_adaptive_review_plan(workbench)

    assert expanded["sample_correction_count"] == 1
    assert expanded["sample_target_count"] == 20
    assert len(expanded["sampled_agreement_ids"]) == 20


def test_two_sample_corrections_require_every_agreement() -> None:
    workbench = _workbench()
    _register(workbench)
    initial = build_adaptive_review_plan(workbench)
    for case_id in initial["sampled_agreement_ids"][:2]:
        workbench.decisions[case_id] = Decision(
            case_id=case_id,
            action="edited",
            final_answer=["corrected"],
            decided_by="여형준",
            decided_at="2026-08-01T01:00:00Z",
        )

    expanded = build_adaptive_review_plan(workbench)

    assert expanded["sample_correction_count"] == 2
    assert expanded["escalation"] == "full_agreement_review"
    assert len(expanded["required_detail_ids"]) == 100


def test_same_provider_family_cannot_review_its_own_draft() -> None:
    workbench = _workbench()

    try:
        register_independent_ai_review(
            workbench,
            reviewing_agent="OpenAI GPT-5",
            review_source="independent_openai_opinion",
            blinded_from=["engine/policy.json"],
            required_blinded_from=["engine/policy.json"],
            packet_sha256=build_blind_ai_review_packet(
                workbench,
                required_blinded_from=["engine/policy.json"],
            )["packet_sha256"],
            engine_output_consulted=False,
            cases=_reviews(workbench),
        )
    except ValueError as exc:
        assert str(exc) == "ai_review_agent_matches_drafting_agent_family"
    else:
        raise AssertionError("same-family review was accepted")


def test_consensus_batch_needs_detailed_sample_and_exact_human_confirmation() -> None:
    workbench = _workbench()
    _register(workbench)
    plan = build_adaptive_review_plan(workbench)

    try:
        approve_consensus_batch(
            workbench,
            approved_by="여형준",
            confirmation="KPI-1 AI 합의안 일괄 승인",
        )
    except ValueError as exc:
        assert str(exc) == "required_detailed_review_pending"
    else:
        raise AssertionError("batch approval bypassed the detailed sample")

    for case_id in plan["required_detail_ids"]:
        draft = next(item for item in workbench.drafts if item.case_id == case_id)
        workbench.decisions[case_id] = Decision(
            case_id=case_id,
            action="accepted",
            final_answer=list(draft.draft_answer),
            decided_by="여형준",
            decided_at="2026-08-01T01:00:00Z",
            review_duration_seconds=3.0,
        )

    try:
        approve_consensus_batch(
            workbench,
            approved_by="여형준",
            confirmation="승인",
        )
    except ValueError as exc:
        assert str(exc) == "consensus_batch_confirmation_mismatch"
    else:
        raise AssertionError("batch approval accepted an imprecise confirmation")

    approval = approve_consensus_batch(
        workbench,
        approved_by="여형준",
        confirmation="KPI-1 AI 합의안 일괄 승인",
        approved_at="2026-08-01T02:00:00Z",
    )

    assert approval["batch_approved_count"] == 95
    assert len(workbench.decisions) == 100
    assert sum(not item.reviewed_in_detail for item in workbench.decisions.values()) == 95
    assert build_adaptive_review_plan(workbench)["status"] == "READY_TO_SEAL"


def test_cli_exports_blind_packet_and_imports_complete_ai_review() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        bench_path = save_workbench(root / "workbench.json", _workbench(3))
        packet_path = root / "packet.json"
        response_path = root / "response.json"
        with (
            patch.object(workbench_cli, "workbench_path", return_value=bench_path),
            patch.object(
                workbench_cli,
                "engine_logic_blinded_from",
                return_value=["engine/policy.json"],
            ),
        ):
            export_result = workbench_cli.cmd_export_ai_review(
                SimpleNamespace(indicator="KPI-1", output=str(packet_path))
            )
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            response_path.write_text(
                json.dumps(
                    {
                        "reviewing_agent": "claude",
                        "review_source": "independent_claude_opinion",
                        "blinded_from": ["engine/policy.json"],
                        "packet_sha256": packet["packet_sha256"],
                        "engine_output_consulted": False,
                        "cases": _reviews(load_workbench(bench_path)),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            import_result = workbench_cli.cmd_import_ai_review(
                SimpleNamespace(indicator="KPI-1", response=str(response_path))
            )

        assert export_result == 0
        assert import_result == 0
        assert set(packet["cases"][0]) == {"case_id", "prompt"}
        assert load_workbench(bench_path).ai_review["reviewing_agent"] == "claude"
