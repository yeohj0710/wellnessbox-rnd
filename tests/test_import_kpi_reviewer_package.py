from __future__ import annotations

import json
import zipfile
from datetime import UTC, datetime, timedelta

import pytest

from scripts import import_kpi_reviewer_package as importer


def test_package_reader_keeps_the_validated_zip_snapshot(tmp_path) -> None:
    source = tmp_path / "review.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("value.txt", "original")

    reader = importer.PackageReader(source)
    original_hash = reader.source_sha256
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("value.txt", "replacement")

    try:
        assert reader.read("value.txt") == b"original"
        assert reader.source_sha256 == original_hash
    finally:
        reader.close()


def test_parse_timestamp_requires_timezone() -> None:
    with pytest.raises(ValueError, match="review_timestamp_timezone_missing"):
        importer._parse_timestamp(
            "2026-08-03T12:00:00", case_id="case-1", field="start"
        )


def test_split_answer_deduplicates_and_sorts() -> None:
    assert importer._split_answer("b|a|b") == ["a", "b"]


def test_overlapping_review_intervals_are_detectable() -> None:
    start = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)
    intervals = [
        importer.ReviewedInterval("case-1", start, start + timedelta(seconds=2)),
        importer.ReviewedInterval(
            "case-2", start + timedelta(seconds=1), start + timedelta(seconds=3)
        ),
    ]

    ordered = sorted(intervals, key=lambda item: item.start)

    assert ordered[1].start < ordered[0].end


class _MemoryReader:
    def __init__(self, payload: dict[str, object]):
        self.payload = payload

    def read(self, name: str) -> bytes:
        assert name == "seal_disposal_review.json"
        return json.dumps(self.payload).encode()


class _ReviewerReader:
    def __init__(self, payload: dict[str, str]):
        self.payload = payload

    def read(self, name: str) -> bytes:
        assert name == "reviewer_details.json"
        return json.dumps(self.payload).encode()


def test_load_reviewer_rejects_unregistered_digest_shaped_reference() -> None:
    reader = _ReviewerReader(
        {
            "reviewer_name": "비식별 검토자",
            "reviewer_identity_ref": "registry:op039:sha256:" + "0" * 64,
            "affiliation": "비공개",
            "qualification_stage": importer.EXPECTED_QUALIFICATION_STAGE,
            "review_date": "2026-08-03",
        }
    )

    with pytest.raises(ValueError, match="reviewer_identity_not_traceable"):
        importer._load_reviewer(
            reader,
            trusted_identity_refs={"registry:op039:sha256:" + "a" * 64},
            trusted_reviewer_names={"등록 검토자"},
        )


def test_load_reviewer_rejects_unregistered_alias_without_reference() -> None:
    reader = _ReviewerReader(
        {
            "reviewer_name": "reviewer-001",
            "reviewer_identity_ref": "",
            "affiliation": "비공개",
            "qualification_stage": importer.EXPECTED_QUALIFICATION_STAGE,
            "review_date": "2026-08-03",
        }
    )

    with pytest.raises(ValueError, match="reviewer_identity_not_traceable"):
        importer._load_reviewer(
            reader,
            trusted_identity_refs={"registry:op039:sha256:" + "a" * 64},
            trusted_reviewer_names={"등록 검토자"},
        )


def test_load_seal_disposals_accepts_one_shot_reviewer_authorization() -> None:
    payload = {
        indicator_id: {
            "decision": "DISCARD",
            "reason": "과속 자동 수락 기록",
            "reviewed_by": "검토자",
            "reviewed_at": f"2026-08-03T12:00:0{index}+09:00",
        }
        for index, indicator_id in enumerate(importer.SEAL_INDICATORS)
    }

    result = importer._load_seal_disposals(
        _MemoryReader(payload), reviewer_name="검토자"
    )

    assert set(result) == {"KPI-1", "KPI-5"}
    assert all(entry["decision"] == "DISCARD" for entry in result.values())


def test_load_seal_disposals_rejects_different_reviewer() -> None:
    payload = {
        indicator_id: {
            "decision": "KEEP",
            "reason": "유지 판단",
            "reviewed_by": "다른 이름",
            "reviewed_at": "2026-08-03T12:00:00+09:00",
        }
        for indicator_id in importer.SEAL_INDICATORS
    }

    with pytest.raises(ValueError, match="seal_disposal_reviewer_mismatch:KPI-1"):
        importer._load_seal_disposals(
            _MemoryReader(payload), reviewer_name="검토자"
        )


def test_apply_package_uses_recorded_disposal_without_second_prompt(
    tmp_path, monkeypatch
) -> None:
    workbench_dir = tmp_path / "workbench"
    seal_dir = tmp_path / "seals"
    disposal_dir = tmp_path / "seal_disposals"
    monkeypatch.setattr(importer, "ROOT", tmp_path)
    monkeypatch.setattr(importer, "WORKBENCH_DIR", workbench_dir)
    monkeypatch.setattr(importer, "SEAL_DIR", seal_dir)
    monkeypatch.setattr(importer, "SEAL_DISPOSAL_DIR", disposal_dir)
    monkeypatch.setattr(
        importer, "_trusted_identity_context", lambda: (set(), {"검토자"})
    )

    staged = {}
    for indicator_id in importer.INDICATORS:
        workbench = importer.Workbench(indicator_id, [], {})
        staged[indicator_id] = workbench
        importer.save_workbench(importer._workbench_path(indicator_id), workbench)
    for indicator_id in importer.SEAL_INDICATORS:
        seal_path = (
            seal_dir
            / "discarded"
            / f"{importer._slug(indicator_id)}_reference_seal_v1.json"
        )
        seal_path.parent.mkdir(parents=True, exist_ok=True)
        seal_path.write_text(
            json.dumps(
                {"indicator_id": indicator_id, "seal_sha256": f"seal-{indicator_id}"}
            ),
            encoding="utf-8",
        )

    package_dir = tmp_path / "completed_package"
    package_dir.mkdir()
    (package_dir / "reviewer_details.json").write_text(
        json.dumps(
            {
                "reviewer_name": "검토자",
                "affiliation": "연구팀",
                "qualification_stage": importer.EXPECTED_QUALIFICATION_STAGE,
                "review_date": "2026-08-03",
            }
        ),
        encoding="utf-8",
    )
    (package_dir / "seal_disposal_review.json").write_text(
        json.dumps(
            {
                indicator_id: {
                    "decision": "DISCARD",
                    "reason": "과속 자동 수락 기록",
                    "reviewed_by": "검토자",
                    "reviewed_at": "2026-08-03T12:00:00+09:00",
                }
                for indicator_id in importer.SEAL_INDICATORS
            }
        ),
        encoding="utf-8",
    )
    reviewer = {
        "reviewer_name": "검토자",
        "reviewer_identity_ref": "",
    }
    seal_disposals = {
        indicator_id: {
            "decision": "DISCARD",
            "reason": "과속 자동 수락 기록",
            "reviewed_by": "검토자",
            "reviewed_at": "2026-08-03T12:00:00+09:00",
        }
        for indicator_id in importer.SEAL_INDICATORS
    }
    monkeypatch.setattr(
        importer,
        "_validate_reader",
        lambda _: (
            staged,
            {
                "status": "READY_TO_IMPORT",
                "seal_disposal_decisions": {"KPI-1": "DISCARD", "KPI-5": "DISCARD"},
                "replacement_required_count": 2,
            },
            reviewer,
            seal_disposals,
        ),
    )

    report = importer.apply_package(package_dir)

    assert report["status"] == "IMPORTED_REPLACEMENTS_REQUIRED"
    assert report["discarded_seals"] == ["KPI-1", "KPI-5"]
    for indicator_id in importer.SEAL_INDICATORS:
        applied = importer.load_workbench(importer._workbench_path(indicator_id))
        assert len(applied.seal_disposals) == 1
        assert applied.seal_disposals[0]["discarded_by"] == "검토자"
