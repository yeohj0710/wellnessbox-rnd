"""Metrics and metadata helpers."""

from importlib import import_module

__all__ = [
    "PRO_BASELINE_STANDARDIZATION_VERSION_V1",
    "PRO_IMPROVEMENT_SUMMARY_VERSION_V1",
    "PRO_INSTRUMENT_CONTRACT_VERSION_V1",
    "PROBaselineDistributionV1",
    "PROBaselineScoreObservationV1",
    "PRODomainNormV1",
    "PRODomainFormSchemaV1",
    "PROFormResponseV1",
    "PROFormSchemaV1",
    "PROImprovementSummaryV1",
    "PROInstrumentResponseV1",
    "PROInstrumentScoreV1",
    "PROStandardizedScoreV1",
    "PROItemSchemaV1",
    "PROZScoreSnapshotV1",
    "build_default_pro_domain_norms_v1",
    "build_default_pro_form_schema_v1",
    "build_pro_baseline_distribution_v1",
    "coerce_baseline_followup_pro_event_v1",
    "load_pro_instrument_scoring_contract_v1",
    "score_pro_instrument_response_v1",
    "standardize_pro_instrument_score_v1",
    "summarize_pro_form_contract_v1",
    "summarize_pro_improvement_from_event_v1",
    "transform_pro_response_to_zscores_v1",
    "validate_pro_improvement_summary_from_event_v1",
    "validate_pro_domain_norms_v1",
    "validate_pro_form_response_v1",
]


def __getattr__(name: str):
    if name in __all__:
        module = import_module("wellnessbox_rnd.metrics.pro_scoring")
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

