# 우선순위 백로그

## P0

| 우선순위 | 작업 | 이유 | 주요 파일 |
| --- | --- | --- | --- |
| P0-1 | KPI/요구사항 재정리 | 전체 실행 기준 재확인 | `docs/context/master_context.md`, `docs/context/original_plan.pdf` |
| P0-2 | recommend schema refinement | eval / baseline / API 공통 기준 | `src/wellnessbox_rnd/schemas/recommendation.py` |
| P0-3 | frozen eval 확대 | KPI gate 최소 기반 확보 | `data/frozen_eval/`, `src/wellnessbox_rnd/evals/runner.py` |
| P0-4 | safety rules 확장 | 잘못된 추천 억제 | `data/rules/safety_rules.json`, `src/wellnessbox_rnd/safety/` |
| P0-5 | efficacy / ranking 개선 | recommendation coverage 개선 | `src/wellnessbox_rnd/efficacy/`, `src/wellnessbox_rnd/optimizer/` |
| P0-6 | missing info / follow-up 개선 | closed-loop 품질 향상 | `src/wellnessbox_rnd/orchestration/` |
| P0-7 | synthetic case generator 설계 | eval 확대 자동화 | `scripts/`, `data/frozen_eval/` |
| P0-8 | evidence / citation 구조화 | safety KPI 강화 | `schemas/`, `safety/`, future `data/knowledge/` |
| P0-9 | docs / runtime sync 유지 | 다음 세션 drift 방지 | `README.md`, `PROGRESS.md`, `SESSION_HANDOFF.md` |
| P0-10 | generic API boundary 정리 | 외부 소비자와 무관한 R&D 기준 유지 | `docs/01_architecture/` |

## P1

| 우선순위 | 작업 | 이유 |
| --- | --- | --- |
| P1-1 | catalog 확장 | demo catalog 한계 보완 |
| P1-2 | effect quantification 강화 | KPI 2 보강 |
| P1-3 | policy state machine 강화 | KPI 3 보강 |
| P1-4 | artifact/version discipline 추가 | 재현성 향상 |

## P2

| 우선순위 | 작업 | 이유 |
| --- | --- | --- |
| P2-1 | optional LLM explanation layer | deterministic baseline 이후 |
| P2-2 | synthetic large-scale generation | baseline / eval 안정화 이후 |

## 범위 밖

- 제품 repo 연동
- preview / rollout / timeout UX
- 특정 route/file 기반 adapter
