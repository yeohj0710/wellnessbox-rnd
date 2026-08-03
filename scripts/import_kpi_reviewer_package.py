"""Validate and atomically import completed offline KPI review CSV files."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
import zipfile
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_kpi_reviewer_package import (  # noqa: E402
    CSV_FIELDS,
    INDICATORS,
    build_rows,
)
from wellnessbox_rnd.evals.adaptive_answer_key_review import (  # noqa: E402
    build_adaptive_review_plan,
    build_blind_ai_review_packet,
)
from wellnessbox_rnd.evals.answer_key_integrity import (  # noqa: E402
    MIN_SECONDS_PER_DECISION,
)
from wellnessbox_rnd.evals.answer_key_workbench import (  # noqa: E402
    Workbench,
    decide,
    discard_seal_with_audit_trail,
    load_workbench,
    save_workbench,
)

WORKBENCH_DIR = ROOT / "data/original_plan/kpi/workbench"
SEAL_DIR = ROOT / "data/original_plan/kpi/seals"
SEAL_DISPOSAL_DIR = ROOT / "data/original_plan/kpi/seal_disposals"
EXPECTED_QUALIFICATION_STAGE = "pharmacist_candidate_preliminary_safety_review"
IMMUTABLE_FIELDS = CSV_FIELDS[:10]
SEAL_INDICATORS = ("KPI-1", "KPI-5")


def _slug(indicator_id: str) -> str:
    return indicator_id.lower().replace("-", "")


def _workbench_path(indicator_id: str) -> Path:
    return WORKBENCH_DIR / f"{_slug(indicator_id)}_workbench_v1.json"


def _seal_candidate_path(indicator_id: str) -> Path:
    name = f"{_slug(indicator_id)}_reference_seal_v1.json"
    active = SEAL_DIR / name
    legacy = SEAL_DIR / "discarded" / name
    return active if active.is_file() else legacy


def _seal_disposal_history_path(indicator_id: str) -> Path:
    return SEAL_DISPOSAL_DIR / f"{_slug(indicator_id)}_seal_disposals_v1.json"


class PackageReader:
    def __init__(self, source: Path):
        self.source = source
        self.archive = zipfile.ZipFile(source) if source.is_file() else None

    def read(self, name: str) -> bytes:
        if self.archive is not None:
            try:
                return self.archive.read(name)
            except KeyError as exc:
                raise ValueError(f"review_package_file_missing:{name}") from exc
        path = self.source / name
        if not path.is_file():
            raise ValueError(f"review_package_file_missing:{name}")
        return path.read_bytes()

    def close(self) -> None:
        if self.archive is not None:
            self.archive.close()


@dataclass(frozen=True)
class ReviewedInterval:
    case_id: str
    start: datetime
    end: datetime


def _parse_timestamp(value: str, *, case_id: str, field: str) -> datetime:
    text = value.strip()
    if not text:
        raise ValueError(f"review_timestamp_missing:{case_id}:{field}")
    try:
        stamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"review_timestamp_invalid:{case_id}:{field}") from exc
    if stamp.tzinfo is None:
        raise ValueError(f"review_timestamp_timezone_missing:{case_id}:{field}")
    return stamp


def _split_answer(value: str) -> list[str]:
    return sorted({item.strip() for item in value.split("|") if item.strip()})


def _answer_vocabulary(workbench: Workbench) -> set[str]:
    packet = build_blind_ai_review_packet(
        workbench,
        required_blinded_from=workbench.ai_review.get(
            "required_blinded_from", []
        ),
    )
    return set(packet["answer_vocabulary"])


def _load_rows(reader: PackageReader, indicator_id: str) -> list[dict[str, str]]:
    name = f"{_slug(indicator_id)}_review.csv"
    text = reader.read(name).decode("utf-8-sig")
    csv_reader = csv.DictReader(io.StringIO(text))
    if tuple(csv_reader.fieldnames or ()) != CSV_FIELDS:
        raise ValueError(f"review_csv_columns_changed:{indicator_id}")
    return list(csv_reader)


def _load_reviewer(reader: PackageReader) -> dict[str, str]:
    payload = json.loads(reader.read("reviewer_details.json").decode("utf-8"))
    required = ("reviewer_name", "affiliation", "qualification_stage", "review_date")
    for field in required:
        if not str(payload.get(field, "")).strip():
            raise ValueError(f"reviewer_detail_missing:{field}")
    if payload["qualification_stage"] != EXPECTED_QUALIFICATION_STAGE:
        raise ValueError("reviewer_qualification_stage_invalid")
    try:
        datetime.fromisoformat(str(payload["review_date"]))
    except ValueError as exc:
        raise ValueError("review_date_invalid") from exc
    return {key: str(value).strip() for key, value in payload.items()}


def _load_seal_disposals(
    reader: PackageReader, *, reviewer_name: str
) -> dict[str, dict[str, str]]:
    payload = json.loads(reader.read("seal_disposal_review.json").decode("utf-8"))
    if set(payload) != set(SEAL_INDICATORS):
        raise ValueError("seal_disposal_indicators_invalid")
    normalized: dict[str, dict[str, str]] = {}
    for indicator_id in SEAL_INDICATORS:
        source = payload[indicator_id]
        if not isinstance(source, dict):
            raise ValueError(f"seal_disposal_entry_invalid:{indicator_id}")
        entry = {key: str(value).strip() for key, value in source.items()}
        decision = entry.get("decision", "")
        if decision not in {"DISCARD", "KEEP"}:
            raise ValueError(f"seal_disposal_decision_invalid:{indicator_id}")
        for field in ("reason", "reviewed_by", "reviewed_at"):
            if not entry.get(field):
                raise ValueError(f"seal_disposal_detail_missing:{indicator_id}:{field}")
        if entry["reviewed_by"] != reviewer_name:
            raise ValueError(f"seal_disposal_reviewer_mismatch:{indicator_id}")
        _parse_timestamp(
            entry["reviewed_at"], case_id=indicator_id, field="seal_reviewed_at"
        )
        normalized[indicator_id] = entry
    return normalized


def validate_package(source: Path) -> tuple[dict[str, Workbench], dict[str, Any]]:
    reader = PackageReader(source)
    try:
        reviewer = _load_reviewer(reader)
        seal_disposals = _load_seal_disposals(
            reader, reviewer_name=reviewer["reviewer_name"]
        )
        staged: dict[str, Workbench] = {}
        intervals: list[ReviewedInterval] = []
        counts: dict[str, int] = {}
        choice_counts: dict[str, dict[str, int]] = {}
        for indicator_id in INDICATORS:
            expected_rows, _ = build_rows(indicator_id)
            rows = _load_rows(reader, indicator_id)
            if len(rows) != len(expected_rows):
                raise ValueError(f"review_csv_case_count_changed:{indicator_id}")
            workbench = deepcopy(load_workbench(_workbench_path(indicator_id)))
            if workbench.decisions:
                raise ValueError(f"workbench_already_has_decisions:{indicator_id}")
            draft_by_id = {draft.case_id: draft for draft in workbench.drafts}
            vocabulary = _answer_vocabulary(workbench)
            seen: set[str] = set()
            indicator_choices = {choice: 0 for choice in ("A", "B", "CUSTOM", "REJECT")}
            for row, expected in zip(rows, expected_rows, strict=True):
                case_id = row["case_id"].strip()
                if case_id in seen:
                    raise ValueError(f"review_case_id_duplicated:{case_id}")
                seen.add(case_id)
                for field in IMMUTABLE_FIELDS:
                    if row[field] != expected[field]:
                        raise ValueError(f"review_source_field_changed:{case_id}:{field}")

                choice = row["검토_선택"].strip().upper()
                if choice not in {"A", "B", "CUSTOM", "REJECT"}:
                    raise ValueError(f"review_choice_invalid:{case_id}")
                indicator_choices[choice] += 1
                if choice == "A":
                    final_answer: list[str] | None = _split_answer(expected["안_A"])
                elif choice == "B":
                    final_answer = _split_answer(expected["안_B"])
                elif choice == "CUSTOM":
                    final_answer = _split_answer(row["최종_답"])
                    if not final_answer:
                        raise ValueError(f"custom_answer_empty:{case_id}")
                else:
                    final_answer = None
                if final_answer is not None:
                    outside = sorted(set(final_answer) - vocabulary)
                    if outside:
                        raise ValueError(
                            f"final_answer_outside_vocabulary:{case_id}:{'|'.join(outside)}"
                        )

                start = _parse_timestamp(
                    row["검토_시작_시각"], case_id=case_id, field="start"
                )
                end = _parse_timestamp(
                    row["검토_종료_시각"], case_id=case_id, field="end"
                )
                duration = (end - start).total_seconds()
                if not math.isfinite(duration) or duration < MIN_SECONDS_PER_DECISION:
                    raise ValueError(f"review_duration_too_short:{case_id}")
                intervals.append(ReviewedInterval(case_id, start, end))
                note_parts = [f"offline_review_choice:{choice}"]
                if row["검토_메모"].strip():
                    note_parts.append(row["검토_메모"].strip())
                workbench.decisions[case_id] = decide(
                    draft=draft_by_id[case_id],
                    final_answer=final_answer,
                    decided_by=reviewer["reviewer_name"],
                    decided_at=end.isoformat(),
                    note="; ".join(note_parts),
                    review_duration_seconds=duration,
                )
            plan = build_adaptive_review_plan(workbench)
            if plan["pending_required_detail_ids"]:
                raise ValueError(f"required_review_still_pending:{indicator_id}")
            staged[indicator_id] = workbench
            counts[indicator_id] = len(rows)
            choice_counts[indicator_id] = indicator_choices

        ordered = sorted(intervals, key=lambda item: item.start)
        for previous, current in zip(ordered, ordered[1:], strict=False):
            if current.start < previous.end:
                raise ValueError(
                    f"review_intervals_overlap:{previous.case_id}:{current.case_id}"
                )
        return staged, {
            "status": "READY_TO_IMPORT",
            "reviewer_name": reviewer["reviewer_name"],
            "qualification_stage": reviewer["qualification_stage"],
            "review_count": sum(counts.values()),
            "indicator_counts": counts,
            "choice_counts": choice_counts,
            "replacement_required_counts": {
                indicator_id: choices["REJECT"]
                for indicator_id, choices in choice_counts.items()
            },
            "replacement_required_count": sum(
                choices["REJECT"] for choices in choice_counts.values()
            ),
            "seal_disposal_decisions": {
                indicator_id: entry["decision"]
                for indicator_id, entry in seal_disposals.items()
            },
        }
    finally:
        reader.close()


def _disposal_mutation_paths(
    seal_disposals: dict[str, dict[str, str]],
) -> dict[str, dict[str, Path]]:
    paths: dict[str, dict[str, Path]] = {}
    for indicator_id, entry in seal_disposals.items():
        if entry["decision"] != "DISCARD":
            continue
        candidate = _seal_candidate_path(indicator_id)
        if not candidate.is_file():
            raise ValueError(f"seal_disposal_candidate_missing:{indicator_id}")
        seal = json.loads(candidate.read_text(encoding="utf-8"))
        seal_sha256 = str(seal.get("seal_sha256", "")).strip()
        if not seal_sha256:
            raise ValueError(f"active_seal_sha256_missing:{indicator_id}")
        slug = _slug(indicator_id)
        archive = SEAL_DISPOSAL_DIR / "archive"
        paths[indicator_id] = {
            "candidate": candidate,
            "history": _seal_disposal_history_path(indicator_id),
            "archived_seal": archive / "seals" / f"{slug}_reference_seal_{seal_sha256}.json",
            "archived_workbench": archive
            / "workbenches"
            / f"{slug}_workbench_{seal_sha256}.json",
        }
    return paths


def _restore_files(snapshots: dict[Path, bytes | None]) -> None:
    for path, content in snapshots.items():
        if content is None:
            path.unlink(missing_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)


def apply_package(source: Path) -> dict[str, Any]:
    staged, report = validate_package(source)
    reader = PackageReader(source)
    try:
        reviewer = _load_reviewer(reader)
        seal_disposals = _load_seal_disposals(
            reader, reviewer_name=reviewer["reviewer_name"]
        )
    finally:
        reader.close()
    disposal_paths = _disposal_mutation_paths(seal_disposals)
    mutation_paths = {
        *(_workbench_path(indicator_id) for indicator_id in INDICATORS),
        *(
            path
            for indicator_paths in disposal_paths.values()
            for path in indicator_paths.values()
        ),
    }
    snapshots = {
        path: path.read_bytes() if path.is_file() else None for path in mutation_paths
    }
    try:
        for indicator_id, paths in disposal_paths.items():
            entry = seal_disposals[indicator_id]
            record = discard_seal_with_audit_trail(
                active_seal_path=paths["candidate"],
                workbench_path=_workbench_path(indicator_id),
                history_path=paths["history"],
                archive_dir=SEAL_DISPOSAL_DIR / "archive",
                record_root=ROOT,
                discarded_by=entry["reviewed_by"],
                reason=entry["reason"],
                discarded_at=entry["reviewed_at"],
            )
            staged[indicator_id].seal_disposals.append(record)
        for indicator_id in INDICATORS:
            save_workbench(_workbench_path(indicator_id), staged[indicator_id])
    except Exception:
        _restore_files(snapshots)
        raise
    replacement_count = int(report.get("replacement_required_count", 0))
    return {
        **report,
        "status": (
            "IMPORTED_REPLACEMENTS_REQUIRED"
            if replacement_count
            else "IMPORTED"
        ),
        "discarded_seals": sorted(disposal_paths),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.input.exists():
        raise SystemExit(f"검토 자료를 찾지 못했습니다: {args.input}")
    try:
        if args.apply:
            report = apply_package(args.input)
        else:
            _, report = validate_package(args.input)
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
