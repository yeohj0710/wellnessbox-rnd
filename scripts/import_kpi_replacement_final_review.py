"""Validate and preserve completed final decisions for KPI replacement cases."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.build_kpi_replacement_final_review_package import (  # noqa: E402
    CSV_FIELDS,
    IDENTITY_NAME,
    REVIEW_CSV_NAME,
    STAGING_PATH,
    build_rows,
    build_workbenches,
)
from scripts.import_kpi_replacement_responses import (  # noqa: E402
    SnapshotZip,
    _validate_identity_selection,
)
from wellnessbox_rnd.evals.answer_key_integrity import (  # noqa: E402
    MIN_SECONDS_PER_DECISION,
)

OUTPUT_DIR = STAGING_PATH.parent / "final_review" / "completed"
SOURCE_ZIP_NAME = "kpi_replacement_final_review_completed.zip"
DECISIONS_PATH = OUTPUT_DIR / "kpi_replacement_final_decisions_v1.json"
IMMUTABLE_FIELDS = tuple(
    field
    for field in CSV_FIELDS
    if field not in {"결정", "수정_정답", "메모", "시작_시각", "종료_시각"}
)
EDITABLE_FIELDS = {"결정", "수정_정답", "메모", "시작_시각", "종료_시각"}
ALLOWED_DECISIONS = {"ACCEPT", "EDIT", "REJECT"}


def _parse_timestamp(value: str, *, case_id: str, field: str) -> datetime:
    try:
        stamp = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"review_timestamp_invalid:{case_id}:{field}") from exc
    if stamp.tzinfo is None:
        raise ValueError(f"review_timestamp_timezone_missing:{case_id}:{field}")
    return stamp


def _split_answer(value: str) -> list[str]:
    return sorted({item.strip() for item in value.split("|") if item.strip()})


def _load_csv(reader: SnapshotZip) -> tuple[list[dict[str, str]], bytes]:
    content = reader.read(REVIEW_CSV_NAME)
    text = content.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise ValueError("replacement_final_review_csv_empty")
    if tuple(rows[0]) != CSV_FIELDS:
        raise ValueError("replacement_final_review_csv_fields_changed")
    if any(None in row or set(row) != set(CSV_FIELDS) for row in rows):
        raise ValueError("replacement_final_review_csv_shape_invalid")
    return rows, content


def _load_identity(reader: SnapshotZip) -> tuple[dict[str, Any], bytes]:
    content = reader.read(IDENTITY_NAME)
    payload = json.loads(content.decode("utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("replacement_final_review_identity_object_required")
    return payload, content


def validate_return(source: Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    reader = SnapshotZip(source)
    try:
        rows, csv_bytes = _load_csv(reader)
        identity_payload, identity_bytes = _load_identity(reader)
        identity = _validate_identity_selection(identity_payload)
        staging = json.loads(STAGING_PATH.read_text(encoding="utf-8"))
        if staging.get("status") != "READY_FOR_FINAL_REVIEW_PACKAGE":
            raise ValueError("replacement_staging_not_ready_for_final_decisions")
        if identity["reviewer_identity_ref"] != staging.get(
            "identity_confirmation", {}
        ).get("reviewer_identity_ref"):
            raise ValueError("replacement_final_review_identity_mismatch")

        expected_rows, _ = build_rows()
        if len(rows) != len(expected_rows):
            raise ValueError("replacement_final_review_case_count_changed")
        workbenches = build_workbenches(staging)
        vocabularies = {
            indicator_id: {
                token
                for draft in workbench.drafts
                for token in draft.draft_answer
                if token.strip()
            }
            | set(workbench.ai_review.get("answer_vocabulary", []))
            | set(workbench.primary_ai_draft.get("answer_vocabulary", []))
            for indicator_id, workbench in workbenches.items()
        }
        decisions: list[dict[str, Any]] = []
        intervals: list[tuple[datetime, datetime, str]] = []
        seen: set[str] = set()
        counts = {choice: 0 for choice in sorted(ALLOWED_DECISIONS)}
        indicator_counts: dict[str, dict[str, int]] = {}

        for row, expected in zip(rows, expected_rows, strict=True):
            case_id = row["case_id"].strip()
            indicator_id = row["indicator_id"].strip()
            if not case_id or case_id in seen:
                raise ValueError(f"replacement_final_review_case_id_invalid:{case_id}")
            seen.add(case_id)
            for field in IMMUTABLE_FIELDS:
                if row[field] != expected[field]:
                    raise ValueError(
                        f"replacement_final_review_source_field_changed:{case_id}:{field}"
                    )

            decision = row["결정"].strip().upper()
            edited_answer = _split_answer(row["수정_정답"])
            if decision not in ALLOWED_DECISIONS:
                raise ValueError(f"replacement_final_review_decision_invalid:{case_id}")
            if decision == "EDIT" and not edited_answer:
                raise ValueError(f"replacement_final_review_edit_empty:{case_id}")
            if decision != "EDIT" and edited_answer:
                raise ValueError(
                    f"replacement_final_review_unexpected_edited_answer:{case_id}"
                )
            final_answer = (
                _split_answer(expected["권고_정답"])
                if decision == "ACCEPT"
                else edited_answer if decision == "EDIT" else []
            )
            outside = sorted(set(final_answer) - vocabularies[indicator_id])
            if outside:
                raise ValueError(
                    f"replacement_final_review_answer_outside_vocabulary:{case_id}:"
                    f"{'|'.join(outside)}"
                )

            start = _parse_timestamp(row["시작_시각"], case_id=case_id, field="start")
            end = _parse_timestamp(row["종료_시각"], case_id=case_id, field="end")
            duration = (end - start).total_seconds()
            if not math.isfinite(duration) or duration < MIN_SECONDS_PER_DECISION:
                raise ValueError(f"replacement_final_review_duration_too_short:{case_id}")
            intervals.append((start, end, case_id))
            counts[decision] += 1
            per_indicator = indicator_counts.setdefault(
                indicator_id, {choice: 0 for choice in sorted(ALLOWED_DECISIONS)}
            )
            per_indicator[decision] += 1
            decisions.append(
                {
                    "indicator_id": indicator_id,
                    "case_id": case_id,
                    "decision": decision,
                    "final_answer": final_answer,
                    "note": row["메모"].strip(),
                    "started_at": start.isoformat(),
                    "decided_at": end.isoformat(),
                    "review_duration_seconds": duration,
                }
            )

        ordered = sorted(intervals)
        for previous, current in zip(ordered, ordered[1:], strict=False):
            if current[0] < previous[1]:
                raise ValueError(
                    f"replacement_final_review_intervals_overlap:{previous[2]}:{current[2]}"
                )

        source_sha256 = hashlib.sha256(reader.source_bytes).hexdigest()
        result = {
            "schema_version": "kpi_replacement_final_decisions_v1",
            "source_zip_sha256": source_sha256,
            "source_csv_sha256": hashlib.sha256(csv_bytes).hexdigest(),
            "reviewer_identity_ref": identity["reviewer_identity_ref"],
            "identity_confirmed_at": identity["confirmed_at"],
            "review_count": len(decisions),
            "decision_counts": counts,
            "indicator_decision_counts": indicator_counts,
            "replacement_required_count": counts["REJECT"],
            "replacement_required_case_ids": [
                item["case_id"] for item in decisions if item["decision"] == "REJECT"
            ],
            "status": (
                "IMPORTED_ADDITIONAL_REPLACEMENTS_REQUIRED"
                if counts["REJECT"]
                else "IMPORTED_COMPLETE"
            ),
            "decisions": decisions,
        }
        return result, {
            SOURCE_ZIP_NAME: reader.source_bytes,
            REVIEW_CSV_NAME: csv_bytes,
            IDENTITY_NAME: identity_bytes,
        }
    finally:
        reader.close()


def apply_return(source: Path) -> dict[str, Any]:
    result, snapshots = validate_return(source)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = {OUTPUT_DIR / name: content for name, content in snapshots.items()}
    paths[DECISIONS_PATH] = (
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
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
        "review_count": result["review_count"],
        "decision_counts": result["decision_counts"],
        "replacement_required_case_ids": result["replacement_required_case_ids"],
        "decisions_path": str(DECISIONS_PATH),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.input.is_file():
        raise SystemExit(f"replacement_final_review_return_missing:{args.input}")
    try:
        result = apply_return(args.input) if args.apply else validate_return(args.input)[0]
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
