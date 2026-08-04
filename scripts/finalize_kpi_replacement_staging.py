"""Attach the preserved OpenAI KPI-4 opinion after the Anthropic primary draft."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.build_kpi_replacement_handoff import (  # noqa: E402
    OUTPUT_DIR,
    REQUEST_NAMES,
    RESPONSE_NAMES,
    build_candidates,
)
from scripts.import_kpi_replacement_responses import (  # noqa: E402
    STAGING_PATH,
    SnapshotZip,
    _load_json,
    _required_blinded_from,
    _validate_identity_selection,
)
from wellnessbox_rnd.evals.adaptive_answer_key_review import (  # noqa: E402
    agent_family,
    build_adaptive_review_plan,
    register_blind_primary_ai_draft,
    register_independent_ai_review,
)
from wellnessbox_rnd.evals.answer_key_workbench import Workbench  # noqa: E402

OPENAI_SUBMISSION_DIR = OUTPUT_DIR / "openai_submission"
OPENAI_SOURCE_ZIP = OPENAI_SUBMISSION_DIR / "kpi_replacement_completed.zip"
OPENAI_INTAKE_REPORT = OPENAI_SUBMISSION_DIR / "intake_report_v1.json"
OPENAI_MODEL_ID = "gpt-5.6-pro"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"json_object_required:{path}")
    return payload


def _case_list(record: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"case_id": case_id, **case}
        for case_id, case in record.get("cases", {}).items()
    ]


def build_finalized_staging(
    *,
    staging_path: Path = STAGING_PATH,
    openai_source_zip: Path = OPENAI_SOURCE_ZIP,
    intake_report_path: Path = OPENAI_INTAKE_REPORT,
) -> dict[str, Any]:
    staging = _read_json(staging_path)
    if staging.get("schema_version") != "kpi_replacement_staging_v1":
        raise ValueError("replacement_staging_schema_invalid")
    if staging.get("status") not in {
        "READY_FOR_KPI4_SECOND_OPINION_AND_FINAL_REVIEW",
        "READY_FOR_FINAL_REVIEW_PACKAGE",
    }:
        raise ValueError("replacement_staging_not_ready_for_kpi4_review")

    intake = _read_json(intake_report_path)
    source_bytes = openai_source_zip.read_bytes()
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    if source_sha256 != intake.get("source_zip_sha256"):
        raise ValueError("openai_submission_zip_sha256_mismatch")
    disposition = intake.get("dispositions", {}).get("KPI-4", {})
    if disposition.get("status") != "PENDING_REUSE_AS_OPENAI_SECOND_OPINION":
        raise ValueError("openai_kpi4_response_not_approved_for_pending_reuse")

    candidates = build_candidates()
    workbench = Workbench("KPI-4", deepcopy(candidates["KPI-4"]))
    primary = staging.get("responses", {}).get("KPI-4", {}).get(
        "validated_record", {}
    )
    if primary.get("drafting_agent_family") != "anthropic":
        raise ValueError("kpi4_anthropic_primary_required")
    workbench.primary_ai_draft = {
        "answer_vocabulary": list(primary.get("answer_vocabulary", []))
    }
    register_blind_primary_ai_draft(
        workbench,
        drafting_agent=str(primary.get("drafting_agent", "")),
        draft_source=str(primary.get("response_source", "")),
        blinded_from=list(primary.get("blinded_from", [])),
        required_blinded_from=list(primary.get("required_blinded_from", [])),
        packet_sha256=str(primary.get("packet_sha256", "")),
        engine_output_consulted=bool(
            primary.get("engine_output_consulted", False)
        ),
        cases=_case_list(primary),
        input_response_role=str(primary.get("input_response_role", "")),
        input_response_sha256=str(primary.get("input_response_sha256", "")),
        drafted_at=str(primary.get("drafted_at", "")),
    )

    reader = SnapshotZip(openai_source_zip)
    try:
        selection, _ = _load_json(reader, "reviewer_identity_selection.json")
        identity = _validate_identity_selection(selection)
        if identity.get("reviewer_identity_ref") != staging.get(
            "identity_confirmation", {}
        ).get("reviewer_identity_ref"):
            raise ValueError("replacement_submission_identity_mismatch")
        response, raw = _load_json(reader, RESPONSE_NAMES["KPI-4"])
    finally:
        reader.close()

    original_agent = str(response.get("drafting_agent", "")).strip()
    if original_agent.casefold() != OPENAI_MODEL_ID or agent_family(
        original_agent
    ) != "openai":
        raise ValueError("kpi4_openai_second_opinion_agent_invalid")
    request = _read_json(OUTPUT_DIR / REQUEST_NAMES["KPI-4"])
    review = register_independent_ai_review(
        workbench,
        reviewing_agent=original_agent,
        review_source=str(response.get("draft_source", "")),
        blinded_from=list(response.get("blinded_from", [])),
        required_blinded_from=_required_blinded_from(request),
        packet_sha256=str(response.get("packet_sha256", "")),
        engine_output_consulted=bool(
            response.get("engine_output_consulted", False)
        ),
        cases=list(response.get("cases", [])),
    )
    response_sha256 = hashlib.sha256(raw).hexdigest()
    if response_sha256 != disposition.get("response_sha256"):
        raise ValueError("kpi4_openai_response_sha256_mismatch")
    review["input_response_sha256"] = response_sha256
    review["reviewed_at_semantics"] = (
        "role_registration_time_not_response_generation_time"
    )
    review["role_conversion_provenance"] = {
        "source_zip_sha256": source_sha256,
        "original_response_role": disposition.get("original_response_role"),
        "original_agent_field": "drafting_agent",
        "original_source_field": "draft_source",
        "applied_response_role": "independent_ai_review",
        "conversion_reason": (
            "blind_openai_response_registered_after_anthropic_primary"
        ),
        "source_submission_precedes_anthropic_primary_import": True,
        "content_regenerated_for_role_conversion": False,
        "registration_order_only": True,
        "original_provenance_preserved": True,
    }

    result = deepcopy(staging)
    result["responses"]["KPI-4"]["openai_second_opinion"] = {
        "response_sha256": response_sha256,
        "validated_record": review,
    }
    result["review_plans"] = {
        "KPI-4": build_adaptive_review_plan(workbench),
    }
    result["status"] = "READY_FOR_FINAL_REVIEW_PACKAGE"
    return result


def apply_finalized_staging(staging_path: Path = STAGING_PATH) -> dict[str, Any]:
    result = build_finalized_staging(staging_path=staging_path)
    temporary = staging_path.with_suffix(staging_path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(staging_path)
    return {
        "status": result["status"],
        "kpi4_review_plan": result["review_plans"]["KPI-4"],
        "staging_path": str(staging_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        report = (
            apply_finalized_staging()
            if args.apply
            else {
                "status": build_finalized_staging()["status"],
            }
        )
    except (ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
