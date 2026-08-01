# KPI 정답지 블라인드 AI 응답 패킷

이 폴더의 JSON 4개는 KPI-1·3·4·5 각 100건을 AI가 독립적으로 판단할 수 있게 만든 입력이다. 패킷에는 사례 ID와 질문, 공용 답변 어휘만 있다. 기존 초안의 답·근거, 엔진 로직 9개 내용, 엔진 출력은 넣지 않았다.

## AI에는 패킷만 전달한다

KPI-1·5에는 독립 1차 초안이 있다. 사람의 상세 검토량을 줄이려면 다른 제공자 계열 AI에 패킷만 전달해 2차 의견을 받는다. KPI-3에는 아직 정답 초안이 없으므로 서로 다른 제공자 계열 AI 응답이 두 개 필요하다. KPI-4의 문항은 준비됐지만, 측정 대상 상담 모델이 OpenAI 계열이면 현재 Codex 답을 봉인하지 않고 비-OpenAI 계열의 블라인드 1차 답으로 교체한다. 저장소 전체나 워크벤치 원본을 함께 전달하면 블라인딩이 깨진다.

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

KPI-3의 첫 응답과 KPI-4의 대체 1차 응답은 필드 이름을 `drafting_agent`, `draft_source`로 바꾼 뒤 아래 명령으로 가져온다.

```powershell
python scripts/run_answer_key_workbench.py import-primary-ai-draft --indicator KPI-3 --response <1차_응답.json>
python scripts/run_answer_key_workbench.py import-ai-review --indicator KPI-3 --response <다른_제공자_2차_응답.json>
# KPI-4도 같은 두 명령을 --indicator KPI-4로 실행한다.
```

가져오기 도구는 1차 응답의 답과 출처를 `blind_primary_ai_response_v1@adaptive_answer_key_review` 경로에 묶어 기록한다. 원래의 빈 정답 상황 생성 모듈을 답의 출처로 잘못 기록하지 않는다. 현재 작업처럼 엔진 정책을 이미 읽은 AI는 블라인드 답안 작성자나 검수자 역할을 맡지 않는다.

KPI-4의 측정 대상 상담 모듈은 OpenAI 계열이다. 따라서 현재 Codex 1차 초안을 그대로 봉인할 수 없다. Claude의 블라인드 응답을 KPI-3과 같은 `import-primary-ai-draft` 명령으로 1차 초안에 넣고, 새 블라인드 Codex 작업의 응답을 `import-ai-review`로 가져온다.

## 사람은 불일치와 표본을 판단한다

```powershell
python scripts/run_answer_key_workbench.py import-ai-review --indicator KPI-1 --response <응답.json>
python scripts/run_answer_key_workbench.py minimal-status --indicator KPI-1
python scripts/run_answer_key_workbench.py review-minimal --indicator KPI-1 --by <검토자>
python scripts/run_answer_key_workbench.py approve-consensus --indicator KPI-1 --by <검토자>
```

도구는 모든 AI 불일치와 위험 플래그를 상세 검토 대상으로 잡는다. AI가 합의한 사례에서는 SHA-256으로 5건을 고른다. 사람이 표본 1건을 수정하면 20건으로 늘리고, 2건을 수정하면 모든 합의 사례를 상세 검토한다. 5건은 통계적·임상적 검증 표본이 아니라 오류를 일찍 찾기 위한 임의의 운영 하한이다.

나머지 합의 사례는 사람이 정확한 확인 문구를 직접 입력해야 최종 결정이 생긴다. 일괄 승인 사례는 `reviewed_in_detail: false`로 저장되며 상세 검토 건수와 섞이지 않는다. AI가 사람 승인이나 봉인을 대신 만들 수는 없다.

두 AI가 4개 지표의 모든 사례에서 합의하고 위험 플래그가 없다면, 사람의 상세 검토 하한은 400건이 아니라 지표별 5건, 합계 20건이다. 사람은 지표별 일괄 승인도 한 번씩 직접 입력한다. 불일치·위험 플래그·표본 수정이 있으면 상세 검토 건수는 늘어나며, 최악의 경우 400건 전체를 검토한다.

## 감사가 증명하지 못하는 범위

가져오기 도구는 응답 파일에 적힌 `engine_output_consulted: false`와 `blinded_from`을 검증한다. 그러나 외부 AI가 실제로 무엇을 보았는지는 저장소에서 독립적으로 관찰할 수 없다. 외부 AI 실행자는 패킷만 전달했다는 운영 증빙을 따로 보존해야 한다. AST 감사가 `adaptive_answer_key_review.py`를 통과했다는 사실은 가져오기 코드가 엔진 파일을 읽지 않았다는 뜻이지, 외부 AI의 블라인딩을 직접 증명한다는 뜻은 아니다.

제공자 계열은 `codex`, `claude`, `gemini` 같은 실행 주체 문자열에서 추정한다. 알 수 없는 문자열은 서로 다른 제공자로 간주하지 않고 가져오기를 거부한다. 이 추정도 제공자 계열의 독립성을 암호학적으로 증명하지는 않는다.

KPI-4를 봉인할 때는 `--system-under-test-provider-family`도 입력한다. 1차 초안 작성 AI와 상담 모델의 제공자 계열이 같으면 봉인을 거부한다.
