# KPI 정답지 2차 AI 검토 패킷

이 폴더의 JSON 4개는 KPI-1·3·4·5 각 100건을 2차 AI가 독립적으로 판단할 수 있게 만든 입력이다. 패킷에는 사례 ID와 질문, 공용 답변 어휘만 있다. 1차 AI의 답·근거, 엔진 로직 9개 내용, 엔진 출력은 넣지 않았다.

## 2차 AI에는 패킷만 전달한다

현재 1차 작성 주체는 `codex`다. 적응형 검토로 사람의 상세 검토량을 줄이려면 2차 AI는 다른 제공자 계열을 사용한다. 예를 들어 Claude에 패킷 하나만 전달하고 아래 형식의 JSON을 받는다. 저장소 전체나 워크벤치 원본을 함께 전달하면 블라인딩이 깨진다.

```json
{
  "reviewing_agent": "claude-<정확한 모델 또는 실행 ID>",
  "review_source": "blind_packet_independent_opinion",
  "blinded_from": ["패킷의 required_blinded_from 9개를 그대로 복사"],
  "packet_sha256": "패킷의 packet_sha256",
  "engine_output_consulted": false,
  "cases": [
    {
      "case_id": "패킷의 case_id",
      "proposed_answer": ["answer_vocabulary 안의 값"],
      "confidence": 0.0,
      "flags": [],
      "rationale": "독립 판단 근거"
    }
  ]
}
```

`cases`는 패킷의 100건을 빠짐없이 한 번씩 포함해야 한다. `confidence`는 0부터 1 사이다. 불확실성, 임상 위험, 어휘 부족이 있으면 `flags`에 구체적인 문자열을 넣는다. 가져오기 도구는 사례 누락·중복·추가, 빈 답, 같은 제공자 계열, 잘못된 패킷 SHA-256, 엔진 출력 열람, 빠진 블라인딩 경로를 거부한다.

## 사람은 불일치와 표본을 판단한다

```powershell
python scripts/run_answer_key_workbench.py import-ai-review --indicator KPI-1 --response <응답.json>
python scripts/run_answer_key_workbench.py minimal-status --indicator KPI-1
python scripts/run_answer_key_workbench.py review-minimal --indicator KPI-1 --by <검토자>
python scripts/run_answer_key_workbench.py approve-consensus --indicator KPI-1 --by <검토자>
```

도구는 모든 AI 불일치와 위험 플래그를 상세 검토 대상으로 잡는다. AI가 합의한 사례에서는 SHA-256으로 5건을 고른다. 사람이 표본 1건을 수정하면 20건으로 늘리고, 2건을 수정하면 모든 합의 사례를 상세 검토한다. 5건은 통계적·임상적 검증 표본이 아니라 오류를 일찍 찾기 위한 임의의 운영 하한이다.

나머지 합의 사례는 사람이 정확한 확인 문구를 직접 입력해야 최종 결정이 생긴다. 일괄 승인 사례는 `reviewed_in_detail: false`로 저장되며 상세 검토 건수와 섞이지 않는다. AI가 사람 승인이나 봉인을 대신 만들 수는 없다.
