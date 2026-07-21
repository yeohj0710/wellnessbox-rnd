from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

DEFAULT_COUNSELING_VERIFIER_POLICY_PATH = Path(
    "data/knowledge/counseling_answer_verifier_policy_v1.json"
)


class CounselingAnswerVerifierPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_id: str = Field(min_length=1)
    urgent_risk_keys: list[str] = Field(min_length=1)
    emergency_guidance_sentences: list[str] = Field(min_length=1)
    forbidden_expressions: list[str] = Field(min_length=1)
    recommendation_expressions: list[str] = Field(min_length=1)
    interaction_risk_terms: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_policy(self) -> CounselingAnswerVerifierPolicy:
        for field_name in (
            "urgent_risk_keys",
            "forbidden_expressions",
            "recommendation_expressions",
            "interaction_risk_terms",
        ):
            values = getattr(self, field_name)
            if values != sorted(set(values)):
                raise ValueError(f"{field_name}_must_be_sorted_unique")
            if any(not value.strip() for value in values):
                raise ValueError(f"{field_name}_must_not_contain_blank")
        if len(self.emergency_guidance_sentences) != len(set(self.emergency_guidance_sentences)):
            raise ValueError("emergency_guidance_sentences_must_be_unique")
        if any(not sentence.strip() for sentence in self.emergency_guidance_sentences):
            raise ValueError("emergency_guidance_sentences_must_not_contain_blank")
        return self

    @property
    def emergency_guidance_text(self) -> str:
        return " ".join(self.emergency_guidance_sentences)


def load_counseling_answer_verifier_policy(
    path: str | Path = DEFAULT_COUNSELING_VERIFIER_POLICY_PATH,
) -> CounselingAnswerVerifierPolicy:
    return CounselingAnswerVerifierPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def require_repository_approved_policy(
    policy: CounselingAnswerVerifierPolicy,
) -> CounselingAnswerVerifierPolicy:
    approved = load_counseling_answer_verifier_policy()
    if policy != approved:
        raise ValueError("counseling_verifier_policy_not_repository_approved")
    return approved


__all__ = [
    "CounselingAnswerVerifierPolicy",
    "DEFAULT_COUNSELING_VERIFIER_POLICY_PATH",
    "load_counseling_answer_verifier_policy",
    "require_repository_approved_policy",
]
