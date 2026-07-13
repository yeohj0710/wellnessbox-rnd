# Cloud GPU 대량 추론 테스트베드

작은 요청 하나를 GPU로 보내면 오히려 느릴 수 있어요. 데이터를 복사하고 GPU를 깨우는 시간이 실제
계산보다 길기 때문이에요. 이 테스트베드는 같은 입력을 큰 배치로 묶었을 때 CPU와 GPU가 각각 얼마나
처리하는지 재현 가능한 숫자로 확인해요.

## 무엇을 측정하나요?

대상은 기존 `effect_model_v3`예요. JSON으로 저장된 다중 출력 ridge 계수를 PyTorch의 단일
`Linear` 계층으로 옮긴 뒤, 같은 합성 데이터와 같은 float32 입력을 CPU와 CUDA에서 반복 추론해요.
측정 구간 앞에는 warmup을 두고, CUDA 측정 전후에는 `torch.cuda.synchronize()`를 호출해 비동기
실행 시간이 빠지는 일을 막아요.

새 모델은 학습하지 않아요. 현재 프로젝트의 strict training-readiness gate는 `NO-GO`이므로 기존
replay-only held artifact만 변환해요. 결과 모델도 런타임으로 승격하지 않고, deterministic safety와
추천 경로는 바꾸지 않아요.

## 한 번 실행하면 무엇이 남나요?

출력 폴더에는 6개 파일이 생겨요.

- `metrics.json`: 환경, 입력·모델 SHA-256, 처리량, 실행 시간, CUDA 배속, 수치 동등성
- `model_torchscript.pt`: 기존 JSON 계수를 옮긴 portable float32 추론 모델
- `predictions_sample.jsonl`: 최대 16개 입력의 예측 샘플
- `events.jsonl`: 시작, 데이터 로드, 장치별 완료, 종료 이벤트
- `run.log`: 사람이 빠르게 읽을 수 있는 핵심 로그
- `manifest.json`: 앞선 5개 파일의 크기와 SHA-256

`manifest.json` 검증이 실패하면 실행도 실패해요. CPU와 GPU의 최대 절대 오차가 `1e-4`를 넘을
때도 실패해요.

## 설치와 테스트

Python 3.11 이상 환경에서 실행해요.

```powershell
cd C:\dev\wellnessbox-rnd
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest tests/test_gpu_inference_testbed.py -q
python -m ruff check src/wellnessbox_rnd/gpu_testbed scripts/run_gpu_inference_testbed.py tests/test_gpu_inference_testbed.py
```

`requirements.txt`는 PyTorch `2.6.0+cu124` wheel 인덱스를 함께 지정해요. Cloud NVIDIA 이미지의
CUDA 12.4 드라이버와 맞추기 위한 고정값이에요. 최신 PyPI wheel을 무조건 받으면 CUDA 13 wheel이
선택되어 GPU 초기화가 실패할 수 있어요.

## 로컬에서 CPU와 CUDA 비교하기

먼저 작게 확인해요.

```powershell
python scripts/run_gpu_inference_testbed.py `
  --devices cpu,cuda `
  --require-cuda `
  --batch-size 65536 `
  --iterations 5 `
  --warmup 2 `
  --output artifacts/gpu_testbed/local_smoke
```

실제 대량 추론 프로파일은 기본값인 `batch_size=262144`, `iterations=40`을 써요. 총 처리 행 수는
장치마다 `10,485,760`개예요. 원본 480개 trajectory record를 순서대로 반복해 같은 배치를
만들고, 96명 user case의 특징 분포는 그대로 유지해요.

## Cloud GPU Runner로 실행하기

유료 실행 전에는 항상 공급자와 실행시간을 고정해 상태를 확인해요. NAVER 크레딧이 2026년 7월
31일 먼저 만료되므로 NAVER를 우선해요.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File C:\dev\cloud-gpu-runner\scripts\cloud-gpu.ps1 `
  status -Provider naver -Minutes 60
```

2026년 7월 13일 사전 계산값은 최대 `1,459.61원 + VAT`예요. GPU `1,447.01원`, 50GB 임시
디스크 `7.00원`, 공인 IP `5.60원`을 합친 값이에요. 실행 전 NAVER 잔액은 `5,300,000원`이었어요.

업로드는 `etc/cloud-gpu-project/`에 만든 최소 staging bundle을 써요. 전체 로컬 `artifacts/`와
`tmp/`를 보내지 않기 위한 경계예요. 입력은 프로젝트 내부 비민감 합성 데이터만 별도 전달해요.

```powershell
$command = 'apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y software-properties-common && add-apt-repository -y ppa:deadsnakes/ppa && apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y python3.11 python3.11-venv && python3.11 -m venv /opt/cgr-venv && /opt/cgr-venv/bin/pip install --upgrade pip && /opt/cgr-venv/bin/pip install -r requirements.txt && /opt/cgr-venv/bin/python scripts/run_gpu_inference_testbed.py --data "$CGR_DATA_FILE" --artifact artifacts/models/effect_model_v3.json --output "$CGR_OUTPUT_DIR" --devices cpu,cuda --require-cuda --batch-size 262144 --iterations 40 --warmup 3 --provider kakao --estimated-max-cost-krw 666.31'

powershell -NoProfile -ExecutionPolicy Bypass `
  -File C:\dev\cloud-gpu-runner\scripts\cloud-gpu.ps1 `
  run -Provider kakao -Minutes 60 `
  -ProjectPath C:\dev\wellnessbox-rnd\etc\cloud-gpu-project `
  -DataPath C:\dev\wellnessbox-rnd\data\synthetic\synthetic_longitudinal_v4.jsonl `
  -Command $command `
  -ApproveEstimatedCost
```

Runner는 실행시간을 60분으로 제한하고, 성공·실패·timeout 모두 종료 경로에서 서버 종료와 출력
업로드를 수행해요. 작업이 끝난 뒤에는 job terminal state뿐 아니라 GPU 서버, 공인 IP, 임시 디스크가
남지 않았는지 각각 확인해야 해요. 다시 `status`를 실행해 실제 사용액과 남은 잔액도 기록해요.

## 숫자를 읽을 때 주의할 점

`rows_per_second`는 입력이 해당 장치 메모리에 올라간 뒤의 compute-only 처리량이에요.
`transfer_seconds`는 모델과 한 배치를 옮기는 시간을 따로 보여줘요. 그래서 CUDA 배속이 크더라도
작은 실시간 요청까지 GPU로 옮겨야 한다는 뜻은 아니에요. 큰 offline replay, frozen-eval 대량 추론,
연구용 sweep처럼 배치가 충분히 클 때 쓰는 경로예요.

CPU와 GPU가 완전히 같은 하드웨어 조건은 아니에요. 이 비교는 해당 Cloud 인스턴스 안에서 같은 모델,
같은 배치, 같은 반복 횟수를 사용한 compute-only 장치 비교예요. 전송 시간은 별도 항목이에요. 다른
공급자나 GPU flavor를 비교할 때는 `metrics.json`의 환경과 설정을 함께 봐야 해요.

Reference basis: tossfeed-easy-finance (LTV·DTI·DSR explainer)

## 2026년 7월 13일 실제 실행 결과

NAVER를 먼저 선택했지만 인스턴스를 만들기 전에 `ncp_gpu_network_configuration_missing`으로 중단됐어요.
과금과 자원 생성은 없었어요. 승인된 자동 선택 범위에 따라 Kakao `gn1i.xlarge`로 전환했어요.

Kakao에서는 환경 문제를 세 번 고친 뒤 성공했어요.

- 기본 이미지에 `pip`가 없음 → Python 3.11 가상환경 설치
- 기본 Python 3.10이 프로젝트 요구사항보다 낮음 → Python 3.11 설치
- 최신 PyPI wheel이 CUDA 13을 요구함 → `torch==2.6.0`, CUDA 12.4 wheel로 고정

성공 job은 `abe1d1b1-4e77-47a4-a4fe-9d1fcc96f1ef`예요. Tesla T4 한 대에서 같은 모델과
`10,485,760`개 입력을 장치별로 처리했어요.

| 항목 | CPU | Tesla T4 |
|---|---:|---:|
| compute-only 시간 | 0.315232초 | 0.030180초 |
| 처리량 | 33,263,664 rows/s | 347,441,184 rows/s |
| GPU 배속 | - | 10.445배 |

CPU와 GPU의 최대 절대 오차는 `0.0`이었어요. 최초 전송 시간은 `0.323738초`라서 작은 단건 요청보다
대량 추론에 적합해요.

실패 재시도를 포함한 GPU 시간은 `746.077초`(12분 26.077초), GPU job 비용은 `138.086418원`이에요.
Object Storage 비용 `0.0854원`을 더한 이번 작업 총액은 `138.171818원`(VAT 별도)이에요.
종료 뒤 NAVER 잔액은 `5,299,999.835918원`, Kakao 잔액은 `9,999,498.635506원`이에요.

마지막 status에서 GPU 인스턴스와 공인 IP는 모두 0개였어요. Kakao 임시 디스크는 인스턴스 소유라서
인스턴스 삭제 시 함께 반납됐어요. 세부 실행별 시간·비용·잔액과 삭제 시각은
`artifacts/gpu_testbed/cloud_kakao/cost.json`에 있어요.
