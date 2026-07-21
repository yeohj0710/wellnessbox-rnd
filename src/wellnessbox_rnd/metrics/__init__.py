"""Metrics and metadata helpers."""

from importlib import import_module

__all__ = [
    "PRO_BASELINE_STANDARDIZATION_VERSION_V1",
    "PRO_FOLLOWUP_ADHERENCE_THRESHOLD_V1",
    "PRO_FOLLOWUP_EFFECT_INTERPRETATION_SCHEMA_VERSION_V1",
    "PRO_FOLLOWUP_EVENT_SCHEMA_VERSION_V1",
    "PRO_FOLLOWUP_INTERPRETATION_CONTRACT_VERSION_V1",
    "PRO_GROUP_EFFECT_CONTRACT_VERSION_V1",
    "PRO_GROUP_EFFECT_SUMMARY_SCHEMA_VERSION_V1",
    "PRO_IMPROVEMENT_SUMMARY_VERSION_V1",
    "PRO_INSTRUMENT_CONTRACT_VERSION_V1",
    "PROBaselineDistributionV1",
    "PROBaselineScoreObservationV1",
    "PROAdherenceWindowV1",
    "PROAdverseEventContextV1",
    "PRODomainNormV1",
    "PRODomainFormSchemaV1",
    "PROFormResponseV1",
    "PROFormSchemaV1",
    "PROFollowUpEffectInterpretationV1",
    "PROFollowUpEventV1",
    "PROFollowUpInterpretationContractV1",
    "PROGroupConfidenceIntervalV1",
    "PROGroupEffectContractV1",
    "PROGroupEffectSummaryV1",
    "PROGroupEstimateV1",
    "PROCorrectionRecalculationResultV1",
    "PRORecommendationEffectLineageV1",
    "PROImprovementSummaryV1",
    "PROInstrumentResponseV1",
    "PROInstrumentScoreV1",
    "PROInstrumentObservedChangeV1",
    "PROPlanActionDecisionV1",
    "PROPlanActionV1",
    "PROStandardizedScoreV1",
    "PROItemSchemaV1",
    "PROZScoreSnapshotV1",
    "build_default_pro_domain_norms_v1",
    "build_default_pro_form_schema_v1",
    "build_pro_baseline_distribution_v1",
    "build_pro_group_effect_summary_v1",
    "correct_and_recalculate_pro_followup_v1",
    "coerce_baseline_followup_pro_event_v1",
    "interpret_pro_followup_effect_v1",
    "decide_pro_plan_action_v1",
    "is_versioned_pro_followup_payload_v1",
    "load_pro_followup_interpretation_contract_v1",
    "load_pro_group_effect_contract_v1",
    "load_pro_instrument_scoring_contract_v1",
    "score_pro_instrument_response_v1",
    "normalize_pro_followup_event_v1",
    "standardize_pro_instrument_score_v1",
    "summarize_pro_form_contract_v1",
    "summarize_pro_improvement_from_event_v1",
    "transform_pro_response_to_zscores_v1",
    "validate_pro_improvement_summary_from_event_v1",
    "validate_pro_domain_norms_v1",
    "validate_pro_form_response_v1",
    "validate_pro_followup_sequence_v1",
]

_PRO_FOLLOWUP_EXPORTS = {
    "PRO_FOLLOWUP_ADHERENCE_THRESHOLD_V1",
    "PRO_FOLLOWUP_EFFECT_INTERPRETATION_SCHEMA_VERSION_V1",
    "PRO_FOLLOWUP_EVENT_SCHEMA_VERSION_V1",
    "PRO_FOLLOWUP_INTERPRETATION_CONTRACT_VERSION_V1",
    "PROAdherenceWindowV1",
    "PROAdverseEventContextV1",
    "PROFollowUpEffectInterpretationV1",
    "PROFollowUpEventV1",
    "PROFollowUpInterpretationContractV1",
    "PROInstrumentObservedChangeV1",
    "interpret_pro_followup_effect_v1",
    "is_versioned_pro_followup_payload_v1",
    "load_pro_followup_interpretation_contract_v1",
    "normalize_pro_followup_event_v1",
    "validate_pro_followup_sequence_v1",
}

_PRO_GROUP_EFFECT_EXPORTS = {
    "PRO_GROUP_EFFECT_CONTRACT_VERSION_V1",
    "PRO_GROUP_EFFECT_SUMMARY_SCHEMA_VERSION_V1",
    "PROGroupConfidenceIntervalV1",
    "PROGroupEffectContractV1",
    "PROGroupEffectSummaryV1",
    "PROGroupEstimateV1",
    "build_pro_group_effect_summary_v1",
    "load_pro_group_effect_contract_v1",
}

_PRO_CORRECTION_EXPORTS = {
    "PROCorrectionRecalculationResultV1",
    "PRORecommendationEffectLineageV1",
    "correct_and_recalculate_pro_followup_v1",
}

_PRO_ACTION_EXPORTS = {
    "PROPlanActionDecisionV1",
    "PROPlanActionV1",
    "decide_pro_plan_action_v1",
}


def __getattr__(name: str):
    if name in __all__:
        module_name = (
            "wellnessbox_rnd.metrics.pro_actions"
            if name in _PRO_ACTION_EXPORTS
            else "wellnessbox_rnd.metrics.pro_correction"
            if name in _PRO_CORRECTION_EXPORTS
            else "wellnessbox_rnd.metrics.pro_group_effects"
            if name in _PRO_GROUP_EFFECT_EXPORTS
            else (
                "wellnessbox_rnd.metrics.pro_followup"
                if name in _PRO_FOLLOWUP_EXPORTS
                else "wellnessbox_rnd.metrics.pro_scoring"
            )
        )
        module = import_module(module_name)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
