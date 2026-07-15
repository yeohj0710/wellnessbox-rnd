import hashlib
import json
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


def test_source_content_change_stays_quarantined_on_identical_resync(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    common = {
        "source_id": "source-1",
        "source_tier": "official",
        "canonical_uri": "https://example.test/",
        "license_status": "OPEN",
    }
    first = registry.register_source(title="v1", **common)
    changed = registry.register_source(title="v2", **common)
    repeated = registry.register_source(title="v2", **common)
    metadata = registry.store.rows(
        "select metadata_json from source_registry where source_id='source-1'"
    )[0][0]

    assert changed.quarantined is True
    assert repeated.quarantined is True
    assert repeated.reason == "content_changed_requires_review"
    assert first.checksum in metadata


def test_legacy_source_checksum_upgrades_without_false_content_quarantine(
    tmp_path: Path,
) -> None:
    registry = _registry(tmp_path)
    legacy_payload = {
        "source_id": "source-legacy",
        "title": "Legacy source",
        "canonical_uri": "https://example.test/legacy",
        "effective_at": None,
        "retired_at": None,
        "metadata": {},
    }
    legacy_checksum = hashlib.sha256(
        json.dumps(
            legacy_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    with registry.store.transaction() as connection:
        connection.execute(
            "insert into source_registry values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "source-legacy",
                "official",
                "Legacy source",
                "https://example.test/legacy",
                "OPEN",
                None,
                None,
                legacy_checksum,
                "PROXY_GOLD_SIMULATION",
                "{}",
            ),
        )

    result = registry.register_source(
        source_id="source-legacy",
        source_tier="official",
        title="Legacy source",
        canonical_uri="https://example.test/legacy",
        license_status="OPEN",
    )

    assert result.checksum != legacy_checksum
    assert result.quarantined is False
    assert result.reason is None


def test_legacy_checksum_upgrade_still_quarantines_tier_change(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    legacy_payload = {
        "source_id": "source-legacy",
        "title": "Legacy source",
        "canonical_uri": "https://example.test/legacy",
        "effective_at": None,
        "retired_at": None,
        "metadata": {},
    }
    legacy_checksum = hashlib.sha256(
        json.dumps(
            legacy_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    with registry.store.transaction() as connection:
        connection.execute(
            "insert into source_registry values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "source-legacy",
                "secondary",
                "Legacy source",
                "https://example.test/legacy",
                "OPEN",
                None,
                None,
                legacy_checksum,
                "PROXY_GOLD_SIMULATION",
                "{}",
            ),
        )

    result = registry.register_source(
        source_id="source-legacy",
        source_tier="official",
        title="Legacy source",
        canonical_uri="https://example.test/legacy",
        license_status="OPEN",
    )

    assert result.quarantined is True
    assert result.reason == "content_changed_requires_review"


def test_passage_without_span_metadata_keeps_legacy_content_addressed_id(
    tmp_path: Path,
) -> None:
    registry = _registry(tmp_path)
    registry.register_source(
        source_id="source-1",
        source_tier="official",
        title="Source",
        canonical_uri="https://example.test/source",
        license_status="OPEN",
    )

    passage = registry.add_passage(
        source_id="source-1",
        passage_text="Legacy passage identity",
    )
    expected_checksum = hashlib.sha256(b"Legacy passage identity").hexdigest()

    assert passage.checksum == expected_checksum
    assert passage.identifier == f"ev_{expected_checksum[:20]}"
