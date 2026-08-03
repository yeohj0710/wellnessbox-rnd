# Claude 블라인드 요청 파일 사용법

이 폴더의 JSON 파일 하나만 새 Claude 작업에 전달한다. 저장소, 워크벤치, 엔진 규칙, 엔진 출력, 기존 정답은 전달하지 않는다.

Claude 작업은 `claude.ai`의 Anthropic 계열 모델에서 실행한다. ChatGPT·Codex 응답은 사용할 수 없다. 반환 JSON의 `reviewing_agent` 또는 `drafting_agent`에는 실제 Claude 모델명을 기록하며 `not_recorded`·`unknown`·빈 값은 허용하지 않는다.

- KPI-1·3·5 파일은 `reviewing_agent` 형식의 독립 2차 의견을 요청한다.
- KPI-4 파일은 `drafting_agent` 형식의 독립 1차 초안을 요청한다. 측정 대상 상담 모델이 OpenAI 계열이기 때문이다.
- Claude는 `response_skeleton`의 모든 사례를 채우고 JSON 객체만 반환한다. 빈 답·빈 confidence를 그대로 반환하면 검증이 실패한다.
- 반환 파일은 가져오기 전에 다음처럼 검사한다.

```text
python scripts/run_answer_key_workbench.py validate-ai-response --indicator KPI-3 --role review --provider-family anthropic --response <Claude_응답.json>
```

`READY_TO_IMPORT`와 `mutated: false`를 확인한 뒤에만 대응하는 `import-ai-review` 또는 `import-primary-ai-draft` 명령을 실행한다. 검증과 가져오기는 사람의 최종 판단이나 봉인이 아니다.
