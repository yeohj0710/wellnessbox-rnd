# OP-017·018 Consent and Deterministic Input Hash Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 설문, 국민건강보험, 웨어러블, CGM, 유전자 데이터의 추천 사용·영속 저장 동의를 분리하고, 같은 정규화 입력이 같은 SHA-256을 만들게 한다.

**Architecture:** `RecommendationRequest`가 출처별 동의 범위를 소유한다. `normalize_request`는 데이터 존재 여부와 추천 사용 동의를 결합한 유효 입력만 기존 안전·효과·추천 경로에 전달하고, 정규화된 순서 독립 스냅샷으로 해시를 계산한다. 영속 저장은 이번 단계에서 수행하지 않으며, 저장 가능 출처 집합만 다음 Data Lake 단계가 사용할 결정론적 계약으로 제공한다.

**Tech Stack:** Python 3.12, Pydantic v2, FastAPI, pytest, SHA-256

---

### Task 1: 출처별 동의 계약

**Files:**
- Modify: `src/wellnessbox_rnd/schemas/recommendation.py`
- Test: `tests/test_consent_and_input_hash_contracts.py`

- [x] **Step 1: 동의 범위가 없는 현재 동작을 재현하는 실패 테스트를 작성한다.**

```python
request = RecommendationRequest.model_validate(payload)
assert request.data_source_consents.cgm.use_for_recommendation is False
assert request.data_source_consents.cgm.allow_persistent_storage is False
```

- [x] **Step 2: 출처와 목적이 분리된 Pydantic 모델을 추가한다.**

```python
class DataSource(StrEnum):
    SURVEY = "survey"
    NHIS = "nhis"
    WEARABLE = "wearable"
    CGM = "cgm"
    GENETIC = "genetic"


class DataSourceConsent(_StrictHealthInput):
    use_for_recommendation: bool = False
    allow_persistent_storage: bool = False
```

명시적으로 제공한 동의 블록에서 생략한 출처는 두 목적 모두 거부한다. 동의 블록 전체를 생략한 기존 요청만 추천 사용을 허용하고, 영속 저장은 계속 거부한다.

- [x] **Step 3: 스키마 계약 테스트를 실행한다.**

Run: `.\.venv-interim\Scripts\python.exe -m pytest tests/test_consent_and_input_hash_contracts.py -q`

Expected: 출처별 동의 기본값, 명시적 허용·거부, 추가 필드 거부가 PASS한다.

### Task 2: 동의 게이트와 결정론적 해시

**Files:**
- Modify: `src/wellnessbox_rnd/domain/intake.py`
- Test: `tests/test_consent_and_input_hash_contracts.py`

- [x] **Step 1: 동의하지 않은 CGM과 유전자 출처가 신호 집합에서 제외되는 실패 테스트를 작성한다.**

```python
intake = normalize_request(request)
assert intake.effective_input_availability.cgm is False
assert "cgm_data_available" not in intake.signal_flags
assert "cgm" not in intake.storage_authorized_input_source_set
```

- [x] **Step 2: 존재 여부와 동의를 결합한 유효 입력 계약을 구현한다.**

```python
effective = InputAvailability(**{
    source.value: getattr(request.input_availability, source.value)
    and getattr(request.data_source_consents, source.value).use_for_recommendation
    for source in DataSource
})
```

- [x] **Step 3: 정규화 입력 스냅샷과 SHA-256을 구현한다.**

```python
canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
input_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

- [x] **Step 4: 요청 ID, 입력 배열 순서, 공백·대소문자가 달라도 같은 정규화 결과는 같은 해시를 만드는지 검증한다.**

Run: `.\.venv-interim\Scripts\python.exe -m pytest tests/test_consent_and_input_hash_contracts.py -q`

Expected: 동일 정규화 스냅샷과 해시, 동의 변경 시 다른 해시가 PASS한다.

### Task 3: API 예시와 원계획 증거

**Files:**
- Modify: `apps/inference_api/routes/recommend.py`
- Create: `data/samples/api_recommend_consent_hash_request_v1.json`
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `.github/workflows/original-plan-evidence.yml`
- Modify: `tests/test_original_plan_manifest.py`
- Modify: `tests/test_original_plan_audit.py`
- Modify: `tests/test_original_plan_audit_cli.py`
- Modify: `tests/test_original_plan_completion_report.py`
- Modify: `docs/plans/2026-07-15-original-plan-completion-program.md`
- Modify: `PROGRESS.md`
- Modify: `NEXT_STEPS.md`
- Modify: `SESSION_HANDOFF.md`

- [x] **Step 1: 다섯 출처 동의를 모두 명시한 대표 요청을 API와 fixture에 추가한다.**

```json
"data_source_consents": {
  "survey": {"use_for_recommendation": true, "allow_persistent_storage": true},
  "nhis": {"use_for_recommendation": false, "allow_persistent_storage": false},
  "wearable": {"use_for_recommendation": true, "allow_persistent_storage": true},
  "cgm": {"use_for_recommendation": false, "allow_persistent_storage": false},
  "genetic": {"use_for_recommendation": false, "allow_persistent_storage": false}
}
```

- [x] **Step 2: OP-017·018에 구현·테스트 증거를 연결하고 완료 보고서를 다시 생성한다.**

Run: `.\.venv-interim\Scripts\python.exe scripts\audit_original_plan_requirements.py`

Expected: 감사 PASS, 완료 요구사항 수가 20으로 증가한다.

- [x] **Step 3: 집중·확장·전체 회귀와 frozen eval을 실행한다.**

Run: `.\.venv-interim\Scripts\python.exe -m ruff check .`

Run: `.\.venv-interim\Scripts\python.exe -m pytest tests/test_consent_and_input_hash_contracts.py tests/test_inference_api.py tests/test_original_plan_manifest.py tests/test_original_plan_audit.py tests/test_original_plan_audit_cli.py tests/test_original_plan_completion_report.py`

Expected: 신규 실패가 없고 기존 전체 테스트 기준선의 알려진 실패만 남는다.

- [x] **Step 4: 관련 파일만 커밋하고 `main`에 푸시한 뒤 `Original plan evidence` CI를 확인한다.**

```text
feat: gate TIPS inputs by consent and stable hash
```
