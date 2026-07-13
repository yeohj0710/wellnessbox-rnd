# Cloud GPU Inference Testbed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify a reusable CPU/CUDA bulk-inference testbed for the existing replay-only `effect_model_v3` artifact, including reproducible outputs, Cloud GPU execution, cost evidence, and cleanup proof.

**Architecture:** Convert the existing multi-output ridge artifact into an equivalent PyTorch `Linear` module and vectorize the frozen synthetic v4 records with the canonical project vectorizer. Run identical tiled batches on CPU and CUDA, verify numerical agreement, write model/metrics/log/sample/manifest artifacts, and keep the learned model outside runtime promotion. Use a minimal staging copy under `etc/` for Cloud GPU upload so ignored local artifacts and unrelated project files are not transferred.

**Tech Stack:** Python 3.11+, PyTorch 2.x, NumPy, Pydantic, pytest, Ruff, Cloud GPU Runner PowerShell wrapper.

---

### Task 1: Freeze testbed behavior with CPU-only tests

**Files:**
- Create: `tests/test_gpu_inference_testbed.py`

- [ ] **Step 1: Add artifact-conversion equivalence test**

```python
def test_torch_model_matches_canonical_predictor() -> None:
    artifact, records = load_fixture_inputs()
    model, features = build_torch_effect_model(artifact, records[:3])
    actual = model(features).detach().numpy()
    expected = canonical_prediction_matrix(artifact, records[:3])
    np.testing.assert_allclose(actual, expected, rtol=1e-5, atol=1e-5)
```

- [ ] **Step 2: Add CPU benchmark accounting test**

```python
def test_cpu_benchmark_counts_all_rows() -> None:
    result = benchmark_inference(model, features, device="cpu", iterations=3, warmup=1)
    assert result.processed_rows == features.shape[0] * 3
    assert result.rows_per_second > 0
```

- [ ] **Step 3: Add output contract test**

```python
def test_run_writes_reproducible_output_contract(tmp_path: Path) -> None:
    result = run_testbed(config_for(tmp_path, devices=("cpu",)))
    assert result.metrics_path.name == "metrics.json"
    assert (tmp_path / "model_torchscript.pt").is_file()
    assert verify_manifest(tmp_path / "manifest.json") == []
```

- [ ] **Step 4: Run tests and confirm pre-implementation failure**

Run: `python -m pytest tests/test_gpu_inference_testbed.py -q`

Expected: collection fails because `wellnessbox_rnd.gpu_testbed` does not exist.

### Task 2: Implement reusable inference engine and artifact contract

**Files:**
- Create: `src/wellnessbox_rnd/gpu_testbed/__init__.py`
- Create: `src/wellnessbox_rnd/gpu_testbed/pipeline.py`
- Test: `tests/test_gpu_inference_testbed.py`

- [ ] **Step 1: Define validated configuration and result models**

```python
@dataclass(frozen=True)
class InferenceBenchmarkConfig:
    dataset_path: Path
    artifact_path: Path
    output_dir: Path
    devices: tuple[str, ...] = ("cpu", "cuda")
    batch_size: int = 262_144
    iterations: int = 40
    warmup: int = 3
    require_cuda: bool = True
    seed: int = 20260713
```

- [ ] **Step 2: Reuse canonical feature extraction and build equivalent Torch module**

```python
rows = [build_effect_feature_dict_v1(record) for record in records]
matrix = EffectFeatureVectorizerV1(artifact.feature_names).transform(rows)
layer = torch.nn.Linear(len(artifact.feature_names), len(artifact.output_names))
layer.weight.copy_(torch.tensor(artifact.weights, dtype=torch.float32))
layer.bias.copy_(torch.tensor(artifact.intercepts, dtype=torch.float32))
```

- [ ] **Step 3: Benchmark identical batches with explicit synchronization**

```python
with torch.inference_mode():
    for _ in range(warmup):
        output = model(features)
    synchronize(device)
    started = perf_counter()
    for _ in range(iterations):
        output = model(features)
    synchronize(device)
    elapsed = perf_counter() - started
```

- [ ] **Step 4: Enforce CPU/CUDA numerical equivalence**

Compute sample outputs on both devices and fail when maximum absolute difference exceeds `1e-4`. This proves the measured CUDA path preserves the existing artifact calculation within float32 tolerance.

- [ ] **Step 5: Write required artifacts atomically**

Write:

- `metrics.json`: config, environment, timing, throughput, speedup, correctness, input/model hashes.
- `model_torchscript.pt`: portable inference model converted from the existing JSON artifact.
- `predictions_sample.jsonl`: bounded record IDs and output values.
- `events.jsonl`: structured lifecycle events.
- `run.log`: concise human-readable run log.
- `manifest.json`: byte size and SHA-256 for every output except itself.

- [ ] **Step 6: Run focused tests**

Run: `python -m pytest tests/test_gpu_inference_testbed.py -q`

Expected: all focused tests pass on CPU; CUDA tests skip when unavailable.

### Task 3: Add CLI and install contract

**Files:**
- Create: `scripts/run_gpu_inference_testbed.py`
- Create: `requirements.txt`
- Modify: `pyproject.toml`

- [ ] **Step 1: Add GPU optional dependency**

```toml
gpu = [
  "torch==2.6.0",
]
```

- [ ] **Step 2: Add root requirements entrypoint**

```text
--extra-index-url https://download.pytorch.org/whl/cu124
-e .[dev,interim,gpu]
```

- [ ] **Step 3: Implement explicit CLI**

Support `--dataset`, `--artifact`, `--output`, `--devices`, `--batch-size`, `--iterations`, `--warmup`, `--require-cuda`, `--provider`, and `--estimated-max-cost-krw`. Exit nonzero if CUDA is required but unavailable or output verification fails.

- [ ] **Step 4: Run local CPU smoke**

Run: `python scripts/run_gpu_inference_testbed.py --devices cpu --batch-size 4096 --iterations 2 --warmup 1 --output artifacts/gpu_testbed/local_cpu_smoke`

Expected: exit 0 and six verified output files.

### Task 4: Document reproducible local and Cloud execution

**Files:**
- Create: `docs/cloud_gpu_inference_testbed.md`
- Modify: `README.md`

- [ ] **Step 1: Document model boundary**

State that the testbed benchmarks the existing held/replay-only `effect_model_v3`, does not retrain it, does not change deterministic safety, and does not promote learned output into runtime.

- [ ] **Step 2: Document commands and outputs**

Include install, focused test, CPU smoke, local CUDA smoke, Cloud GPU status/run, result verification, and cleanup checks with exact Windows PowerShell commands.

- [ ] **Step 3: Document performance interpretation**

Explain compute-only throughput, host-to-device transfer timing, warmup, synchronization, same-batch comparison, and why small interactive requests should remain on CPU.

### Task 5: Validate locally before paid execution

**Files:**
- Modify only when tests expose a root cause.

- [ ] **Step 1: Run formatting and focused checks**

Run:

```powershell
python -m ruff check src/wellnessbox_rnd/gpu_testbed scripts/run_gpu_inference_testbed.py tests/test_gpu_inference_testbed.py
python -m pytest tests/test_gpu_inference_testbed.py -q
```

Expected: zero Ruff errors and all focused tests pass.

- [ ] **Step 2: Run local CPU/CUDA comparison**

Run with `--devices cpu,cuda --require-cuda`, reduced batch/iterations, then verify `max_abs_diff <= 1e-4` and positive speedup/throughput metrics.

- [ ] **Step 3: Run broader guardrails**

Run `python -m ruff check .` and `python -m pytest`. Record pre-existing failures separately; fix only regressions caused by this loop.

### Task 6: Execute bounded NAVER Cloud GPU job

**Files:**
- Create temporarily: `etc/cloud-gpu-project/`
- Produce locally after retrieval: `artifacts/gpu_testbed/cloud_naver/`

- [ ] **Step 1: Record pre-run estimate**

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\dev\cloud-gpu-runner\scripts\cloud-gpu.ps1 status -Provider naver -Minutes 60
```

Expected bound: `1,459.61 KRW + VAT`, below approved `20,000 KRW + VAT`; NAVER selected because its credit expires first.

- [ ] **Step 2: Build minimal staging bundle**

Copy only `pyproject.toml`, `requirements.txt`, `src/`, `scripts/run_gpu_inference_testbed.py`, and `artifacts/models/effect_model_v3.json` into `etc/cloud-gpu-project/`. Use the original internal synthetic dataset as `-DataPath`.

- [ ] **Step 3: Submit one approved 60-minute maximum job**

Run `cloud-gpu.ps1 run -Provider naver -Minutes 60 -ApproveEstimatedCost` with command:

```bash
pip install -r requirements.txt && python scripts/run_gpu_inference_testbed.py --data "$CGR_DATA_FILE" --artifact artifacts/models/effect_model_v3.json --output "$CGR_OUTPUT_DIR" --devices cpu,cuda --require-cuda --batch-size 262144 --iterations 40 --warmup 3 --provider naver --estimated-max-cost-krw 1459.61
```

- [ ] **Step 4: Poll job state and retrieve output**

Wait on actual state transitions, not fixed sleeps. Download output package, verify manifest, and place final usable results under `artifacts/gpu_testbed/cloud_naver/`.

- [ ] **Step 5: Record actual time, cost, and balance**

Capture job timestamps/elapsed runtime/provider cost from Runner usage and write `cost.json` beside metrics.

### Task 7: Verify cleanup and update canonical handoff

**Files:**
- Modify: `PROGRESS.md`
- Modify: `NEXT_STEPS.md`
- Modify: `SESSION_HANDOFF.md`
- Modify: `docs/cloud_gpu_inference_testbed.md`

- [ ] **Step 1: Prove resource cleanup**

Confirm job terminal state and absence of its GPU server, public IP, and temporary volume. Run post-job NAVER status and record remaining credit. If any paid resource remains, terminate it before continuing.

- [ ] **Step 2: Update project truth documents**

Record chosen P3/P4 infrastructure loop, primary dataset path and case count, no-training boundary, performance, cost, output paths, validation, unchanged frozen metrics, five bottlenecks, and next three loops.

- [ ] **Step 3: Remove Codex-created staging clutter**

Delete only `etc/cloud-gpu-project/` after outputs are safely retrieved and verified. Preserve all pre-existing ignored artifacts.

### Task 8: Final verification, commit, and push

**Files:**
- All files changed in Tasks 1-7.

- [ ] **Step 1: Apply verification-before-completion checklist**

Rerun focused tests, Ruff, output manifest verification, `git diff --check`, secret-pattern scan, and Git status. Inspect the exact diff and ensure no credential or unrelated user artifact is staged.

- [ ] **Step 2: Commit intentionally**

```powershell
git add requirements.txt pyproject.toml README.md PROGRESS.md NEXT_STEPS.md SESSION_HANDOFF.md docs/cloud_gpu_inference_testbed.md docs/superpowers/plans/2026-07-13-cloud-gpu-inference-testbed.md scripts/run_gpu_inference_testbed.py src/wellnessbox_rnd/gpu_testbed tests/test_gpu_inference_testbed.py
git commit -m "feat: add cloud GPU inference testbed"
```

- [ ] **Step 3: Push current branch**

Run: `git push origin main`

Expected: new commit plus the three pre-existing local commits reach `origin/main`; working tree remains clean.
