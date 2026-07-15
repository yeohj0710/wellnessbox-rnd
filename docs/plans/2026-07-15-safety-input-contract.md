# Safety Input Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 알레르기와 응급 위험 신호를 R&D 추천 계약에 추가하고 추천 전에 결정론적으로 차단한다.

**Architecture:** `RecommendationRequest`가 알레르기와 위험 신호를 구조화된 토큰으로 받는다. `NormalizedIntake`가 토큰을 정규화하고, 데이터 파일의 버전 관리 규칙을 `assess_safety`가 적용한다. 서비스의 R&D 클라이언트는 같은 필드를 전달할 수 있지만 기존 preview 계약은 유지한다.

**Tech Stack:** FastAPI, Pydantic, pytest, TypeScript

---

### Task 1: 실패하는 R&D API 테스트 추가

**Files:**
- Modify: `tests/test_inference_api.py`

- [x] **Step 1: 어류 알레르기가 오메가3를 제외하는 테스트를 추가한다**

```python
payload["allergies"] = ["fish"]
response = client.post("/v1/recommend", json=payload)
assert response.status_code == 200
assert "omega3" in response.json()["safety_summary"]["excluded_ingredients"]
```

- [x] **Step 2: 흉통 위험 신호가 추천을 중단하는 테스트를 추가한다**

```python
payload["risk_flags"] = ["red_flag_chest_pain"]
response = client.post("/v1/recommend", json=payload)
assert response.status_code == 200
body = response.json()
assert body["status"] == "blocked"
assert body["recommendations"] == []
```

- [x] **Step 3: 테스트가 새 계약 부재로 실패하는지 확인한다**

Run: `python -m pytest tests/test_inference_api.py -q`

Expected: 새 안전 입력 테스트가 실패한다.

### Task 2: 구조화 안전 입력과 규칙 구현

**Files:**
- Modify: `src/wellnessbox_rnd/schemas/recommendation.py`
- Modify: `src/wellnessbox_rnd/domain/intake.py`
- Modify: `src/wellnessbox_rnd/domain/models.py`
- Modify: `src/wellnessbox_rnd/safety/service.py`
- Modify: `data/rules/safety_rules.json`

- [x] **Step 1: 요청 스키마에 안전 입력을 추가한다**

```python
allergies: list[str] = Field(default_factory=list)
risk_flags: list[str] = Field(default_factory=list)
```

- [x] **Step 2: 정규화 결과에 안전 토큰 집합을 추가한다**

```python
allergy_set: set[str]
risk_flag_set: set[str]
```

- [x] **Step 3: 안전 규칙 모델을 추가한다**

```python
class AllergyRule(BaseModel):
    allergies: list[str] = Field(default_factory=list)
    excluded_ingredients: list[str] = Field(default_factory=list)
    metadata: SafetyRuleMetadata


class RiskFlagRule(BaseModel):
    risk_flags: list[str] = Field(default_factory=list)
    blocked_reason: str
    metadata: SafetyRuleMetadata
```

- [x] **Step 4: 어류 알레르기와 응급 위험 신호 규칙을 JSON에 등록한다**

```json
{
  "allergies": ["fish", "fish allergy"],
  "excluded_ingredients": ["omega3"]
}
```

```json
{
  "risk_flags": ["red_flag_chest_pain", "red_flag_severe_abdominal_pain"],
  "blocked_reason": "Urgent symptom input requires recommendation to stop."
}
```

- [x] **Step 5: `assess_safety`가 위험 신호를 먼저 차단하고 알레르기 성분을 제외하게 한다**

Run: `python -m pytest tests/test_inference_api.py -q`

Expected: PASS

### Task 3: 서비스 요청 계약 보완

**Files:**
- Modify: `C:/dev/wellnessbox/lib/server/wb-rnd-client.ts`
- Modify: `C:/dev/wellnessbox/scripts/qa/check-rnd-recommend-preview.cts`

- [x] **Step 1: `WbRndRecommendRequest`에 안전 입력을 추가한다**

```ts
allergies?: string[];
risk_flags?: string[];
```

- [x] **Step 2: preview 요청이 안전 입력을 그대로 R&D API에 전달하는지 검사한다**

Run: `npm run qa:rnd:preview-route`

Expected: PASS

### Task 4: 전체 검증과 문서 갱신

**Files:**
- Modify: `PROGRESS.md`
- Modify: `NEXT_STEPS.md`
- Modify: `SESSION_HANDOFF.md`

- [x] **Step 1: 변경 범위 R&D 정적 검사와 테스트를 실행한다**

Run: `python -m ruff check .`

Expected: PASS

Run: `python -m pytest tests/test_inference_api.py tests/test_sensor_genetic_normalization_audit.py -q`

Expected: PASS

- [x] **Step 2: 서비스 계약 검사를 실행한다**

Run: `npm run qa:rnd:preview-route`

Expected: PASS

Run: `npx tsc --noEmit`

Expected: PASS

- [x] **Step 3: 현재 단계와 다음 세 단계를 진행 문서에 기록한다**

`PROGRESS.md`, `NEXT_STEPS.md`, `SESSION_HANDOFF.md`에 완료된 안전 계약과 다음 입력 계약 범위를 기록한다.

### 전체 R&D 테스트 기준선

- [ ] Git에서 제외된 평가 보고서 산출물을 신뢰 가능한 원본에서 복원한다.
- [ ] CGM 최종 단계의 현재 실행값과 테스트 기대값 드리프트 4건을 별도 원인 분석으로 해소한다.
- 현재 전체 결과: `445 passed, 77 failed, 68 warnings`
- 실패 분류: 보고서 산출물 부재 73건, 기존 CGM 실행값 드리프트 4건
- 새 안전 입력 규칙을 런타임에서 비활성화해도 CGM 분포가 같으므로 이번 계약 변경에서 발생한 회귀가 아니다.
