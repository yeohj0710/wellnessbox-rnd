from pathlib import Path

from wellnessbox_rnd.interim.bootstrap import bootstrap_operational_evidence
from wellnessbox_rnd.interim.store import InterimStore


def test_bootstrap_is_idempotent_and_keeps_unlicensed_sources_quarantined(
    tmp_path: Path,
) -> None:
    store = InterimStore(tmp_path / "bootstrap.sqlite3")
    store.migrate()
    first = bootstrap_operational_evidence(store)
    second = bootstrap_operational_evidence(store)
    assert first == second
    assert first.sources == 9
    assert first.evidence_passages == 1
    assert first.active_rules == 1
    assert first.quarantined_sources == 8
