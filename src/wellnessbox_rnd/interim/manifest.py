from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ARTIFACT_DIRECTORY = Path("artifacts/interim_proxy_research_full")
EXPECTED_SPLITS = {
    "train": 120_000,
    "validation": 15_000,
    "calibration": 10_000,
    "blind_test": 5_000,
}
APPROVED_SOURCE_ROOT = Path(
    "C:/dev/wellnessbox-rnd/etc/source_packages/wellnessbox_tips_interim_simulation_package"
)
APPROVED_SOURCE_MANIFEST_SHA256 = "2a430ac5899544885d4be923213b50d526ffd0df016b2b34bf57a077d4c650a4"


@dataclass(frozen=True)
class ManifestValidation:
    valid: bool
    artifact_root: Path
    manifest_sha256: str
    checked_files: int
    failures: list[str]
    split_counts: dict[str, int]
    total_records: int
    proxy_kpis_passed: int
    proxy_kpis_total: int
    model_sha256: str


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def resolve_artifact_root(package_root: Path) -> Path:
    root = package_root.resolve()
    if (root / "evidence_manifest.json").is_file():
        return root
    artifact_root = root / ARTIFACT_DIRECTORY
    if not artifact_root.is_dir():
        raise FileNotFoundError(f"interim_artifact_root_missing:{artifact_root}")
    return artifact_root


def count_gzip_jsonl(path: Path) -> int:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def validate_interim_package(package_root: Path) -> ManifestValidation:
    artifact_root = resolve_artifact_root(package_root)
    manifest_path = artifact_root / "evidence_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("files", [])
    failures: list[str] = []

    if package_root.resolve() == APPROVED_SOURCE_ROOT.resolve() and (
        manifest.get("manifest_sha256") != APPROVED_SOURCE_MANIFEST_SHA256
    ):
        failures.append("approved_source_manifest_trust_root_mismatch")

    if manifest.get("file_count") != len(entries):
        failures.append(f"manifest_file_count:{manifest.get('file_count')}!={len(entries)}")

    for entry in entries:
        relative = str(entry.get("path", ""))
        path = artifact_root / relative
        if not path.is_file():
            failures.append(f"missing:{relative}")
            continue
        actual_size = path.stat().st_size
        if actual_size != int(entry.get("size_bytes", -1)):
            failures.append(f"size:{relative}:{actual_size}")
        actual_hash = sha256_file(path)
        if actual_hash != str(entry.get("sha256", "")).lower():
            failures.append(f"sha256:{relative}:{actual_hash}")

    calculated_manifest_hash = sha256_text(canonical_json(entries))
    if calculated_manifest_hash != manifest.get("manifest_sha256"):
        failures.append(f"manifest_sha256:{calculated_manifest_hash}")

    split_counts = {
        split: count_gzip_jsonl(artifact_root / "datasets" / f"proxy_cases.{split}.jsonl.gz")
        for split in EXPECTED_SPLITS
    }
    for split, expected in EXPECTED_SPLITS.items():
        if split_counts[split] != expected:
            failures.append(f"split_count:{split}:{split_counts[split]}!={expected}")

    kpi_report = json.loads(
        (artifact_root / "evals" / "proxy_kpi_report.json").read_text(encoding="utf-8")
    )
    passed = int(kpi_report.get("proxy_kpis_passed", 0))
    total = int(kpi_report.get("proxy_kpis_total", 0))
    if passed != 7 or total != 7 or not kpi_report.get("proxy_research_completion"):
        failures.append(f"proxy_kpis:{passed}/{total}")

    model_hash = sha256_file(artifact_root / "model" / "proxy_recommendation_model.joblib")
    return ManifestValidation(
        valid=not failures,
        artifact_root=artifact_root,
        manifest_sha256=str(manifest.get("manifest_sha256", "")),
        checked_files=len(entries),
        failures=failures,
        split_counts=split_counts,
        total_records=sum(split_counts.values()),
        proxy_kpis_passed=passed,
        proxy_kpis_total=total,
        model_sha256=model_hash,
    )
