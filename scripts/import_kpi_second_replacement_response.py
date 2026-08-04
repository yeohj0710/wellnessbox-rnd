"""Validate and preserve the two-case Anthropic replacement response."""

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

from scripts.build_kpi_second_replacement_handoff import (  # noqa: E402
    CANDIDATES_PATH,
    REQUEST_PATH,
    SECOND_DIR,
)
from scripts.import_kpi_replacement_final_review import (  # noqa: E402
    DECISIONS_PATH,
)
from scripts.import_kpi_replacement_responses import (  # noqa: E402
    ALLOWED_ANTHROPIC_MODEL_IDS,
    SELECTION_NAME,
    SnapshotZip,
    _actual_anthropic_agent,
    _load_json,
    _validate_identity_selection,
)
from wellnessbox_rnd.evals.adaptive_answer_key_review import (  # noqa: E402
    build_adaptive_review_plan,
    register_independent_ai_review,
)
from wellnessbox_rnd.evals.answer_key_workbench import (  # noqa: E402
    CaseDraft,
    Workbench,
)

RESPONSE_NAME = "kpi1_response.json"
IDENTITY_NAME = SELECTION_NAME
RETURN_ZIP_NAME = "kpi1_second_replacement_completed.zip"
STAGING_PATH = SECOND_DIR / "kpi1_second_replacement_staging_v1.json"
RESPONSE_DIR = SECOND_DIR / "responses"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"json_object_required:{path}")
    return payload


def _drafts(payload: dict[str, Any]) -> list[CaseDraft]:
    if payload.get("schema_version") != "kpi_second_replacement_candidates_v1":
        raise ValueError("second_replacement_candidates_schema_invalid")
    cases = payload.get("cases", [])
    if payload.get("count") != 2 or len(cases) != 2:
        raise ValueError("second_replacement_candidate_count_changed")
    return [CaseDraft(**deepcopy(item)) for item in cases]


def validate_return(source: Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    reader = SnapshotZip(source)
    try:
        if set(reader.archive.namelist()) != {RESPONSE_NAME, IDENTITY_NAME}:
            raise ValueError("second_replacement_return_file_set_invalid")
        response, response_bytes = _load_json(reader, RESPONSE_NAME)
        identity_payload, identity_bytes = _load_json(reader, IDENTITY_NAME)
        identity = _validate_identity_selection(identity_payload)
        prior_decisions = _read_json(DECISIONS_PATH)
        if identity["reviewer_identity_ref"] != prior_decisions.get(
            "reviewer_identity_ref"
        ):
            raise ValueError("second_replacement_identity_mismatch")

        request = _read_json(REQUEST_PATH)
        candidates = _read_json(CANDIDATES_PATH)
        workbench = Workbench("KPI-1", _drafts(candidates))
        agent = _actual_anthropic_agent(
            response,
            "reviewing_agent",
            request.get("blindness_contract", {}).get(
                "allowed_model_ids", ALLOWED_ANTHROPIC_MODEL_IDS
            ),
        )
        record = register_independent_ai_review(
            workbench,
            reviewing_agent=agent,
            review_source=str(response.get("review_source", "")),
            blinded_from=list(response.get("blinded_from", [])),
            required_blinded_from=list(
                request.get("packet", {}).get("required_blinded_from", [])
            ),
            packet_sha256=str(response.get("packet_sha256", "")),
            engine_output_consulted=bool(
                response.get("engine_output_consulted", False)
            ),
            cases=list(response.get("cases", [])),
        )
        plan = build_adaptive_review_plan(workbench)
        if plan.get("status") != "REVIEW_REQUIRED":
            raise ValueError("second_replacement_final_review_not_required")
        if plan.get("required_detail_ids") != [
            "kpi1-repl2-001",
            "kpi1-repl2-002",
        ]:
            raise ValueError("second_replacement_review_case_set_changed")

        source_sha256 = hashlib.sha256(reader.source_bytes).hexdigest()
        result = {
            "schema_version": "kpi_second_replacement_staging_v1",
            "source_zip_sha256": source_sha256,
            "response_sha256": hashlib.sha256(response_bytes).hexdigest(),
            "identity_confirmation": identity,
            "validated_record": record,
            "review_plan": plan,
            "status": "READY_FOR_FINAL_REVIEW_PACKAGE",
        }
        return result, {
            RETURN_ZIP_NAME: reader.source_bytes,
            RESPONSE_NAME: response_bytes,
            IDENTITY_NAME: identity_bytes,
        }
    finally:
        reader.close()


def apply_return(source: Path) -> dict[str, Any]:
    result, snapshots = validate_return(source)
    RESPONSE_DIR.mkdir(parents=True, exist_ok=True)
    paths = {RESPONSE_DIR / name: content for name, content in snapshots.items()}
    paths[STAGING_PATH] = (
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    ).encode()
    previous = {path: path.read_bytes() if path.is_file() else None for path in paths}
    try:
        for path, content in paths.items():
            path.write_bytes(content)
    except Exception:
        for path, content in previous.items():
            if content is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(content)
        raise
    return {
        "status": result["status"],
        "source_zip_sha256": result["source_zip_sha256"],
        "case_count": result["validated_record"]["case_count"],
        "required_detail_ids": result["review_plan"]["required_detail_ids"],
        "staging_path": str(STAGING_PATH),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.input.is_file():
        raise SystemExit(f"second_replacement_return_missing:{args.input}")
    try:
        report = apply_return(args.input) if args.apply else validate_return(args.input)[0]
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
