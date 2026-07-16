from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from wellnessbox_rnd.interim.connectors import OFFICIAL_SOURCE_ADAPTERS
from wellnessbox_rnd.interim.evidence import EvidenceRegistry
from wellnessbox_rnd.interim.store import InterimStore

ORIGINAL_PLAN_PAGE_26_URI = (
    "urn:sha256:31291e6f93977fa2d5d083d0161743c49debef25caf12dccf6edc7fa1c2197d4"
    "#page=26"
)


@dataclass(frozen=True)
class BootstrapSummary:
    sources: int
    evidence_passages: int
    active_rules: int
    quarantined_sources: int


def bootstrap_operational_evidence(store: InterimStore) -> BootstrapSummary:
    registry = EvidenceRegistry(store)
    plan_source = registry.register_source(
        source_id="tips-original-plan-p26",
        source_tier="internal_governance",
        title="TIPS original plan safety gate, page 26",
        canonical_uri=ORIGINAL_PLAN_PAGE_26_URI,
        license_status="APPROVED_INTERNAL",
        metadata={"scope": "evaluation_policy_only", "clinical_claims": False},
    )
    passage = registry.add_passage(
        source_id=plan_source.identifier,
        passage_text=(
            "Interim evaluation policy: critical safety false negatives must remain zero; "
            "BLOCK and STOP_AND_ESCALATE outcomes are non-overridable."
        ),
        approved_for_safety=True,
    )
    if not store.scalar(
        "select count(*) from safety_rules where rule_version_id='SAFE-GATE-001:v1'"
    ):
        registry.activate_rule(
            rule_id="SAFE-GATE-001",
            version=1,
            severity="CRITICAL",
            action="BLOCK",
            predicate={"hard_false_negative": True},
            evidence_ids=[passage.identifier],
            valid_from=datetime.now(UTC).isoformat(),
        )

    for name, url in OFFICIAL_SOURCE_ADAPTERS.items():
        registry.register_source(
            source_id=f"adapter-{name}",
            source_tier="official_adapter_contract",
            title=f"{name} official adapter contract",
            canonical_uri=url,
            license_status="UNKNOWN",
            metadata={
                "adapter_only": True,
                "content_ingested": False,
                "gate": "license_and_environment_review",
            },
        )

    return BootstrapSummary(
        sources=int(store.scalar("select count(*) from source_registry")),
        evidence_passages=int(store.scalar("select count(*) from evidence_passages")),
        active_rules=int(
            store.scalar("select count(*) from safety_rules where review_status='ACTIVE'")
        ),
        quarantined_sources=int(
            store.scalar(
                "select count(*) from source_registry where metadata_json like '%quarantined%true%'"
            )
        ),
    )
