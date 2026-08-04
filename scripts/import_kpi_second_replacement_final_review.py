"""Validate and preserve the final two KPI-1 replacement decisions."""

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
)
from scripts.build_kpi_second_replacement_final_review_package import (  # noqa: E402
    FINAL_DIR,
    REVIEW_CSV_NAME,
)
from scripts.build_kpi_second_replacement_handoff import (  # noqa: E402
    CANDIDATES_PATH,
)
from scripts.import_kpi_replacement_responses import (  # noqa: E402
    SnapshotZip,
    _validate_identity_selection,
)
from scripts.import_kpi_second_replacement_response import (  # noqa: E402
    STAGING_PATH,
)
from wellnessbox_rnd.evals.answer_key_integrity import (  # noqa: E402
    MIN_SECONDS_PER_DECISION,
)

RETURN_ZIP_NAME = "kpi1_second_replacement_final_review_completed.zip"
COMPLETED_DIR = FINAL_DIR / "completed"
DECISIONS_PATH = COMPLETED_DIR / "kpi1_second_replacement_final_decisions_v1.json"
EDITABLE_FIELDS = {"결정", "수정_정답", "메모", "시작_시각", "종료_시각"}
IMMUTABLE_FIELDS = tuple(field for field in CSV_FIELDS if field not in EDITABLE_FIELDS)
ALLOWED_DECISIONS = {"ACCEPT", "EDIT", "REJECT"}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"json_object_required:{path}")
    return payload


def _split_answer(value: str) -> list[str]:
    return sorted({item.strip() for item in value.split("|") if item.strip()})


def _parse_timestamp(value: str, *, case_id: str, field: str) -> datetime:
    try:
        stamp = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"second_final_timestamp_invalid:{case_id}:{field}") from exc
    if stamp.tzinfo is None:
        raise ValueError(f"second_final_timestamp_timezone_missing:{case_id}:{field}")
    return stamp


def validate_return(source: Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    reader = SnapshotZip(source)
    try:
        if set(reader.archive.namelist()) != {REVIEW_CSV_NAME, IDENTITY_NAME}:
            raise ValueError("second_final_return_file_set_invalid")
        csv_bytes = reader.read(REVIEW_CSV_NAME)
        rows = list(
            csv.DictReader(io.StringIO(csv_bytes.decode("utf-8-sig")))
        )
        if len(rows) != 2 or tuple(rows[0]) != CSV_FIELDS:
            raise ValueError("second_final_csv_shape_invalid")
        if any(None in row or set(row) != set(CSV_FIELDS) for row in rows):
            raise ValueError("second_final_csv_row_shape_invalid")

        identity_bytes = reader.read(IDENTITY_NAME)
        identity_payload = json.loads(identity_bytes.decode("utf-8-sig"))
        if not isinstance(identity_payload, dict):
            raise ValueError("second_final_identity_object_required")
        identity = _validate_identity_selection(identity_payload)
        staging = _read_json(STAGING_PATH)
        if identity["reviewer_identity_ref"] != staging.get(
            "identity_confirmation", {}
        ).get("reviewer_identity_ref"):
            raise ValueError("second_final_identity_mismatch")

        expected_rows = list(
            csv.DictReader(
                io.StringIO(
                    (FINAL_DIR / REVIEW_CSV_NAME).read_text(
                        encoding="utf-8-sig"
                    )
                )
            )
        )
        if len(expected_rows) != 2 or tuple(expected_rows[0]) != CSV_FIELDS:
            raise ValueError("second_final_source_csv_shape_invalid")
        vocabulary = {
            token
            for item in _read_json(CANDIDATES_PATH).get("cases", [])
            for token in item.get("draft_answer", [])
        } | {
            token
            for item in staging.get("validated_record", {}).get("cases", {}).values()
            for token in item.get("proposed_answer", [])
        }
        intervals: list[tuple[datetime, datetime, str]] = []
        decisions: list[dict[str, Any]] = []
        seen: set[str] = set()
        counts = {choice: 0 for choice in sorted(ALLOWED_DECISIONS)}
        for row, expected in zip(rows, expected_rows, strict=True):
            case_id = row["case_id"].strip()
            if not case_id or case_id in seen:
                raise ValueError(f"second_final_case_id_invalid:{case_id}")
            seen.add(case_id)
            for field in IMMUTABLE_FIELDS:
                if row[field] != expected[field]:
                    raise ValueError(f"second_final_source_field_changed:{case_id}:{field}")
            choice = row["결정"].strip().upper()
            edited = _split_answer(row["수정_정답"])
            if choice not in ALLOWED_DECISIONS:
                raise ValueError(f"second_final_decision_invalid:{case_id}")
            if choice == "EDIT" and not edited:
                raise ValueError(f"second_final_edit_empty:{case_id}")
            if choice != "EDIT" and edited:
                raise ValueError(f"second_final_unexpected_edit:{case_id}")
            final_answer = (
                _split_answer(expected["권고_정답"])
                if choice == "ACCEPT"
                else edited if choice == "EDIT" else []
            )
            outside = sorted(set(final_answer) - vocabulary)
            if outside:
                raise ValueError(
                    f"second_final_answer_outside_vocabulary:{case_id}:{'|'.join(outside)}"
                )
            start = _parse_timestamp(row["시작_시각"], case_id=case_id, field="start")
            end = _parse_timestamp(row["종료_시각"], case_id=case_id, field="end")
            duration = (end - start).total_seconds()
            if not math.isfinite(duration) or duration < MIN_SECONDS_PER_DECISION:
                raise ValueError(f"second_final_duration_too_short:{case_id}")
            intervals.append((start, end, case_id))
            counts[choice] += 1
            decisions.append(
                {
                    "indicator_id": "KPI-1",
                    "case_id": case_id,
                    "decision": choice,
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
                    f"second_final_intervals_overlap:{previous[2]}:{current[2]}"
                )
        result = {
            "schema_version": "kpi_second_replacement_final_decisions_v1",
            "source_zip_sha256": hashlib.sha256(reader.source_bytes).hexdigest(),
            "source_csv_sha256": hashlib.sha256(csv_bytes).hexdigest(),
            "reviewer_identity_ref": identity["reviewer_identity_ref"],
            "identity_confirmed_at": identity["confirmed_at"],
            "review_count": len(decisions),
            "decision_counts": counts,
            "replacement_required_count": counts["REJECT"],
            "status": (
                "READY_TO_APPLY_ALL_REPLACEMENTS"
                if counts["REJECT"] == 0
                else "ADDITIONAL_REPLACEMENTS_REQUIRED"
            ),
            "decisions": decisions,
        }
        return result, {
            RETURN_ZIP_NAME: reader.source_bytes,
            REVIEW_CSV_NAME: csv_bytes,
            IDENTITY_NAME: identity_bytes,
        }
    finally:
        reader.close()


def apply_return(source: Path) -> dict[str, Any]:
    result, snapshots = validate_return(source)
    COMPLETED_DIR.mkdir(parents=True, exist_ok=True)
    paths = {COMPLETED_DIR / name: content for name, content in snapshots.items()}
    paths[DECISIONS_PATH] = (
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
        "decision_counts": result["decision_counts"],
        "decisions_path": str(DECISIONS_PATH),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.input.is_file():
        raise SystemExit(f"second_final_return_missing:{args.input}")
    try:
        result = apply_return(args.input) if args.apply else validate_return(args.input)[0]
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
