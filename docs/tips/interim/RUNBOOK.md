# 중간 파이프라인 실행서

> 상태: `PROXY_GOLD_SIMULATION` · 생성 시각: 2026-07-10T06:43:58.432475+00:00

> 이 문서는 중간 시뮬레이션 근거다. 실제 약사 판정, 실제 임상 효과, 12개월 실제 운영, 생산 기기 연동, 외부 시험·인증 완료를 뜻하지 않는다.

## 실행

```powershell
.\.venv-interim\Scripts\python.exe scripts/run_interim_pipeline.py verify-package
.\.venv-interim\Scripts\python.exe scripts/run_interim_pipeline.py import
.\.venv-interim\Scripts\python.exe scripts/run_interim_pipeline.py retrain
.\.venv-interim\Scripts\python.exe scripts/run_interim_pipeline.py evaluate
.\.venv-interim\Scripts\python.exe scripts/run_interim_pipeline.py report
.\.venv-interim\Scripts\python.exe scripts/run_interim_pipeline.py verify-release
```

원본 package는 덮어쓰지 않는다. 재학습은 `artifacts/tips/interim/retrained`에 쓴다.
