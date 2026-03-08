# wellnessbox-rnd

`wellnessbox-rnd`는 WellnessBox 연구개발 전용 Python 리포다. 기준 문서는 [master_context.md](C:/dev/wellnessbox-rnd/docs/context/master_context.md)이며, 이 저장소는 추천 정확도, 안전 검증, 효과 정량화, closed-loop 정책, 평가 하네스, 추론 API를 담당한다.

`wellnessbox`는 웹서비스/UI 레이어이고, 이 저장소는 그 웹이 호출하는 AI/R&D 서비스 레이어다.

## 현재 구현 상태

- FastAPI 기반 최소 추론 API
- `/health` 엔드포인트
- `/v1/recommend` deterministic baseline 추천 엔드포인트
- intake normalization
- personal safety validation
- candidate filtering
- efficacy/goal scoring
- optimization / ranking
- templated explanation generation
- frozen eval runner와 metric calculator

## 현재 baseline의 범위

- 핵심 의사결정은 룰 기반 + 점수화 기반으로 결정적으로 구현했다.
- LLM은 핵심 추천 의사결정에 사용하지 않는다.
- 추천 카탈로그는 `data/catalog/ingredients.json`의 demo/placeholder catalog를 사용한다.
- 안전 규칙은 `data/rules/safety_rules.json`에 분리했다.
- `wellnessbox`의 기존 survey/scoring 데이터는 읽기 전용으로 검토했지만, 현재 baseline은 그 파일들을 직접 runtime dependency로 사용하지 않는다.

## 아직 구현하지 않은 범위

- 실제 제품 SSOT 연동
- 실제 데이터베이스
- 학습 코드
- 모델 가중치
- 실제 센서/유전자 ingest 파이프라인
- production-grade observability stack
- chat/LLM 상담 엔진

## 빠른 시작

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
uvicorn apps.inference_api.main:app --reload
```

확인 경로:

- `GET http://127.0.0.1:8000/health`
- `POST http://127.0.0.1:8000/v1/recommend`

## 테스트와 평가

```bash
python -m ruff check .
python -m pytest
python scripts/run_eval.py
```

리포트 출력:

- `artifacts/reports/eval_report.json`
- `artifacts/reports/eval_report.md`

## 디렉터리 구조

```text
apps/inference_api/        FastAPI 앱과 라우트
src/wellnessbox_rnd/       도메인, 스키마, safety/optimizer/orchestration 코드
data/catalog/              demo ingredient catalog
data/rules/                safety rules
data/frozen_eval/          frozen eval seed dataset
tests/                     API 및 baseline 엔진 테스트
docs/                      기준 문서, 아키텍처, eval 문서
legacy_code/               wellnessbox에서 이관한 과거 자산
```

## 구현 메모

- 입력 스키마는 `master_context.md`의 핵심 입력 축인 설문, 약물, 증상, 생활습관, 웨어러블/CGM/유전자 가용성을 반영한다.
- 출력에는 `decision_summary`, `safety_flags`, `recommendations`, `follow_up_questions`, `missing_information`이 포함된다.
- 의료적 단정 표현은 피하고, 입력이 부족하면 보수적으로 `needs_review` 또는 `collect_more_input`으로 보낸다.
- 현재 baseline은 KPI 달성을 위한 첫 단계이며, 이후 실제 rule set과 product/catalog contract로 교체될 수 있다.
