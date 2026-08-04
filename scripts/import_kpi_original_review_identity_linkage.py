"""Validate and apply one identity link to the original 335 KPI decisions."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.build_kpi_original_review_identity_linkage_package import (  # noqa: E402
    ANONYMOUS_REVIEWER,
    APPLICATION_PATH,
    FORM_NAME,
    INDICATORS,
    OUTPUT_DIR,
    RETURN_ZIP_NAME,
    _workbench_path,
    build_form,
    decision_scope,
    eligible_reviewer,
)
from wellnessbox_rnd.evals.answer_key_workbench import (  # noqa: E402
    Workbench,
    load_workbench,
    save_workbench,
)

COMPLETED_DIR = OUTPUT_DIR / "completed"
EDITABLE_FIELDS = {"identity_link_status", "confirmed_at"}


def _parse_confirmed_at(value: str) -> str:
    raw = value.strip()
    try:
        stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("identity_link_confirmed_at_invalid") from exc
    if stamp.tzinfo is None:
        raise ValueError("identity_link_confirmed_at_timezone_missing")
    return stamp.isoformat()


def validate_return(source: Path, root: Path = ROOT) -> tuple[dict[str, Any], bytes]:
    source_bytes = source.read_bytes()
    with zipfile.ZipFile(source) as archive:
        if archive.namelist() != [FORM_NAME]:
            raise ValueError("identity_link_return_file_set_invalid")
        form_bytes = archive.read(FORM_NAME)
    payload = json.loads(form_bytes.decode("utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("identity_link_form_object_required")
    expected = build_form(root)
    for field, value in expected.items():
        if field not in EDITABLE_FIELDS and payload.get(field) != value:
            raise ValueError(f"identity_link_immutable_field_changed:{field}")
    if set(payload) != set(expected):
        raise ValueError("identity_link_form_fields_changed")
    status = str(payload.get("identity_link_status", "")).strip().upper()
    if status != "CONFIRMED":
        raise ValueError("identity_link_not_confirmed")
    confirmed_at = _parse_confirmed_at(str(payload.get("confirmed_at", "")))
    identity = eligible_reviewer(root)
    if payload["reviewer_identity_ref"] != identity["reviewer_identity_ref"]:
        raise ValueError("identity_link_reviewer_not_eligible")
    application_path = root / APPLICATION_PATH.relative_to(ROOT)
    existing_application = None
    if application_path.is_file():
        existing_application = json.loads(
            application_path.read_text(encoding="utf-8")
        )
        if existing_application.get("status") != "APPLIED":
            raise ValueError("identity_link_application_status_invalid")
    else:
        scope = decision_scope(root)
        if payload["decision_scope_sha256"] != scope["decision_scope_sha256"]:
            raise ValueError("identity_link_decision_scope_changed")
    result = {
        "schema_version": "kpi_original_review_identity_linkage_application_v1",
        "status": "ALREADY_APPLIED" if existing_application else "READY_TO_APPLY",
        "source_return_zip_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "source_form_sha256": hashlib.sha256(form_bytes).hexdigest(),
        "source_review_zip_sha256": payload["source_review_zip_sha256"],
        "reviewer_identity_ref": payload["reviewer_identity_ref"],
        "registered_name": identity["registered_name"],
        "qualification_stage": payload["qualification_stage"],
        "confirmed_at": confirmed_at,
        "confirmation_channel": "direct_completed_form",
        "confirmed_at_semantics": "provided_in_completed_form",
        "indicator_counts": payload["indicator_counts"],
        "total_decision_count": payload["total_decision_count"],
        "decision_scope_sha256": payload["decision_scope_sha256"],
        "case_ids_sha256": payload["case_ids_sha256"],
    }
    return result, form_bytes


def _linked_workbenches(
    result: dict[str, Any], root: Path = ROOT
) -> dict[str, Workbench]:
    workbenches: dict[str, Workbench] = {}
    linkage = {
        key: result[key]
        for key in (
            "schema_version",
            "source_return_zip_sha256",
            "source_form_sha256",
            "source_review_zip_sha256",
            "reviewer_identity_ref",
            "registered_name",
            "qualification_stage",
            "confirmed_at",
            "confirmation_channel",
            "confirmed_at_semantics",
            "indicator_counts",
            "total_decision_count",
            "decision_scope_sha256",
            "case_ids_sha256",
        )
    }
    changed_total = 0
    for indicator_id in INDICATORS:
        workbench = load_workbench(_workbench_path(root, indicator_id))
        changed = 0
        for decision in workbench.decisions.values():
            if (
                decision.decided_by == ANONYMOUS_REVIEWER
                and not decision.reviewer_identity_ref
            ):
                decision.decided_by = result["registered_name"]
                decision.reviewer_identity_ref = result["reviewer_identity_ref"]
                changed += 1
        expected = int(result["indicator_counts"][indicator_id])
        if changed != expected:
            raise ValueError(
                f"{indicator_id}:identity_link_application_count_mismatch:"
                f"{changed}:{expected}"
            )
        workbench.identity_linkages.append(deepcopy(linkage))
        workbenches[indicator_id] = workbench
        changed_total += changed
    if changed_total != result["total_decision_count"]:
        raise ValueError("identity_link_application_total_mismatch")
    return workbenches


def apply_return(
    source: Path,
    root: Path = ROOT,
    *,
    confirmation_channel: str = "",
    confirmed_at_semantics: str = "",
) -> dict[str, Any]:
    result, form_bytes = validate_return(source, root)
    if result["status"] == "ALREADY_APPLIED":
        raise ValueError("identity_link_already_applied")
    if confirmation_channel.strip():
        result["confirmation_channel"] = confirmation_channel.strip()
    if confirmed_at_semantics.strip():
        result["confirmed_at_semantics"] = confirmed_at_semantics.strip()
    workbenches = _linked_workbenches(result, root)
    completed_dir = root / COMPLETED_DIR.relative_to(ROOT)
    application_path = root / APPLICATION_PATH.relative_to(ROOT)
    paths = {
        _workbench_path(root, indicator_id)
        for indicator_id in INDICATORS
    }
    paths.update(
        {
            completed_dir / RETURN_ZIP_NAME,
            completed_dir / FORM_NAME,
            application_path,
        }
    )
    previous = {path: path.read_bytes() if path.is_file() else None for path in paths}
    completed_dir.mkdir(parents=True, exist_ok=True)
    applied = {**result, "status": "APPLIED"}
    try:
        for indicator_id, workbench in workbenches.items():
            save_workbench(_workbench_path(root, indicator_id), workbench)
        (completed_dir / RETURN_ZIP_NAME).write_bytes(source.read_bytes())
        (completed_dir / FORM_NAME).write_bytes(form_bytes)
        application_path.write_text(
            json.dumps(applied, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception:
        for path, content in previous.items():
            if content is None:
                path.unlink(missing_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
        raise
    return applied


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirmation-channel", default="")
    parser.add_argument("--confirmed-at-semantics", default="")
    args = parser.parse_args()
    try:
        result = (
            apply_return(
                args.input,
                confirmation_channel=args.confirmation_channel,
                confirmed_at_semantics=args.confirmed_at_semantics,
            )
            if args.apply
            else validate_return(args.input)[0]
        )
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
