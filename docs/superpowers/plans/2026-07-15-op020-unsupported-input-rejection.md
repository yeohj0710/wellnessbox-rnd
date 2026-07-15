# OP-020 Unsupported Input Rejection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** R&D 추천 요청이 지원하지 않는 필드, 모호한 구조화 단위, 동일 약·영양제의 상충 중복을 조용히 버리지 않고 실제 API 경계에서 오류로 반환하게 한다.

**Architecture:** 기존 `RecommendationRequest`와 `/v1/recommend` 경로를 그대로 사용한다. 모든 요청 구성 모델은 `extra="forbid"`를 공유하고, 검사 단위는 지원하는 정규 단위 집합으로 제한한다. 요청 수준 검증기는 NFKC·casefold 정규화와 정확한 성분 카탈로그 별칭을 적용한 식별자별 의미 서명을 비교한다. 완전히 같은 약·제품 중복은 호환성을 위해 허용하되 서로 다른 분류, 용량, 성분 정보 또는 성분 개수가 같은 식별자에 붙으면 422를 반환한다.

**Tech Stack:** Python 3.12, Pydantic v2, FastAPI, pytest

---

### Task 1: 실패 회귀 계약

**Files:**
- Create: `tests/test_unsupported_input_contracts.py`
- Reuse: `data/samples/api_recommend_consent_hash_request_v1.json`

- [x] **Step 1: 요청 경계별 미지원 필드가 현재 무시되는 현상을 재현한다.**

```python
@pytest.mark.parametrize(
    ("container_path", "unsupported_field"),
    [
        ((), "unsupported_top_level"),
        (("user_profile",), "unsupported_profile_field"),
        (("lifestyle",), "unsupported_lifestyle_field"),
        (("input_availability",), "unsupported_source"),
        (("preferences",), "unsupported_preference"),
    ],
)
def test_unsupported_fields_fail_closed_at_model_and_api_boundaries(
    container_path: tuple[str, ...],
    unsupported_field: str,
) -> None:
    payload = _load_payload()
    _resolve_mapping(payload, container_path)[unsupported_field] = "must-not-disappear"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RecommendationRequest.model_validate(payload)
    assert client.post("/v1/recommend", json=payload).status_code == 422
```

- [x] **Step 2: 상충 중복 약·영양제, 미지원 검사 단위, 유니코드·카탈로그 별칭 우회를 재현한다.**

```python
payload["medications"] = [
    {"name": "Metformin", "dose": {"amount": 500, "unit": "mg"}},
    {"name": " metformin ", "dose": {"amount": 850, "unit": "mg"}},
]
with pytest.raises(ValidationError, match="conflicting duplicate medications"):
    RecommendationRequest.model_validate(payload)
```

- [x] **Step 3: 실패 테스트를 실행한다.**

Run: `.\.venv-interim\Scripts\python.exe -m pytest -o addopts="" -q tests/test_unsupported_input_contracts.py`

Expected: 미지원 최상위·중첩 필드와 상충 중복 관련 테스트가 FAIL한다. 기존 Pydantic 열거형이 모호한 구조화 단위를 거부하는 테스트는 PASS할 수 있다.

### Task 2: 엄격한 입력 경계와 상충 중복 검증

**Files:**
- Modify: `src/wellnessbox_rnd/schemas/recommendation.py`
- Test: `tests/test_unsupported_input_contracts.py`

- [x] **Step 1: 모든 추천 요청 구성 모델이 같은 엄격한 기본 클래스를 사용하게 한다.**

```python
class _StrictRequestInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserProfile(_StrictRequestInput):
    age: int = Field(ge=18, le=120)
    biological_sex: BiologicalSex
    pregnant: bool = False
    height_cm: float | None = Field(default=None, gt=0, le=300)
    weight_kg: float | None = Field(default=None, gt=0, le=500)


class LifestyleInput(_StrictRequestInput):
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    stress_level: int | None = Field(default=None, ge=1, le=5)
    activity_level: ActivityLevel = ActivityLevel.SEDENTARY
    exercise_minutes_per_week: float | None = Field(default=None, ge=0, le=10_080)
    smoker: bool = False
    alcohol_per_week: int = Field(default=0, ge=0, le=50)
    caffeine_mg_per_day: float | None = Field(default=None, ge=0, le=5_000)


class InputAvailability(_StrictRequestInput):
    survey: bool = True
    nhis: bool = False
    wearable: bool = False
    cgm: bool = False
    genetic: bool = False


class RecommendationPreferences(_StrictRequestInput):
    budget_level: BudgetLevel = BudgetLevel.MEDIUM
    max_products: int = Field(default=2, ge=1, le=5)
    avoid_ingredients: list[str] = Field(default_factory=list)


class RecommendationRequest(_StrictRequestInput):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    user_profile: UserProfile
    goals: list[RecommendationGoal] = Field(min_length=1)
    symptoms: list[str | SymptomInput] = Field(default_factory=list)
    conditions: list[str | ConditionInput] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    risk_flags: list[str | UrgentRiskSignal] = Field(default_factory=list)
    medications: list[MedicationInput] = Field(default_factory=list)
    current_supplements: list[SupplementInput] = Field(default_factory=list)
```

- [x] **Step 2: 지원 검사 단위와 유니코드·카탈로그 정규 식별자를 정의한다.**

```python
def _normalize_contract_text(value: str) -> str:
    normalized = normalize_unicode("NFKC", value)
    return " ".join(normalized.strip().casefold().split())


@field_validator("unit")
@classmethod
def require_supported_unit(cls, value: str) -> str:
    if normalize_laboratory_unit(value) not in _SUPPORTED_LABORATORY_UNITS:
        raise ValueError("unsupported laboratory unit")
    return value
```

- [x] **Step 3: 약과 영양제의 의미 서명을 만든다.**

```python
def _dose_signature(value: LegacyDoseText | DoseAmount | None) -> tuple[object, ...] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return ("legacy_text", _normalize_contract_text(value))
    return ("structured", value.amount, value.unit.value)
```

- [x] **Step 4: 같은 정규화 식별자의 상충 중복을 요청 검증기에서 거부한다.**

```python
@model_validator(mode="after")
def reject_conflicting_duplicate_medications(self) -> "RecommendationRequest":
    signatures: dict[str, tuple[object, ...]] = {}
    for medication in self.medications:
        identity = _normalize_contract_text(medication.name)
        signature = _medication_signature(medication)
        if identity in signatures and signatures[identity] != signature:
            raise ValueError("conflicting duplicate medications for the same normalized name")
        signatures[identity] = signature
    return self
```

- [x] **Step 5: 완전히 같은 약·제품 중복은 허용하고 모든 실패 계약을 통과하는지 확인한다.**

Run: `.\.venv-interim\Scripts\python.exe -m pytest -o addopts="" -q tests/test_unsupported_input_contracts.py tests/test_inference_api.py tests/test_medication_supplement_input_contracts.py tests/test_diet_lifestyle_lab_input_contracts.py tests/test_consent_and_input_hash_contracts.py`

Expected: 신규 실패가 없고 정확한 중복은 호환성을 유지한다.

### Task 3: 원계획 증거와 완료 상태

**Files:**
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `.github/workflows/original-plan-evidence.yml`
- Modify: `tests/test_original_plan_manifest.py`
- Modify: `tests/test_original_plan_audit.py`
- Modify: `tests/test_original_plan_audit_cli.py`
- Modify: `tests/test_original_plan_completion_report.py`
- Modify: `docs/plans/2026-07-15-original-plan-completion-program.md`
- Modify: `docs/original_plan/COMPLETION_STATUS.md`
- Modify: `docs/original_plan/completion_status_v1.json`
- Modify: `PROGRESS.md`
- Modify: `NEXT_STEPS.md`
- Modify: `SESSION_HANDOFF.md`

- [x] **Step 1: OP-020에 구현·API 테스트 증거를 `INTEGRATED` 단계로 등록한다.**

```json
{
  "requirement_id": "OP-020",
  "claimed_stage": "INTEGRATED",
  "evidence": {
    "implementation_files": [
      "wellnessbox-rnd/src/wellnessbox_rnd/schemas/recommendation.py",
      "wellnessbox-rnd/apps/inference_api/routes/recommend.py"
    ],
    "test_files": [
      "wellnessbox-rnd/tests/test_unsupported_input_contracts.py"
    ],
    "integration_evidence": [
      "wellnessbox-rnd/apps/inference_api/routes/recommend.py",
      "wellnessbox-rnd/tests/test_unsupported_input_contracts.py"
    ]
  }
}
```

- [x] **Step 2: 완료 보고서를 다시 생성하고 감사한다.**

Run: `.\.venv-interim\Scripts\python.exe scripts\build_original_plan_completion_report.py`

Run: `.\.venv-interim\Scripts\python.exe scripts\audit_original_plan_requirements.py`

Expected: 감사 PASS, 완료 `21`, 대기 `98`, 외부 `1`, 모순 `0`.

- [x] **Step 3: 집중·핵심·전체 회귀와 frozen eval을 실행한다.**

Run: `.\.venv-interim\Scripts\python.exe -m ruff check .`

Run: `.\.venv-interim\Scripts\python.exe -m pytest`

Run: `.\.venv-interim\Scripts\python.exe scripts\run_eval.py --dataset data\frozen_eval\frozen_eval_v1.jsonl --output-dir etc\op020_eval`

Expected: OP-020 관련 테스트는 모두 PASS하고, 전체 테스트에는 기존 77개 기준선 실패만 남으며, frozen eval 7개 지표 델타는 모두 0이다.

- [x] **Step 4: 진행 문서를 갱신하고 관련 파일만 커밋·푸시한 뒤 `Original plan evidence` CI를 확인한다.**

```text
feat: reject unsupported TIPS recommendation inputs
```

OP-019는 `wellnessbox` 프로필 변환기와 양쪽 저장소의 실제 계약 증거가 생길 때까지 완료 처리하지 않는다.
