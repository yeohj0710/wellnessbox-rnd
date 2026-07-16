from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wellnessbox_rnd.evals.runner import EvalCase, load_eval_cases
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import RecommendationResponse


class ReplayCandidateScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingredient_key: str = Field(min_length=1)
    rank: int = Field(ge=1)
    total_score: float = Field(allow_inf_nan=False)
    learned_effect_bonus: float = Field(allow_inf_nan=False)


class ReplayRankChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingredient_key: str = Field(min_length=1)
    baseline_rank: int = Field(ge=1)
    learned_rank: int = Field(ge=1)
    score_delta: float = Field(allow_inf_nan=False)


class ReplayDecisionStatusCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    not_requested: int = Field(ge=0)
    not_eligible: int = Field(ge=0)
    applied: int = Field(ge=0)
    fallback_missing_path: int = Field(ge=0)
    fallback_missing_file: int = Field(ge=0)
    fallback_invalid_artifact: int = Field(ge=0)
    fallback_suspicious_artifact: int = Field(ge=0)
    fallback_artifact_runtime_error: int = Field(ge=0)

    @property
    def fallback_total(self) -> int:
        return sum(
            value
            for field_name, value in self.model_dump().items()
            if field_name.startswith("fallback_")
        )


ReplayLearnedDecisionStatus = Literal[
    "not_requested",
    "not_eligible",
    "applied",
    "fallback_missing_path",
    "fallback_missing_file",
    "fallback_invalid_artifact",
    "fallback_suspicious_artifact",
    "fallback_artifact_runtime_error",
]


class RecommendationReplayCaseComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    baseline_candidates: list[ReplayCandidateScore]
    learned_candidates: list[ReplayCandidateScore]
    learned_decision_status: ReplayLearnedDecisionStatus
    learned_applied: bool
    selection_changed: bool
    added_ingredient_keys: list[str]
    removed_ingredient_keys: list[str]
    rank_changes: list[ReplayRankChange]
    response_status_changed: bool
    next_action_changed: bool
    safety_changed: bool

    @model_validator(mode="after")
    def validate_exact_replay_delta(self) -> RecommendationReplayCaseComparison:
        baseline_keys = [item.ingredient_key for item in self.baseline_candidates]
        learned_keys = [item.ingredient_key for item in self.learned_candidates]
        for label, candidates, keys in (
            ("baseline", self.baseline_candidates, baseline_keys),
            ("learned", self.learned_candidates, learned_keys),
        ):
            if len(keys) != len(set(keys)):
                raise ValueError(f"{label} replay candidates must be unique")
            if [item.rank for item in candidates] != list(range(1, len(candidates) + 1)):
                raise ValueError(f"{label} replay ranks must be contiguous")
        if self.selection_changed != (baseline_keys != learned_keys):
            raise ValueError("selection_changed does not match replay candidate order")
        expected_added = sorted(set(learned_keys) - set(baseline_keys))
        expected_removed = sorted(set(baseline_keys) - set(learned_keys))
        if self.added_ingredient_keys != expected_added:
            raise ValueError("added ingredients do not match replay candidates")
        if self.removed_ingredient_keys != expected_removed:
            raise ValueError("removed ingredients do not match replay candidates")
        baseline_by_key = {item.ingredient_key: item for item in self.baseline_candidates}
        learned_by_key = {item.ingredient_key: item for item in self.learned_candidates}
        expected_rank_changes = [
            ReplayRankChange(
                ingredient_key=key,
                baseline_rank=baseline_by_key[key].rank,
                learned_rank=learned_by_key[key].rank,
                score_delta=round(
                    learned_by_key[key].total_score - baseline_by_key[key].total_score,
                    6,
                ),
            )
            for key in sorted(set(baseline_keys) & set(learned_keys))
            if (
                baseline_by_key[key].rank != learned_by_key[key].rank
                or abs(
                    learned_by_key[key].total_score
                    - baseline_by_key[key].total_score
                )
                > 1e-6
            )
        ]
        if self.rank_changes != expected_rank_changes:
            raise ValueError("rank changes do not match replay candidate scores")
        if not self.learned_applied and self.selection_changed:
            raise ValueError("non-applied learned replay must preserve baseline selection")
        if self.learned_applied != (
            self.learned_decision_status == "applied"
        ):
            raise ValueError("learned replay status and applied flag disagree")
        return self


class RecommendationReplayComparisonReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["recommendation_learned_baseline_replay_compare_v1"] = (
        "recommendation_learned_baseline_replay_compare_v1"
    )
    dataset_path: str
    learned_artifact_path: str
    case_count: int = Field(ge=1)
    learned_applied_case_count: int = Field(ge=0)
    deterministic_baseline_case_count: int = Field(ge=0)
    fallback_case_count: int = Field(ge=0)
    decision_status_counts: ReplayDecisionStatusCounts
    selection_changed_case_count: int = Field(ge=0)
    rank_or_score_changed_case_count: int = Field(ge=0)
    response_status_changed_case_count: int = Field(ge=0)
    next_action_changed_case_count: int = Field(ge=0)
    safety_changed_case_count: int = Field(ge=0)
    cases: list[RecommendationReplayCaseComparison]

    @model_validator(mode="after")
    def validate_aggregate_counts(self) -> RecommendationReplayComparisonReport:
        if self.case_count != len(self.cases):
            raise ValueError("replay case count mismatch")
        case_ids = [item.case_id for item in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("replay case IDs must be unique")
        expected = {
            "learned_applied_case_count": sum(item.learned_applied for item in self.cases),
            "deterministic_baseline_case_count": sum(
                not item.learned_applied for item in self.cases
            ),
            "fallback_case_count": sum(
                item.learned_decision_status.startswith("fallback_")
                for item in self.cases
            ),
            "selection_changed_case_count": sum(
                item.selection_changed for item in self.cases
            ),
            "rank_or_score_changed_case_count": sum(
                bool(item.rank_changes) for item in self.cases
            ),
            "response_status_changed_case_count": sum(
                item.response_status_changed for item in self.cases
            ),
            "next_action_changed_case_count": sum(
                item.next_action_changed for item in self.cases
            ),
            "safety_changed_case_count": sum(item.safety_changed for item in self.cases),
        }
        for field_name, expected_value in expected.items():
            if getattr(self, field_name) != expected_value:
                raise ValueError(f"{field_name} mismatch")
        status_counts = Counter(item.learned_decision_status for item in self.cases)
        if self.decision_status_counts.model_dump() != {
            field_name: status_counts[field_name]
            for field_name in ReplayDecisionStatusCounts.model_fields
        }:
            raise ValueError("decision_status_counts mismatch")
        if sum(self.decision_status_counts.model_dump().values()) != self.case_count:
            raise ValueError("decision status counts must cover every replay case")
        return self


def _candidate_scores(response: RecommendationResponse) -> list[ReplayCandidateScore]:
    return [
        ReplayCandidateScore(
            ingredient_key=item.ingredient_key,
            rank=index,
            total_score=round(item.score_breakdown.total, 6),
            learned_effect_bonus=round(item.score_breakdown.learned_effect_bonus, 6),
        )
        for index, item in enumerate(response.recommendations, start=1)
    ]


def _safety_fingerprint(response: RecommendationResponse) -> str:
    return json.dumps(
        {
            "safety_summary": response.safety_summary.model_dump(
                mode="json",
                exclude={"applied_at"},
            ),
            "safety_flags": response.safety_flags,
            "safety_evidence": [
                item.model_dump(mode="json") for item in response.safety_evidence
            ],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _portable_source_path(value: str | Path) -> str:
    path = Path(value)
    project_root = Path(__file__).resolve().parents[3]
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError:
        return path.as_posix()


def _compare_case(
    case: EvalCase,
    *,
    learned_artifact_path: str | Path,
) -> RecommendationReplayCaseComparison:
    baseline = recommend(case.request)
    learned = recommend(
        case.request,
        enable_learned_reranking=True,
        learned_efficacy_artifact_path=str(learned_artifact_path),
    )
    baseline_candidates = _candidate_scores(baseline)
    learned_candidates = _candidate_scores(learned)
    baseline_by_key = {item.ingredient_key: item for item in baseline_candidates}
    learned_by_key = {item.ingredient_key: item for item in learned_candidates}
    rank_changes = [
        ReplayRankChange(
            ingredient_key=key,
            baseline_rank=baseline_by_key[key].rank,
            learned_rank=learned_by_key[key].rank,
            score_delta=round(
                learned_by_key[key].total_score - baseline_by_key[key].total_score,
                6,
            ),
        )
        for key in sorted(set(baseline_by_key) & set(learned_by_key))
        if (
            baseline_by_key[key].rank != learned_by_key[key].rank
            or abs(
                learned_by_key[key].total_score - baseline_by_key[key].total_score
            )
            > 1e-6
        )
    ]
    baseline_keys = [item.ingredient_key for item in baseline_candidates]
    learned_keys = [item.ingredient_key for item in learned_candidates]
    return RecommendationReplayCaseComparison(
        case_id=case.case_id,
        request_id=case.request.request_id,
        category=case.category,
        baseline_candidates=baseline_candidates,
        learned_candidates=learned_candidates,
        learned_decision_status=learned.learned_reranking_decision.status,
        learned_applied=learned.learned_reranking_decision.learned_reranking_applied,
        selection_changed=baseline_keys != learned_keys,
        added_ingredient_keys=sorted(set(learned_keys) - set(baseline_keys)),
        removed_ingredient_keys=sorted(set(baseline_keys) - set(learned_keys)),
        rank_changes=rank_changes,
        response_status_changed=baseline.status != learned.status,
        next_action_changed=baseline.next_action != learned.next_action,
        safety_changed=_safety_fingerprint(baseline) != _safety_fingerprint(learned),
    )


def build_recommendation_replay_comparison(
    *,
    dataset_path: str | Path,
    learned_artifact_path: str | Path,
) -> RecommendationReplayComparisonReport:
    cases = load_eval_cases(dataset_path)
    comparisons = [
        _compare_case(case, learned_artifact_path=learned_artifact_path)
        for case in cases
    ]
    decision_status_counts = Counter(
        item.learned_decision_status for item in comparisons
    )
    return RecommendationReplayComparisonReport(
        dataset_path=_portable_source_path(dataset_path),
        learned_artifact_path=_portable_source_path(learned_artifact_path),
        case_count=len(comparisons),
        learned_applied_case_count=sum(item.learned_applied for item in comparisons),
        deterministic_baseline_case_count=sum(
            not item.learned_applied for item in comparisons
        ),
        fallback_case_count=sum(
            item.learned_decision_status.startswith("fallback_")
            for item in comparisons
        ),
        decision_status_counts=ReplayDecisionStatusCounts(
            **{
                field_name: decision_status_counts[field_name]
                for field_name in ReplayDecisionStatusCounts.model_fields
            }
        ),
        selection_changed_case_count=sum(item.selection_changed for item in comparisons),
        rank_or_score_changed_case_count=sum(
            bool(item.rank_changes) for item in comparisons
        ),
        response_status_changed_case_count=sum(
            item.response_status_changed for item in comparisons
        ),
        next_action_changed_case_count=sum(
            item.next_action_changed for item in comparisons
        ),
        safety_changed_case_count=sum(item.safety_changed for item in comparisons),
        cases=comparisons,
    )


__all__ = [
    "RecommendationReplayCaseComparison",
    "RecommendationReplayComparisonReport",
    "ReplayCandidateScore",
    "ReplayDecisionStatusCounts",
    "ReplayRankChange",
    "build_recommendation_replay_comparison",
]
