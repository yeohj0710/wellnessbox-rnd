from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT.parent / "wellnessbox"
MANIFEST_PATH = ROOT / "data/original_plan/requirements_manifest_v1.json"
LEDGER_PATH = ROOT / "data/original_plan/evidence/evidence_verification_ledger_v1.json"
REPORT_ROOT = ROOT / "docs/original_plan/research_reports"
TARGET_NUMBERS = {*range(31, 79), 105, 106, 117, 118, 119}
REPOSITORY_PREFIXES = {
    "wellnessbox-rnd/": ROOT,
    "wellnessbox/": WEB_ROOT,
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _requirements(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        requirement
        for group in manifest["groups"]
        for requirement in group["requirements"]
        if int(requirement["requirement_id"].split("-")[1]) in TARGET_NUMBERS
    ]


def _resolve_reference(reference: str) -> Path:
    for prefix, repository_root in REPOSITORY_PREFIXES.items():
        if reference.startswith(prefix):
            return repository_root / reference.removeprefix(prefix)
    raise ValueError(f"저장소 파일 경로가 아닙니다: {reference}")


def _expected_pairs(
    requirements: list[dict[str, Any]],
) -> tuple[dict[tuple[str, str], list[str]], int]:
    pairs: dict[tuple[str, str], set[str]] = {}
    reference_count = 0
    for requirement in requirements:
        requirement_id = requirement["requirement_id"]
        for evidence_type, references in requirement["evidence"].items():
            for reference in references:
                if not reference.startswith(tuple(REPOSITORY_PREFIXES)):
                    continue
                reference_count += 1
                pairs.setdefault((requirement_id, reference), set()).add(evidence_type)
    return {pair: sorted(types) for pair, types in pairs.items()}, reference_count


def verify() -> dict[str, Any]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    requirements = _requirements(manifest)
    expected_pairs, reference_count = _expected_pairs(requirements)
    judgments = ledger["judgments"]
    actual_pairs = {
        (row["op_id"], row["cited_path"]): row["evidence_types"] for row in judgments
    }
    if len(actual_pairs) != len(judgments):
        raise ValueError("근거 원장에 중복 OP-경로 행이 있습니다.")
    if actual_pairs != expected_pairs:
        missing = sorted(set(expected_pairs) - set(actual_pairs))
        extra = sorted(set(actual_pairs) - set(expected_pairs))
        raise ValueError(
            f"manifest와 근거 원장의 경로가 다릅니다: "
            f"missing={missing}, extra={extra}"
        )
    if ledger["manifest"]["sha256"] != _sha256(MANIFEST_PATH):
        raise ValueError("근거 원장의 manifest hash가 현재 파일과 다릅니다.")

    report_hashes = ledger["reports"]
    for requirement in requirements:
        requirement_id = requirement["requirement_id"]
        report_path = REPORT_ROOT / f"{requirement_id}.md"
        expected_report = report_hashes[requirement_id]
        if expected_report["sha256"] != _sha256(report_path):
            raise ValueError(f"보고서 hash가 근거 원장과 다릅니다: {requirement_id}")

    for row in judgments:
        path = _resolve_reference(row["cited_path"])
        if not path.is_file() or row["exists"] is not True:
            raise ValueError(f"등록 근거 파일이 없습니다: {row['op_id']} {row['cited_path']}")
        if row["file_sha256"] != _sha256(path):
            raise ValueError(
                f"등록 근거 파일 hash가 바뀌었습니다: "
                f"{row['op_id']} {row['cited_path']}"
            )
        if row["content_match"] is not True or not row["note"].strip():
            raise ValueError(f"내용 판정이 미완료입니다: {row['op_id']} {row['cited_path']}")
        report_text = (REPORT_ROOT / f"{row['op_id']}.md").read_text(encoding="utf-8")
        if row["report_references_path_verbatim"] != (row["cited_path"] in report_text):
            raise ValueError(
                f"보고서 경로 원문 인용 판정이 다릅니다: "
                f"{row['op_id']} {row['cited_path']}"
            )

    computed_summary = {
        "report_count": len(requirements),
        "manifest_reference_count": reference_count,
        "unique_op_path_count": len(judgments),
        "unique_file_count": len({row["cited_path"] for row in judgments}),
        "missing_path_count": sum(row["exists"] is not True for row in judgments),
        "content_mismatch_count": sum(
            row["content_match"] is not True for row in judgments
        ),
        "verbatim_path_reference_count": sum(
            row["report_references_path_verbatim"] is True for row in judgments
        ),
    }
    if ledger["summary"] != computed_summary:
        raise ValueError(
            f"근거 원장 요약이 상세 행과 다릅니다: "
            f"recorded={ledger['summary']}, computed={computed_summary}"
        )
    return {"status": "READY", **computed_summary}


def main() -> int:
    print(json.dumps(verify(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
