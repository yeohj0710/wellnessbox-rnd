import json
from pathlib import Path

from wellnessbox_rnd.interim.importer import import_interim_package
from wellnessbox_rnd.interim.manifest import APPROVED_SOURCE_ROOT
from wellnessbox_rnd.interim.reports import generate_release, verify_release
from wellnessbox_rnd.interim.store import InterimStore

SOURCE_PACKAGE = APPROVED_SOURCE_ROOT
RETRAINED_PACKAGE = Path("artifacts/tips/interim/retrained")


def test_release_contains_truthful_kpi_and_verifiable_manifest(tmp_path: Path) -> None:
    store = InterimStore(tmp_path / "release.sqlite3")
    store.migrate()
    import_interim_package(store, SOURCE_PACKAGE, max_records_per_split=2)
    summary = generate_release(
        store,
        repo_root=tmp_path,
        source_package=SOURCE_PACKAGE,
        retrained_package=RETRAINED_PACKAGE,
    )
    assert summary.proxy_kpis_passed == 7
    assert summary.proxy_kpis_total == 7
    manifest = tmp_path / "artifacts" / "tips" / "interim" / "evidence_manifest.json"
    result = verify_release(manifest)
    assert result["valid"] is True
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["real_research_completion"] is False
    report = (tmp_path / "docs" / "tips" / "interim" / "INTERIM_RESEARCH_REPORT.md").read_text(
        encoding="utf-8"
    )
    assert "7/7" in report
    assert "실제 연구 완료 여부는 `false`" in report
    current_audit = (tmp_path / "docs" / "tips" / "CURRENT_REPO_AUDIT.md").read_text(
        encoding="utf-8"
    )
    assert "빈 기준 집합 1,456건 제외" in current_audit
    assert "유효 기준 집합 3,544건 평가" in current_audit
