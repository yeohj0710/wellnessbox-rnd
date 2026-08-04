from __future__ import annotations

import json
from copy import deepcopy

from scripts import apply_kpi_replacements as application
from wellnessbox_rnd.evals.adaptive_answer_key_review import audit_adaptive_review
from wellnessbox_rnd.evals.answer_key_workbench import load_workbench


def _report() -> dict:
    return json.loads(application.REPORT_PATH.read_text(encoding="utf-8"))


def test_applied_workbenches_contain_no_rejected_case() -> None:
    report = _report()

    assert report["status"] == "APPLIED_ALL_REPLACEMENTS"
    assert report["replacement_counts"] == {"KPI-1": 49, "KPI-4": 7, "KPI-5": 9}
    assert report["rejected_case_count_after_application"] == 0
    for indicator_id in application.INDICATORS:
        workbench = load_workbench(application._workbench_path(indicator_id))
        assert len(workbench.drafts) == 100
        assert len(workbench.decisions) == 100
        assert all(decision.action != "rejected" for decision in workbench.decisions.values())
        assert len(report["mappings"][indicator_id]) == report["replacement_counts"][indicator_id]


def test_applied_replacement_ids_are_present_and_original_rejects_are_absent() -> None:
    report = _report()

    for indicator_id, mappings in report["mappings"].items():
        workbench = load_workbench(application._workbench_path(indicator_id))
        case_ids = {draft.case_id for draft in workbench.drafts}
        assert {item["replacement_case_id"] for item in mappings} <= case_ids
        assert not ({item["rejected_case_id"] for item in mappings} & case_ids)


def test_composite_packet_segments_cover_every_merged_review_case() -> None:
    for indicator_id in application.INDICATORS:
        workbench = load_workbench(application._workbench_path(indicator_id))
        audit = audit_adaptive_review(
            workbench,
            required_blinded_from=workbench.drafts[0].blinded_from,
        )
        assert audit["verdict"] == "PASS"


def test_composite_packet_prompt_digest_tampering_is_rejected() -> None:
    workbench = deepcopy(
        load_workbench(application._workbench_path("KPI-1"))
    )
    workbench.ai_review["packet_segments"][0]["case_prompts_sha256"] = "0" * 64

    audit = audit_adaptive_review(
        workbench,
        required_blinded_from=workbench.drafts[0].blinded_from,
    )

    assert audit["verdict"] == "FAIL"
    assert audit["reason"] == "ai_review_packet_segment_prompt_digest_mismatch"
