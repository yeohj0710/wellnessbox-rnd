# 권혁찬 약사·오너 최종 세션 실행서

## 먼저 확인할 결론

이 세션의 실행 순서는 **H-007 실제 5개 프로필 → 생성된 AI 초안 확인 → H-003 권혁찬 약사 전수 검토 → 승인 초안의 학습·평가 반영 확인 → H-002 정책 승인과 H-004 문체 승인 → H-005 고위험 10건 약사 안전 검토 → H-006 최종 영수증**이다.

다음 세 조건을 모두 충족하지 못하면 세션을 시작하지 않는다.

1. 5개 프로필의 실제 복용 전 자료와 실제 후속평가 자료가 준비돼 있다. 후속 자료가 아직 없으면 관찰 기간이 끝날 때까지 H-007을 완료할 수 없다.
2. `etc/final_session_private/final_session_signing_key.pem`이 이미 있다. H-007 운영 영수증 검증에는 이 키가 필요하지만, 새 키를 만드는 H-006은 요청된 순서상 마지막이다.
3. H-005 입력 화면의 선택과 의견이 모두 비어 있다. 현재 `data/original_plan/final_session/op039_external_reviewer_form.html`은 10건을 `타당`으로 선택하고 의견까지 채워 두므로 이번 세션에 그대로 쓰면 안 된다.

이 문서는 판단 결과, 승인, 서명, 실제 사용 값을 대신 입력하지 않는다. 표에 적은 H-007 프로필은 입력 분산을 확인하기 위한 **제안안**이다. 운영자는 실제 참여자 자료와 대조해 고쳐야 한다. H-005의 `시스템 신호`도 약사의 결론이 아니다.

## 누가 무엇을 맡는가

| 역할 | 맡을 일 | 대신할 수 없는 결정 |
|---|---|---|
| 운영 보조자 | 명령 실행, 서버 상태 확인, 실제 자료 준비, 화면 전환, 증거 경로 기록 | 약사 판정, 오너 승인, 서명 |
| 권혁찬 약사 | H-003 전수 검토, H-002 정책 검토, H-005 고위험 10건 판정 | 시스템이나 오너가 대신 입력할 수 없음 |
| 오너 | H-004 보고서 문체 승인, H-006 최종 영수증 발급·확인 | 약사 판정을 대신할 수 없음 |

권혁찬 약사는 H-003부터 H-005까지 한 번에 처리한다. 운영 보조자는 권혁찬 약사가 도착하기 전에 H-007과 초안 생성 여부를 끝내고, 각 검토 화면을 바로 열 수 있게 준비한다. 오너는 H-004와 H-006 때만 참여한다.

## 현재 파일은 새 판단을 대신하지 않는다

`data/original_plan/final_session/session_state_v1.json`은 2026-07-23~24의 저장 상태를 `AUDIT`와 완료 상태로 기록하고, `data/original_plan/evidence/op120_final_completion_audit_v1.json`은 당시 입력을 기준으로 `READY`와 빈 차단 목록을 기록한다. H-003에는 검토자 `웰니스박스`, 생성·검토 초안 0건도 기록돼 있다.

이 값은 저장된 과거 상태라는 사실만 보여 준다. 이번 세션에서 권혁찬 약사가 실제 초안을 검토했다는 증거로 재사용하거나, 기존 H-005 판정을 복사하거나, 기존 서명을 새 세션의 서명으로 간주하지 않는다. **과거 상태를 보존한 채 새 세션을 여는 방법은 확인 필요**다. 확인 범위는 다음 파일이다.

- `src/wellnessbox_rnd/governance/final_session_console.py`
- `data/original_plan/final_session/session_state_v1.json`
- `data/original_plan/final_session/external_validation/op039_external_validation.json`
- `data/original_plan/final_session/final_validation_receipt_v1.json`
- `data/original_plan/final_session/independent_final_review_receipt_v1.json`

기존 파일을 삭제하거나 덮어쓰지 않는다. 세션 ID 분리 방법이 정해질 때까지 새 판단 제출을 멈춘다.

## 전체 순서와 예상 시간

시간은 실제 측정값이 아닌 일정 수립용 추정치다. H-003의 60~120분만 `human_signoff_checklist.md`의 예상 범위를 따른다.

| 순서 | 단계 | 담당 | 선행 조건 | 예상 시간 | 완료 기준 | 중단 조건 |
|---:|---|---|---|---:|---|---|
| 0 | 사전 확인과 서버 시작 | 운영 보조자 | 실제 자료, 중립 H-005 화면, 서명 키 | 10~15분 | 준비 완료 문구와 두 URL 확인 | DB 없음, 키 없음, 서버 준비 실패 |
| 1 | H-007 실제 프로필 5개 | 운영 보조자 | 실제 복용 전·후속 자료 | 50~75분 | 서로 다른 실제 프로필 5개가 전체 경로를 마치고 영수증 대상이 됨 | 가상값·자동 저장·후속 자료 부재 |
| 2 | AI 초안 생성·대기열 확인 | 운영 보조자 | H-007 결과 | 5분 | 실제 생성 초안 수와 대기 수를 기록 | 생성돼야 할 초안이 0건 |
| 3 | H-003 전수 검토 | 권혁찬 약사 | 대기열과 근거 표시 | 60~120분 | 모든 초안이 승인·수정 승인·반려 중 하나이며 대기 0건 | 빈 대기열을 실제 검토로 확인하려는 경우 |
| 4 | 승인 초안 학습·평가 1회 | 운영 보조자, 결과는 약사에게 보고 | H-003 대기 0건 | **확인 필요** | 승인 초안만 입력되고 평가 결과·모델 변경 여부가 기록됨 | 실행 명령과 입력 계보가 확인되지 않음 |
| 5 | H-002 정책 승인 | 권혁찬 약사 | H-003과 1회 평가 결과 | 10분 | 9개 규칙을 모두 확인하고 실제 승인 또는 수정 의견 저장 | 불리한 상태를 완화하는 임의 변경 |
| 6 | H-004 보고서 문체 승인 | 오너 | 검토할 실제 보고서 2~3편 | 10~15분 | 표본 2~3편에 실제 승인 또는 의견 저장 | 표본 본문이 열리지 않음 |
| 7 | H-005 고위험 10건 검토 | 권혁찬 약사 | 중립 화면, 자격 확인 방법 | 30~45분 | 10건 각각 실제 판정·근거, 자격 확인 방법, 실제 서명 저장 | 선택·의견이 미리 채워짐 |
| 8 | H-006 최종 영수증 | 오너 | H-002~H-005 완료, H-007 영수증 유효 | 5~10분 | 최종 검증·독립 검토 영수증과 서명 검증 완료 | 감사 차단 목록이 비어 있지 않음 |
| 9 | 종료·최종 감사 | 운영 보조자 | H-006 완료 | 5~10분 | 운영 영수증 경로와 감사 `READY` 확인 | 종료 전에 영수증 경로가 없음 |

모든 입력이 미리 준비됐을 때 사람과 운영 보조자의 합산 활동 시간은 **약 185~305분(3시간 5분~5시간 5분)**이다. 실제 후속 관찰 기간과 실행 방법이 확인되지 않은 학습·평가 시간은 제외했다. 권혁찬 약사의 예상 활동 시간은 100~175분, 오너의 예상 활동 시간은 15~25분이다.

## 세션 전에 이 명령만 순서대로 실행한다

아래 명령은 실제 사전 점검으로 검증한 순서다. PowerShell에서 한 줄씩 실행하고, 앞 단계가 정상일 때만 다음 단계로 간다.

### 1. 작업 폴더로 이동한다

```powershell
Set-Location C:\dev\wellnessbox-rnd
```

정상 결과: 오류 없이 프롬프트가 돌아온다.

### 2. 실행용 Python이 있는지 확인한다

```powershell
Test-Path .\.venv-interim\Scripts\python.exe
```

정상 결과: `True`. `False`면 세션을 멈추고 가상환경 설치 범위를 확인한다.

### 3. 운영 DB의 현재 수와 대기 초안을 확인한다

```powershell
.\.venv-interim\Scripts\python.exe scripts\report_operational_session_readiness.py
```

정상 출력의 형태:

```json
{
  "database": "C:\\dev\\wellnessbox-rnd\\etc\\local_research_runtime\\interim.sqlite3",
  "distinct_actual_profiles": 0,
  "target_distinct_profiles": 5,
  "pending_pharmacist_drafts": 0,
  "automatic_receipt_generation": false,
  "next_action": "사람이 실제 프로필의 전체 경로를 실행한다"
}
```

`distinct_actual_profiles`와 `pending_pharmacist_drafts`의 숫자는 현재 DB에 따라 달라진다. 이 스크립트는 `INTERIM_RUNTIME_EVENT` 프로필 수를 세므로, 필드 이름만 보고 실제 사람 자료라고 판단하지 않는다. `status: "missing"`이면 DB가 없다는 뜻이며 세션을 시작하지 않는다. `automatic_receipt_generation`이 `false`인 것이 정상이다.

### 4. H-007 운영 영수증용 서명 키를 확인한다

```powershell
Test-Path .\etc\final_session_private\final_session_signing_key.pem
```

정상 결과: `True`. `False`면 세션을 멈춘다. 현재 구현에서는 H-006이 키를 만들지만, 요청된 실행 순서는 H-007을 먼저 둔다. 오너가 **기존 키를 쓸지, H-006의 키 준비만 앞당길지** 결정해야 한다. 이 문서는 키를 만들거나 선택하지 않는다.

### 5. 운영 영수증을 만들지 않는 사전 점검을 실행한다

```powershell
.\.venv-interim\Scripts\python.exe scripts\run_final_session_preflight.py
```

이 명령은 SQLite 본체와 WAL을 파일 단위로 복사하고 복사 전후의 본체·WAL·SHM hash가 같은지 확인한다. 복사 중 원본이 바뀌거나 임시 DB의 `PRAGMA integrity_check`가 실패하면 즉시 `ERROR`로 끝난다. 최종 확인 상태는 임시 폴더에 만들며, R&D API와 최종 확인 화면, WellnessBox 사용자·약사 화면에는 GET 요청만 보낸다. H-005는 Chromium이 실제로 렌더링한 DOM의 선택값과 의견값을 검사한다. 이 명령이 시작한 PID 트리만 종료한다.

실행 전후에는 실제 DB 본체·WAL·SHM, 운영 캡처와 프로세스 제어 파일, 최종 세션 루트의 직접 파일, 운영 영수증 전체를 파일별 hash로 비교한다. 사람 입력, 약사 판정, 승인, 서명, 실제 운영 영수증은 만들지 않는다.

`status: "READY"`, `exit_code: 0`, 빈 `blockers`, 아래 다섯 저장 불변 값이 모두 `true`일 때만 정상이다.

- `database_unchanged`
- `runtime_controls_unchanged`
- `final_state_unchanged`
- `receipt_file_list_unchanged`
- `receipt_hashes_unchanged`

**사전 점검에서는 `.\research-server-start.cmd`를 실행하지 않는다.** 현재 구현은 이 명령이 서버를 정상 종료할 때 DB 변화가 0건이어도 `data_class: "ACTUAL"` 운영 영수증을 만든다. 기존 운영 영수증을 나중에 삭제하는 방식도 허용하지 않는다.

### 6. 사전 점검 출력과 실제 자료를 마지막으로 확인한다

- R&D health, 최종 확인 화면, 최종 확인 상태, WellnessBox health가 모두 200이다.
- 사용자 화면과 약사 화면의 로그인 응답이 307이고, 이동한 화면이 각각 200이다.
- H-005의 사례와 의견란은 각각 10개이며, 렌더링된 DOM의 `preselected_count`와 `prefilled_comment_count`가 모두 0이다.
- 실제 DB·제어 파일·최종 세션 상태·운영 영수증의 다섯 불변 값이 모두 `true`다.
- 5개 프로필마다 실제 복용 전 자료, 실제 후속평가 자료, 동의 근거가 준비돼 있다.

하나라도 아니면 실제 입력을 시작하지 않는다. `BLOCKED`는 서버 고장이 아니라 사람이 해결해야 할 시작 조건이 남았다는 뜻이다. `ERROR`는 서버·UI 점검 실패 또는 운영 저장 변경을 뜻한다.

사전 점검이 `READY`이고 실제 자료까지 준비된 뒤에만 H-007 실제 운영을 시작한다. 그때 별도 창에서 `.\research-server-start.cmd`를 실행한다. 이 시점부터는 사전 점검이 아니며, 정상 종료 시 실제 운영 영수증이 생성된다.

### 2026-07-27 무영수증 사전 점검 실제 출력

실행 명령은 위 5번 한 줄이며 프로세스 종료 코드는 `2`였다.

```json
{
  "schema_version": "final_session_preflight_v1",
  "status": "BLOCKED",
  "exit_code": 2,
  "operational_receipt_generation": false,
  "human_actions_performed": false,
  "temporary_database": true,
  "temporary_final_state": true,
  "checks": {
    "rnd_health": 200,
    "console_home": 200,
    "console_state": 200,
    "wellnessbox_health": 200,
    "tips": {
      "login_status": 307,
      "page_status": 200,
      "final_url": "http://127.0.0.1:3001/tips"
    },
    "pharmacist": {
      "login_status": 307,
      "page_status": 200,
      "final_url": "http://127.0.0.1:3001/pharm/tips"
    },
    "h005": {
      "status": 200,
      "case_count": 10,
      "preselected_count": 10,
      "comment_count": 10,
      "prefilled_comment_count": 10
    }
  },
  "storage": {
    "database_unchanged": true,
    "runtime_controls_unchanged": true,
    "final_state_unchanged": true,
    "receipt_file_list_unchanged": true,
    "receipt_hashes_unchanged": true
  },
  "storage_evidence": {
    "database_family_before": {
      "interim.sqlite3": {
        "path": "C:\\dev\\wellnessbox-rnd\\etc\\local_research_runtime\\interim.sqlite3",
        "exists": true,
        "sha256": "856817703a430d42b7f7f4689b2b214caee6d727a2efcc59766d515f2a448e87",
        "size": 761856
      },
      "interim.sqlite3-wal": {
        "path": "C:\\dev\\wellnessbox-rnd\\etc\\local_research_runtime\\interim.sqlite3-wal",
        "exists": true,
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "size": 0
      },
      "interim.sqlite3-shm": {
        "path": "C:\\dev\\wellnessbox-rnd\\etc\\local_research_runtime\\interim.sqlite3-shm",
        "exists": true,
        "sha256": "fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb",
        "size": 32768
      }
    },
    "database_family_after": {
      "interim.sqlite3": {
        "path": "C:\\dev\\wellnessbox-rnd\\etc\\local_research_runtime\\interim.sqlite3",
        "exists": true,
        "sha256": "856817703a430d42b7f7f4689b2b214caee6d727a2efcc59766d515f2a448e87",
        "size": 761856
      },
      "interim.sqlite3-wal": {
        "path": "C:\\dev\\wellnessbox-rnd\\etc\\local_research_runtime\\interim.sqlite3-wal",
        "exists": true,
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "size": 0
      },
      "interim.sqlite3-shm": {
        "path": "C:\\dev\\wellnessbox-rnd\\etc\\local_research_runtime\\interim.sqlite3-shm",
        "exists": true,
        "sha256": "fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb",
        "size": 32768
      }
    },
    "runtime_control_manifest_sha256_before": "45d2d47b8b9c61f14c8dd74ddd0ee96160744ce4a752f87d193dab2de0a9e1bb",
    "runtime_control_manifest_sha256_after": "45d2d47b8b9c61f14c8dd74ddd0ee96160744ce4a752f87d193dab2de0a9e1bb",
    "final_state_file_count_before": 13,
    "final_state_file_count_after": 13,
    "final_state_manifest_sha256_before": "fcd74398346da0200b8cf6bd1fc628255abea63a2750d90e75e8a44b37b76a35",
    "final_state_manifest_sha256_after": "fcd74398346da0200b8cf6bd1fc628255abea63a2750d90e75e8a44b37b76a35",
    "receipt_file_count_before": 15,
    "receipt_file_count_after": 15,
    "receipt_manifest_sha256_before": "a73f8e25c2b3fdefe956635ca7092a3f071d4ac10155b6b7e28a69dcc13bf39a",
    "receipt_manifest_sha256_after": "a73f8e25c2b3fdefe956635ca7092a3f071d4ac10155b6b7e28a69dcc13bf39a"
  },
  "blockers": [
    {
      "id": "H005_FORM_NOT_NEUTRAL",
      "message": "H-005 10/10 cases are preselected and 10/10 comments are prefilled."
    }
  ]
}
```

서버와 두 화면은 모두 응답했지만 H-005의 렌더링된 DOM은 10건 모두 `타당`으로 미리 선택됐고 의견란 10개도 모두 채워져 있었다. 따라서 실제 입력을 시작하지 않는다. 실제 DB 본체·WAL·SHM, 운영 캡처·프로세스 제어 파일, 최종 세션 직접 파일 13개, 기존 운영 영수증 15개는 실행 전후 동일했고 새 운영 영수증은 생기지 않았다.

## H-007: 자동 저장 없이 실제 5개 프로필을 입력한다

### 다섯 프로필은 이렇게 다르게 준비한다

아래 값은 화면과 코드가 서로 다른 나이·목표·복용약을 처리하는지 확인하기 위한 **제안안**이다. 실제 참여자 값이 아니며 저장하거나 실제 자료로 표시하면 안 된다. 운영자는 세션 전에 각 행을 실제 참여자 자료로 교체하고, 실제 복용약 이름·용량·복용 빈도를 원문대로 확인한다.

| 프로필 | 나이 제안 | 목표 제안 | 복용약 제안 | 실제 자료로 교체했는가 | 후속 자료가 있는가 |
|---|---:|---|---|---|---|
| 1 | 41 | 수면 질 | 없음 | 미확인 | 미확인 |
| 2 | 58 | 심혈관 건강 | warfarin | 미확인 | 미확인 |
| 3 | 29 | 에너지 | levothyroxine | 미확인 | 미확인 |
| 4 | 67 | 뼈·관절 건강 | metformin | 미확인 | 미확인 |
| 5 | 36 | 장 건강 | omeprazole | 미확인 | 미확인 |

`없음`도 실제 복용약 확인 결과가 없을 때만 입력한다. 추정값, 자동 생성값, 다른 프로필의 복사값을 쓰지 않는다.

### 프로필마다 같은 화면 순서로 한 번씩 처리한다

1. 최종 확인 화면에서 `고급 기능`을 연다.
2. `전체 사용자 화면 열기`를 누른다.
3. 주소가 `/research-login?redirect=/tips`를 거쳐 `/tips`로 이동했는지 확인한다.
4. 사용자 화면에서 새 실제 프로필을 선택하거나 만든다. 프로필 ID가 앞선 네 건과 다른지 기록한다.
5. 동의, 나이, 목표, 복용약, 복용 전 설문을 실제 자료와 대조해 사람이 입력한다.
6. 화면에 입력값 요약이 있으면 원자료와 다시 대조한다.
7. 사용자 화면의 저장·추천 실행 동작을 한 번만 누른다. **최종 확인 화면의 `복용 전 상태 저장` 버튼은 누르지 않는다.** 이 버튼은 고정 예시값을 자동 저장한다.
8. 추천 결과에서 실행 ID, 프로필 ID, 계획 ID, 안전 신호, 생성 시각을 기록한다. 주문이나 결제는 만들지 않는다.
9. 약사 화면이 필요하면 최종 확인 화면의 약사 링크를 열어 `/research-login?redirect=/pharm/tips`를 거쳐 `/pharm/tips`로 이동한다.
10. 실제 후속평가 시점에 같은 프로필 ID·실행 ID·계획 ID를 선택한다. 실제 순응도, 실제 이상사례, 실제 설문을 입력한다.
11. 후속평가 저장 동작을 한 번만 누른다. **최종 확인 화면의 `후속평가 저장` 버튼은 누르지 않는다.** 이 버튼도 고정 예시값을 자동 저장한다.
12. 약사 검토가 필요한 초안은 판단하지 말고 H-003 대기열에 남긴다. 운영 보조자는 승인·수정 승인·반려를 누르지 않는다.
13. 화면을 새로 열어 저장된 프로필 ID·실행 ID·계획 ID가 원래 값과 같은지 확인한다.
14. 다음 프로필로 이동한다. **`다음 프로필로 이동`의 고정 프로필 자동화는 쓰지 않는다.**

사용자 화면 내부의 실제 필드명과 저장 버튼명은 이 저장소에서 확인되지 않았다. 확인 범위는 연결 저장소 `C:\dev\wellnessbox`의 사용자 화면 구현이다. 운영자는 화면에 표시된 이름을 확인해 이 실행서에 기록한 뒤 시작한다. 확인하지 않은 버튼 이름을 추정해 누르지 않는다.

### H-007 완료를 무엇으로 확인하는가

다음 조건을 모두 만족해야 한다.

- 서로 다른 프로필 ID가 5개 이상이다.
- 각 프로필은 실제 자료 분류와 지정 환경 `wellnessbox-local-research-pc`를 사용한다.
- 각 프로필의 실행 경로와 실행 ID가 비어 있지 않다.
- 복용 전 입력, 추천, 후속평가, 필요한 약사 검토가 같은 프로필·실행·계획 계보로 연결된다.
- 서명된 운영 영수증의 payload hash와 Ed25519 서명이 유효하다.
- H-007 운영 적용 범위가 41/41이다.

서버 시작만으로는 완료가 아니다. 자동 생성 프로필이나 고정 예시값도 증거가 아니다. 실제 후속평가가 준비되지 않았다면 H-007은 `확인 필요`로 남기고 세션을 끝낸다.

## H-003: 생성된 AI 초안을 권혁찬 약사가 전수 검토한다

### 먼저 대기열이 실제로 생겼는지 확인한다

운영 보조자는 H-007 뒤 `scripts/report_operational_session_readiness.py`를 다시 실행해 `pending_pharmacist_drafts`를 기록한다. 생성돼야 할 실제 초안이 0건이면 `검토 대상 없음 확인`으로 통과하지 않는다. H-007 실행 ID와 초안 생성 경로를 먼저 조사한다.

### 권혁찬 약사의 실제 클릭 순서

1. 최종 확인 화면의 H-003에서 검토자 이름이 `권혁찬`인지 직접 확인한다.
2. `대기 초안 보기`를 누른다.
3. 한 건의 프로필 요약, 초안, 근거, 금기·상호작용·응급 신호를 읽는다.
4. 권혁찬 약사가 직접 `승인`, `수정 승인`, `반려` 중 하나를 누른다.
5. `수정 승인`이면 권혁찬 약사가 수정 내용을 입력한다. `반려`이면 권혁찬 약사가 반려 이유를 입력한다.
6. 화면이 다음 건으로 자동 이동하면 같은 절차를 반복한다.
7. 대기 건수가 0이 될 때까지 계속한다.
8. 생성 수, 검토 수, 승인 수, 수정 승인 수, 반려 수, 대기 수를 기록한다. 승인율이나 처리 속도로 약사 검토 품질을 판정하지 않는다.

승인·수정 승인 초안만 하류 입력에 쓸 수 있다. 대기·반려 초안은 학습, 평가, 추천, 지식 반영에 쓰면 안 된다.

### 학습·평가 1회는 현재 무엇이 막혀 있는가

`src/wellnessbox_rnd/governance/final_session_console.py`의 `_run_draft_downstream_cycle`은 승인 초안을 학습·평가 입력으로 등록하고 소비 건수를 기록한다. 현재 `data/original_plan/final_session/ai_draft_downstream_cycle_v1.json`은 승인 초안 6건을 학습·평가 입력으로 등록했지만, 새 모델 학습·교체는 하지 않았다고 명시한다. `approved_draft_eval_comparison_v1.json`도 기준 모델과 후보 모델의 256건 평가 결과가 같다고 기록한다.

`scripts/run_interim_pipeline.py retrain`은 별도 패키지의 `run_interim_proxy_research.py`를 실행한다. 이 명령이 H-003 승인 초안을 입력으로 읽는 계보는 확인되지 않았다. 따라서 이 실행서에는 학습 명령을 제시하지 않는다.

현재 저장소에서 안전하게 확정할 수 있는 명령은 고정 평가 세트 확인, 현재 기준 모델 평가, 이미 만들어진 두 평가 보고서의 산술 비교뿐이다. 아래 명령은 H-003 승인 데이터가 준비돼도 누락된 학습 계보가 구현되기 전에는 실행하지 않는다.

```powershell
(Get-FileHash -Algorithm SHA256 data\frozen_eval\frozen_eval_v1.jsonl).Hash
python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl --output-dir <baseline-output-dir>
python scripts/compare_eval_reports.py --baseline-report <baseline-report.json> --candidate-report <candidate-report.json> --output-json <comparison.json> --output-md <comparison.md>
```

고정 평가 세트는 256건이고 현재 SHA-256은 `ba134edbade51d02ad4014a7a66626559eb454967736495d1e60fbcf95b3a960`이다. `run_eval.py`는 후보 모델이나 artifact 인자를 받지 않고 항상 같은 `recommend` 함수를 호출한다. 따라서 두 번째 후보 모델 평가 명령은 현재 만들 수 없다. `compare_eval_reports.py`도 차이만 계산하고 안전 지표가 나빠졌을 때 실패시키지 않는다.

다음 항목을 구현 담당자가 확인하기 전에는 “승인 초안으로 학습·평가 1회를 완료했다”고 승인하지 않는다.

- 승인 초안 ID가 학습 입력 레코드로 연결되는 코드와 명령
- 대기·반려 초안을 제외하는 실행 로그
- 학습 데이터셋 ID, 모델 ID, 코드 버전, 설정 hash
- 고정 평가셋 1회 결과와 기준 모델 비교
- 모델을 교체하지 않았으면 그 결정과 이유
- 승인 초안만 담은 데이터셋 manifest와 초안 ID 계보
- 후보 artifact를 입력받는 고정 평가 실행기와 안전 회귀 실패 조건
- 모델 교체·유지 결정과 rollback 영수증

확인 범위:

- `src/wellnessbox_rnd/governance/final_session_console.py::_run_draft_downstream_cycle`
- `scripts/run_interim_pipeline.py`
- `data/original_plan/final_session/ai_draft_downstream_cycle_v1.json`
- `data/original_plan/final_session/approved_draft_eval_comparison_v1.json`

## H-002: 9개 다음 행동 규칙을 10분 안에 확인한다

아래 표는 `data/original_plan/closed_loop_next_action_policy_v1.json`의 우선순위 순서다. 상태는 모두 `FOLLOWUP_ACTIVE`다. 코드는 위에서부터 처음 일치한 규칙 하나를 적용한다. 권혁찬 약사는 표를 읽고 화면에서 실제 승인 또는 수정 의견을 입력한다. 이 표는 승인을 미리 선택하지 않는다.

| 우선순위 | 규칙 | 상태 × 이벤트 조건 | 시스템 행동 → 목표 상태 | 보수적 안전 표시 |
|---:|---|---|---|---|
| 10 | NA-001 | 후속 진행 중 × 이상사례 있음 | 복용 중단·상향 보고 `stop_and_escalate` → `ESCALATED` | **가장 보수적. 다른 조건보다 먼저 중단** |
| 20 | NA-002 | 후속 진행 중 × 성분 불내성 있음, 이상사례 없음 | 성분 교체 `replace` → `PLAN_REPLACED` | 불내성 성분 유지 금지 |
| 30 | NA-003 | 후속 진행 중 × 용량 관련 문제 있음, 이상사례 없음 | 감량 `reduce` → `PLAN_REDUCED` | 기존 용량 유지 금지 |
| 40 | NA-004 | 후속 진행 중 × 안전 검토 필요, 이상사례 없음 | 안전 검토 요청·보류 `request_safety_review` → `FOLLOWUP_REVIEW` | **판단 전 추천 보류** |
| 50 | NA-005 | 후속 진행 중 × 후속평가 미제출, 이상사례 없음 | 후속평가 요청 `request_followup` → `FOLLOWUP_REVIEW` | 자료 없이 유지·변경 결정 금지 |
| 60 | NA-006 | 후속 진행 중 × 측정 미완료, 이상사례 없음 | 추가 측정 요청 `request_measurement` → `FOLLOWUP_REVIEW` | 자료 없이 유지·변경 결정 금지 |
| 70 | NA-007 | 후속 진행 중 × 결과가 모호함, 이상사례 없음 | 검토 대기 `hold_for_review` → `FOLLOWUP_REVIEW` | **불확실하면 추천 보류** |
| 80 | NA-008 | 후속 진행 중 × 점수 변화가 0보다 큼, 이상사례 없음 | 조합 유지 `maintain` → `PLAN_MAINTAINED` | 개선 확인 뒤 유지 |
| 90 | NA-009 | 후속 진행 중 × 점수 변화가 0 이하, 이상사례 없음 | 재최적화 `reoptimize` → `PLAN_REOPTIMIZATION` | **악화·무개선이면 재최적화** |

검토 순서:

1. 이상사례가 언제나 NA-001로 먼저 중단되는지 본다.
2. 불내성·용량 문제·안전 검토가 유지보다 먼저 적용되는지 본다.
3. 자료 미제출·미측정·모호함이 모두 보류 또는 추가 입력으로 이어지는지 본다.
4. 개선일 때만 유지하고, 0 또는 악화면 재최적화하는지 본다.
5. 최종 확인 화면에서 `정책 전체 확인` 또는 `규칙 수정 의견 남기기`를 권혁찬 약사가 직접 누른다.

현재 결정적 평가 근거 `data/original_plan/evidence/op071_op080_closed_loop_next_action_policy_v1.json`은 130/130, 100%를 기록하고 목표 80%를 넘는다. 이 수치는 의약학적 승인 자체가 아니다.

## H-004: 오너가 보고서 2~3편의 문체만 확인한다

1. H-004 화면에 표시된 무작위 보고서 2~3편의 ID를 적는다.
2. 각 보고서의 결론, 근거 경로, 불확실성 표현, 실제로 하지 않은 일을 했다고 쓰지 않았는지 본다.
3. 오너가 실제 의견을 입력한다.
4. 오너가 `문체 확인`을 누른다.

현재 `session_state_v1.json`에는 과거 표본 `OP-081`, `OP-028`, `OP-117`과 과거 승인이 있다. 이번 세션의 새 표본·새 판단으로 간주하지 않는다.

## H-005: 권혁찬 약사가 고위험 10건을 빈 선택지에서 판단한다

### 현재 화면을 그대로 쓰지 않는다

`data/original_plan/final_session/op039_external_reviewer_form.html`에는 10건 모두 `타당`이 선택돼 있고 AI 의견도 입력돼 있다. 자격 정보도 `pharmacist_license_id: "not_collected"`, `credential_verification_method: "project_owner_attestation"`로 고정돼 있다. 이 상태는 중립 검토 요건을 충족하지 못한다.

중립 화면이 준비되기 전에는 `약사 안전 검토 열기`를 누르지 않는다. 중립 화면은 다음 조건을 충족해야 한다.

- 각 사례의 `타당`·`부적절`이 모두 미선택이다.
- 의견 칸이 비어 있다.
- 시스템 판정, 규칙 ID, 근거 경로만 읽기 전용으로 보인다.
- 권혁찬 약사가 실제 자격 확인 방법을 입력할 수 있다.
- `reviewer_role=project_pharmacist`, `relationship_to_project=project_co_researcher`, `independent_of_implementation_team=false`가 사실대로 기록된다.
- 권혁찬 약사가 H-003도 검토했다면 `was_ai_draft_reviewer=true`로 기록하고 시스템 경고를 보존한다.
- 실제 서명 이름은 권혁찬 약사가 제출 직전에 입력한다.

현재 백엔드 검증도 중립 화면을 대신하지 못한다.

- 오너 차단은 이름이 `여형준` 또는 `웰니스박스`와 정확히 같은 경우만 거부한다. 인증 계정이나 오너 원장과 연결하지 않아 별칭을 막지 못한다.
- 프로젝트 공동연구자와 `independent_of_implementation_team=false` 강제는 현재 체크리스트와 일치한다.
- `was_ai_draft_reviewer=true`는 거부가 아니라 경고이며 H-003 검토자 원장과 대조하지 않는다.
- 면허 ID는 빈 문자열만 거부해 `not_collected`도 통과한다. 자격 확인 방법은 검증하지 않는다.
- 서명은 별도 전자서명이 아니라 검토자 이름과 같은 문자열인지 확인한다. 현재 HTML에는 별도 서명 입력도 없다.
- 신뢰 원장 기반 대체 보고서는 검토자 면허와 서명 없이도 H-005 완료 경로에 들어갈 수 있다.

따라서 화면의 사전 선택만 지워서는 충분하지 않다. 실제 검토 전에 검토자 신원 연결, 면허와 자격 확인 방법, 별도 서명 입력, H-003 검토자 대조, 대체 경로의 같은 자격 검증을 구현하고 시험해야 한다. 이번 실행에서는 코드를 만들거나 판정 데이터를 채우지 않았다.

### 10건에서 약사가 볼 정보

`약사 판정`은 모든 행에서 **미선택**이다. `시스템 신호`는 구현이 낸 고위험 표시이며 약사의 결론이 아니다.

| 사례 | 문제와 성분·상호작용 | 근거 위치 | 시스템 신호 | 약사 판정 |
|---|---|---|---|---|
| `pregnancy` | 임신 중 ashwagandha·berberine 후보 | `data/original_plan/evidence/op033_op034_special_population_condition_safety_smoke_v1.json`; NCCIH Ashwagandha, NCBI MotherToBaby Berberine | `BLOCK`, `SAFE-PREG-001`; 서비스 규칙은 `SAFETY-PREG-001`도 사용 | 미선택 |
| `lactation` | 수유 중 ashwagandha·berberine 후보 | 같은 특수집단 증거; NCCIH Ashwagandha, NCBI MotherToBaby Berberine | `BLOCK`, `SAFE-LACT-001`; 서비스 규칙은 `SAFETY-LACT-001`도 사용 | 미선택 |
| `severe_renal_block` | 신부전·투석과 magnesium glycinate 후보 | 같은 특수집단 증거; NIH ODS Magnesium Health Professional | `BLOCK`, `SAFE-RENAL-001`; 서비스 규칙은 `SAFETY-RENAL-SEVERE-001`도 사용 | 미선택 |
| `hepatic_review_block` | 간부전·간경변 등 간 기능 고위험 상태 | 같은 특수집단 증거; 내부 범위 근거 `docs/context/master_context.md` §21.1 | `BLOCK`, `SAFE-HEPATIC-001`; 서비스 규칙은 `SAFETY-HEPATIC-001`도 사용 | 미선택 |
| `hemochromatosis_contraindication` | 혈색소침착증과 iron·vitamin C 후보 | 같은 특수집단 증거; NIH ODS Iron Health Professional | `BLOCK`, `SAFE-HEMO-001`; 서비스 규칙은 `SAFETY-HEMO-001`도 사용 | 미선택 |
| `warfarin_glucosamine` | warfarin과 glucosamine 병용 | `data/original_plan/evidence/op035_op036_interaction_dose_aggregation_smoke_v1.json`; `data/knowledge/supplements/supplement_overdose_and_drug_interactions_expert.md`; `data/raw_references/supplement_warfarin_interaction.md` | `BLOCK`, `KB-SAFETY-ANTICOAG-001`, `REF-KNOWLEDGE-ANTICOAG-001` | 미선택 |
| `warfarin_omega3` | warfarin과 omega-3 병용 | 같은 상호작용 증거; NIH ODS Omega-3 Fatty Acids Health Professional | `NEEDS_REVIEW`, `SAFETY-ANTICOAG-001` | 미선택 |
| `vitamin_c_above_limit` | vitamin C 합산 2,200 mg/day | `data/original_plan/evidence/op037_op038_dose_limit_rule_metadata_smoke_v1.json`; 한도 2,000 mg/day는 `data/rules/safety_rules.json` | `BLOCK`, `SAFETY-DOSE-VITC-001` | 미선택 |
| `emergency_final_authority` | 응급 신호가 있는 추천 요청 | `data/original_plan/evidence/op040_final_safety_authority_integration_smoke_v1.json`; 응급 예시는 `src/wellnessbox_rnd/interim/safety.py` | `STOP_AND_ESCALATE`, `SAFE-EMERGENCY-001` | 미선택 |
| `emergency_zero_recommendations` | 응급 신호 최종 차단 뒤 추천 0건인지 확인 | 같은 최종 안전 권한 통합 증거 | `BLOCKED_ZERO_RECOMMENDATIONS`, `SAFE-EMERGENCY-001`, 추천 수 0 | 미선택 |

외부 근거 주소는 근거 JSON에 기록된 다음 자료를 연다.

- NCCIH Ashwagandha: `https://www.nccih.nih.gov/health/ashwagandha`
- NCBI MotherToBaby Berberine: `https://www.ncbi.nlm.nih.gov/books/NBK600384/`
- NIH ODS Magnesium: `https://ods.od.nih.gov/factsheets/Magnesium-HealthProfessional/`
- NIH ODS Iron: `https://ods.od.nih.gov/factsheets/Iron-HealthProfessional/`
- NIH ODS Omega-3: `https://ods.od.nih.gov/factsheets/Omega3FattyAcids-HealthProfessional/`

### 근거가 부족하거나 표현이 다른 항목

다음 항목은 약사가 판단하기 전에 추가 확인한다.

- `hepatic_review_block`: 저장된 근거는 프로젝트 범위 문서다. 외부 의약학·규제 근거 위치는 확인 필요다.
- `vitamin_c_above_limit`: 2,000 mg/day 규칙과 결정적 증거는 있으나, 증거 JSON의 `reference_ids`와 외부 인용은 비어 있다. 외부 근거 위치는 확인 필요다.
- 두 응급 사례: 통합 증거에 실제로 넣은 응급 증상 이름이 패키지에 없다. 흉통, 아나필락시스, 자살사고, 중증 출혈 중 어떤 입력이었는지 확인 필요다.
- 임신·수유·중증 신장·간 고위험·혈색소침착증 사례는 중간 엔진과 서비스 규칙 ID 표기가 일부 다르다. 같은 의미인지 규칙 파일과 런타임 계보를 대조한다.
- warfarin·omega-3 근거는 상호작용 가능성과 INR 모니터링 필요성을 설명한다. 모든 경우의 절대 금기로 확대 해석하지 않는다.

권혁찬 약사는 사례별 근거를 읽고 판정과 의견을 직접 입력한다. 10건 모두 끝난 뒤 자격 확인 방법과 서명 이름을 실제 값으로 확인하고 `검토 결과 제출`을 한 번 누른다. 하나라도 `부적절`이면 시스템은 결과를 보존하면서 H-005 완료를 유예한다. 운영 보조자는 판정을 `타당`으로 바꾸지 않는다.

## H-006: 모든 판단이 끝난 뒤 최종 영수증을 발급한다

H-006 전에 다음을 확인한다.

- H-003 대기 초안이 0건이다.
- 승인 초안만 학습·평가 입력에 들어갔다는 계보가 있다.
- H-002 9개 규칙의 실제 승인 또는 수정 의견이 저장됐다.
- H-004 실제 보고서 2~3편의 오너 판단이 저장됐다.
- H-005 10건의 실제 판정, 의견, 자격 확인 방법, 서명이 저장됐다.
- H-007 실제 프로필 5개와 서명된 운영 영수증이 유효하다.

오너의 클릭 순서:

1. 최종 확인 화면에서 각 단계의 완료 근거 경로를 연다.
2. 차단 목록과 외부 검증 공백이 비어 있는지 본다.
3. 오너가 발급자 이름을 직접 확인한다.
4. 오너가 `영수증 서명`을 누른다.
5. 다음 두 경로가 새 세션 입력을 가리키는지 확인한다.
   - `data/original_plan/final_session/final_validation_receipt_v1.json`
   - `data/original_plan/final_session/independent_final_review_receipt_v1.json`
6. 공개키, payload hash, Ed25519 서명 검증 결과를 기록한다.

기존 영수증을 새 세션의 영수증으로 덮어쓰기 전에 세션 ID와 보존 방식을 결정해야 한다. 이 문서는 덮어쓰기를 승인하지 않는다.

## 세션을 종료하고 최종 상태를 확인한다

서버 시작 창을 유지한 상태에서 다음 명령을 실행한다.

```powershell
.\research-server-stop.cmd
```

정상 출력:

```text
로컬 연구 서버에 종료를 요청했습니다.
```

시작 창에는 다음 형식의 경로가 추가로 나와야 한다.

```text
운영 영수증: <실제 JSON 경로>
```

그 다음에만 최종 감사를 실행한다.

```powershell
.\.venv-interim\Scripts\python.exe scripts\run_final_completion_audit.py
```

정상 결과는 `status: "READY"`, `goal_complete: true`, `blockers: []`, 외부 검증 공백 0, 유효한 최종 검증·독립 검토 영수증이다. 2026-07-27 사람 세션 전 현재 입력으로는 120/120 `READY`를 확인했다. 사람 최종 세션은 실행하지 않았으므로 세션 뒤 새 입력·상태·영수증을 대상으로 반드시 다시 실행해야 한다. 결과가 다르면 H-006을 다시 누르지 말고 차단 항목의 근거 경로부터 조사한다.

## 실제 로그에 기록된 오류만 이렇게 대응한다

아래 목록은 추정 오류가 아니다. `etc/local_research_runtime`의 실제 로그와 운영 마법사 기록에 있는 오류만 정리했다.

| 실제 오류 | 기록 위치 | 대응 |
|---|---|---|
| `GET /api/internal/rnd/health 503`가 시작 중 반복됨 | `etc/local_research_runtime/wellnessbox_web.log` | 시작 창의 `로컬 연구 서버가 준비됐습니다.`를 기다린다. 시작 코드는 최대 180초 준비 상태를 확인한다. 준비 문구 없이 입력을 시작하지 않는다. 180초 뒤에도 실패하면 런타임 로그를 보존하고 서버를 다시 시작한다. |
| `/api/tips/pro/plans`, `/api/pharm/tips/ai-drafts` 요청이 `401` | `etc/local_research_runtime/wellnessbox_web.log` | API 주소를 직접 새로고침하지 않는다. `/research-login?redirect=/tips` 또는 `/research-login?redirect=/pharm/tips`를 거쳐 다시 연다. 실제 로그에서 로그인 307 뒤 화면과 API가 200으로 회복됐다. |
| `retrained_model_not_registered`, 추천 POST 500, 서비스 `WB_RND_INTERIM_upstream_500` 502 | `etc/local_research_runtime/rnd_api.log`, `etc/local_research_runtime/wellnessbox_web.log` | 해당 프로필 진행을 멈추고 실패 기록을 보존한다. 등록된 모델과 `src/wellnessbox_rnd/interim/inference.py`의 모델 선택을 조사한다. 실제 수리 명령은 로그에 없으므로 추정 명령을 실행하지 않는다. |
| 후속평가 422, 서비스 `WB_RND_INTERIM_upstream_422` 502, `followup_identity_contract_mismatch_before_fix` | `etc/local_research_runtime/wellnessbox_web.log`, `data/original_plan/final_session/operational_wizard_v1.json`의 `abandoned_attempts` | 실패 시도를 지우지 않는다. 같은 실행 ID·계획 ID·프로필 ID를 임의로 섞지 않는다. 실제 기록에서는 새 복용 전 단계부터 다시 만든 profile-02가 후속 200으로 끝났다. 새로 시작할 때 세 ID의 계보를 다시 확인한다. |
| 오래된 `/api/tips/interim/ai-drafts?status=pending`가 `404` | `etc/local_research_runtime/wellnessbox_web.log` | 오래된 주소를 쓰지 않는다. 최종 확인 화면의 약사 링크로 `/research-login?redirect=/pharm/tips`를 연다. 실제 로그의 `/api/pharm/tips/ai-drafts`는 200으로 응답했다. |
| `WinError 10053`으로 최종 확인 화면 응답이 중단됨 | `etc/local_research_runtime/final_console.log` | 같은 버튼을 바로 다시 누르지 않는다. 화면을 다시 열어 상태 파일과 대상 원장에 저장됐는지 먼저 확인한다. 저장 여부가 불명확하면 증거 경로를 보존하고 구현 담당자가 재현 범위를 확인한다. 실제 로그에는 확정 수리 절차가 없다. |
| 서버는 종료됐지만 `research-server-stop.cmd`가 `Input redirection is not supported`와 종료 코드 1을 반환함 | 2026-07-27 비대화형 사전 점검 | 원인은 `timeout /t 2`의 입력 처리였다. 종료 스크립트는 호환되는 2초 대기 방식으로 수정했다. 같은 오류가 다시 나면 `python scripts\stop_local_research_session.py`를 실행한 뒤 `etc/local_research_runtime/session_processes.json`이 없어졌는지 확인한다. |

## 세션 전에 답이 필요한 항목

1. 기존 `session_state_v1.json`과 영수증을 보존하면서 새 세션을 분리하는 방법은 무엇인가?
2. H-007 전에 사용할 기존 Ed25519 키가 승인된 키인가, 아니면 H-006의 키 준비만 앞당길 것인가?
3. 5개 실제 프로필의 실제 후속평가 자료가 이미 있는가? 없다면 최종 세션 날짜를 후속 관찰 뒤로 옮겨야 한다.
4. 사용자 화면 내부의 실제 필드명과 저장 버튼명은 무엇인가? 연결 저장소 화면 코드와 실제 브라우저에서 확인해야 한다.
5. H-003 승인 초안을 실제 학습 데이터로 연결하고 고정 평가를 1회 실행하는 검증된 명령은 무엇인가?
6. H-005의 선택·의견·자격 정보가 빈 중립 화면은 언제 제공되는가?
7. `hepatic_review_block`, `vitamin_c_above_limit`, 두 응급 사례의 누락된 외부 근거 또는 정확한 입력 사례는 어디에 기록할 것인가?

하나라도 해결되지 않으면 해당 단계는 `확인 필요`로 남긴다. 사람의 판단이나 실제 자료를 추정해 빈칸을 채우지 않는다.

## 최종 완료 판정

다음 항목이 모두 참일 때만 최종 세션 완료로 기록한다.

- 실제 프로필 5개가 서로 다른 나이·목표·복용약을 포함하고, 사람이 전체 화면 경로를 실행했다.
- 실제 후속평가가 같은 프로필·실행·계획 계보에 저장됐다.
- 생성된 실제 AI 초안 전부를 권혁찬 약사가 승인·수정 승인·반려했고 대기 0건이다.
- 승인 초안만 사용한 학습·평가 1회의 입력 계보와 결과가 있다.
- 권혁찬 약사가 H-002 9개 규칙과 H-005 10개 사례를 직접 판단했다.
- 오너가 H-004 보고서 문체와 H-006 영수증을 직접 승인했다.
- H-005 자격 확인 방법과 서명은 실제 값이다.
- 운영 영수증과 최종 두 영수증의 서명·hash가 유효하다.
- 최종 감사가 `READY`, `goal_complete: true`, 빈 차단 목록을 반환한다.

어느 조건도 기존 완료 표시, 자동 저장, 미리 선택된 답, AI 의견, 오너의 약사 대리 판단으로 대신할 수 없다.
