# OpenAI 응답 검증 결과

- 원본 파일: `kpi_processed_responses.zip`
- SHA-256: `1d84499e0805241c172c73359cd1cd27af42fa33bccd6456a60b9e2b1166e45d`
- 사용자 확인 모델: `ChatGPT 5.6 Sol Pro`
- Windows 다운로드 출처 호스트: `chatgpt.com`
- 포함 자료: KPI-1·3·4·5 각 100건, 총 400건
- 구조 검사: 문항 수, 필수 답, 답 어휘, confidence, 패킷 해시 통과
- 원본 모델 필드: 네 파일 모두 `not_recorded`
- 정식 판정: 독립 교차 검수로 사용 불가

KPI-1·3·5는 기존 초안과 OpenAI 제공자 계열이 같아서 `ai_review_agent_matches_drafting_agent_family`로 차단됐다. KPI-4는 측정 대상 상담 모듈과 OpenAI 제공자 계열이 같고 준비된 Codex 2차 의견과도 같은 계열이므로 정식 교차 검수에 사용할 수 없다.

원본 ZIP은 보조 의견과 실패 근거로만 보존한다. 워크벤치, 정답, 승인 또는 봉인에는 반영하지 않았다.
