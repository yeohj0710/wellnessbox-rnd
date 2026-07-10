from pathlib import Path

import pytest

from wellnessbox_rnd.interim.evidence import EvidenceRegistry
from wellnessbox_rnd.interim.store import InterimStore


def _registry(tmp_path: Path) -> EvidenceRegistry:
    store = InterimStore(tmp_path / "evidence.sqlite3")
    store.migrate()
    return EvidenceRegistry(store)


def test_license_gate_quarantines_unapproved_source(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    result = registry.register_source(
        source_id="licensed-1",
        source_tier="secondary",
        title="Licensed source",
        canonical_uri="https://example.test/source",
        license_status="UNKNOWN",
    )
    assert result.quarantined is True
    with pytest.raises(ValueError, match="quarantined_source"):
        registry.add_passage(
            source_id="licensed-1", passage_text="critical", approved_for_safety=True
        )


def test_critical_rule_requires_approved_evidence(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    registry.register_source(
        source_id="ods",
        source_tier="official",
        title="ODS",
        canonical_uri="https://ods.od.nih.gov/",
        license_status="PUBLIC_DOMAIN",
    )
    passage = registry.add_passage(
        source_id="ods", passage_text="Do not exceed the upper limit.", approved_for_safety=True
    )
    rule_id = registry.activate_rule(
        rule_id="SAFE-UL-001",
        version=1,
        severity="CRITICAL",
        action="BLOCK",
        predicate={"above_ul": True},
        evidence_ids=[passage.identifier],
        valid_from="2026-01-01T00:00:00+00:00",
    )
    assert rule_id == "SAFE-UL-001:v1"


def test_source_content_change_preserves_previous_hash_in_metadata(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    common = {
        "source_id": "source-1",
        "source_tier": "official",
        "canonical_uri": "https://example.test/",
        "license_status": "OPEN",
    }
    first = registry.register_source(title="v1", **common)
    second = registry.register_source(title="v2", **common)
    row = registry.store.rows("select metadata_json from source_registry")[0][0]
    assert first.checksum != second.checksum
    assert first.checksum in row
