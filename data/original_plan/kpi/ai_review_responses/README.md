# 블라인드 AI 검수 응답 상태

- `kpi3_codex_blind_response_v1.json`과 `kpi4_codex_blind_response_v1.json`은 각각 100건을 담은 Codex의 독립 의견이다.
- 각 Codex 작업은 대응하는 `data/original_plan/kpi/ai_review_packets/` 파일 하나만 읽었고, 엔진 규칙·엔진 출력·기존 정답은 읽지 않았다.
- 두 파일은 패킷 SHA-256 일치, 문항 100건·고유 ID 100개, 누락·추가 문항 0건, 허용 답변 밖 선택 0건, `engine_output_consulted=false`를 확인했다.
- KPI-3 응답은 원래 응답 역할을 provenance에 남기고 1차 초안으로 가져왔다. KPI-3에는 비 OpenAI 계열(예: Claude)의 독립 2차 의견이 필요하다.
- KPI-4는 측정 대상 상담 모듈이 OpenAI 계열이므로 Codex를 1차 초안으로 쓸 수 없다. 비 OpenAI 계열의 독립 1차 초안을 먼저 가져온 뒤 이 Codex 응답을 2차 의견으로 가져온다.
- 두 파일과 KPI-3 가져오기는 정답, 사람 승인 또는 봉인을 뜻하지 않는다. 사람은 불일치·위험 표시·결정론적 합의 표본만 상세 검토한 뒤 나머지 합의를 직접 일괄 승인한다.
