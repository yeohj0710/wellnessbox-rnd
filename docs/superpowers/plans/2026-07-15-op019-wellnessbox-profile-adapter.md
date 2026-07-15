# OP-019 WellnessBox Profile Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the persisted `wellnessbox` `types/chat.UserProfile` contract into a valid R&D recommendation request without silently discarding any source property.

**Architecture:** `wellnessbox` owns a strict runtime adapter and the existing preview route invokes it before calling `/v1/recommend`. The request retains the exact source profile in a versioned `source_profile` envelope while operational fields are mapped into the existing R&D schema; unsupported keys, missing required fields, and unknown goals fail explicitly. Both repositories carry the same versioned contract fixture, and the R&D evidence workflow checks both tracked repositories.

**Tech Stack:** TypeScript, Zod 4, Next.js route handlers, Python 3.11, Pydantic 2, FastAPI TestClient, GitHub Actions

---

### Task 1: Freeze the two-repository contract

**Files:**
- Create: `data/contracts/wellnessbox_profile_adapter_v1.json`
- Create: `C:/dev/wellnessbox/contracts/wb-rnd/profile-adapter-v1.json`
- Create: `tests/test_wellnessbox_profile_adapter_contract.py`

- [x] **Step 1: Add one representative contract case containing every `UserProfile` property**

The fixture must contain `contract_version`, `source_profile`, `adapter_options`, and `expected_request`. The expected request must preserve the complete source object under `source_profile.profile`, map age/sex/height/weight, conditions, medication names, allergies, supported goals, dietary restrictions, and the conservative pregnancy-or-breastfeeding safety flag, and set explicit survey consent.

- [x] **Step 2: Add failing R&D contract tests**

```python
def test_wellnessbox_and_rnd_contract_snapshots_are_identical() -> None:
    assert SERVICE_FIXTURE_PATH.read_bytes() == RND_FIXTURE_PATH.read_bytes()


def test_adapter_contract_is_accepted_by_real_recommendation_endpoint() -> None:
    contract = json.loads(RND_FIXTURE_PATH.read_text(encoding="utf-8"))
    request = RecommendationRequest.model_validate(contract["expected_request"])
    assert request.source_profile.profile.model_dump(exclude_none=True) == contract["source_profile"]
    assert client.post("/v1/recommend", json=contract["expected_request"]).status_code == 200
```

- [x] **Step 3: Run the new test and verify the schema failure**

Run: `python -m pytest -o addopts="" -q tests/test_wellnessbox_profile_adapter_contract.py`

Expected: FAIL because `RecommendationRequest` does not yet accept `source_profile`.

### Task 2: Accept a strict, versioned source-profile trace in R&D

**Files:**
- Modify: `src/wellnessbox_rnd/schemas/recommendation.py`
- Test: `tests/test_wellnessbox_profile_adapter_contract.py`

- [x] **Step 1: Define the strict source contract**

```python
class WellnessBoxChatUserProfileV1(_StrictRequestInput):
    name: str | None = None
    age: int | None = Field(default=None, ge=18, le=120)
    sex: Literal["male", "female", "other"] | None = None
    heightCm: float | None = Field(default=None, gt=0, le=300)
    weightKg: float | None = Field(default=None, gt=0, le=500)
    conditions: list[str] | None = None
    medications: list[str] | None = None
    allergies: list[str] | None = None
    goals: list[str] | None = None
    dietaryRestrictions: list[str] | None = None
    pregnantOrBreastfeeding: bool | None = None
    caffeineSensitivity: bool | None = None


class SourceProfileInput(_StrictRequestInput):
    schema_version: Literal["wellnessbox.chat.UserProfile.v1"]
    profile: WellnessBoxChatUserProfileV1
```

- [x] **Step 2: Add `source_profile` to `RecommendationRequest`**

Use `Field(default=None, exclude=True)` so source trace metadata is available for integration and later persistence without changing the established normalized clinical input hash or legacy model dumps.

- [x] **Step 3: Run the R&D contract and existing input tests**

Run: `python -m pytest -o addopts="" -q tests/test_wellnessbox_profile_adapter_contract.py tests/test_unsupported_input_contracts.py tests/test_consent_and_input_hash_contracts.py tests/test_inference_api.py`

Expected: PASS.

### Task 3: Implement and route the strict WellnessBox adapter

**Files:**
- Create: `C:/dev/wellnessbox/lib/server/wb-rnd-profile-adapter.ts`
- Modify: `C:/dev/wellnessbox/lib/server/wb-rnd-client.ts`
- Modify: `C:/dev/wellnessbox/lib/server/wb-rnd-recommend-preview-route.ts`
- Create: `C:/dev/wellnessbox/scripts/qa/check-rnd-profile-adapter.cts`
- Modify: `C:/dev/wellnessbox/package.json`
- Modify: `C:/dev/wellnessbox/.github/workflows/encoding-guard.yml`

- [x] **Step 1: Add failing adapter checks**

The QA script must compare the adapter output with the checked-in contract, forward that exact request through the existing client with a fake fetch, and assert explicit errors for an unknown source property, missing age/sex/goals, disabled survey consent, and an unsupported goal.

- [x] **Step 2: Run QA and verify the missing adapter failure**

Run: `npm run qa:rnd:profile-adapter`

Expected: FAIL because `mapWellnessBoxProfileToWbRndRequest` does not exist.

- [x] **Step 3: Implement strict parsing and goal mapping**

Use `z.object(...).strict()` for the runtime `UserProfile` boundary. Normalize goal aliases with Unicode NFKC, lowercase, and collapsed separators. Preserve the parsed source profile exactly in `source_profile.profile`; reject unknown keys and unsupported goals instead of dropping them.

- [x] **Step 4: Map the operational request**

Require age, sex, at least one supported goal, and explicit `surveyConsent.useForRecommendation === true`. Map height and weight, conditions, medications, allergies, dietary restrictions, and `pregnantOrBreastfeeding` into the current R&D fields. Use explicit false consent for NHIS, wearable, CGM, and genetic inputs.

- [x] **Step 5: Connect the existing preview route**

When POST body contains `profile`, call the adapter with `requestId` and `surveyConsent`; retain the existing raw `payload` preview path. Return status 422 and structured adapter issues for invalid source input.

- [x] **Step 6: Run adapter QA, TypeScript, encoding, lint, and build**

Run:

```text
npm run qa:rnd:profile-adapter
npm run qa:rnd:preview-route
npx tsc --noEmit
npm run audit:encoding
npm run lint
npm run build
```

Expected: all commands PASS.

### Task 4: Register cross-repository evidence

**Files:**
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `docs/plans/2026-07-15-original-plan-completion-program.md`
- Modify: `.github/workflows/original-plan-evidence.yml`
- Modify: `scripts/audit_original_plan_requirements.py`
- Modify: `scripts/build_original_plan_completion_report.py`
- Modify: `tests/test_original_plan_audit.py`
- Modify: `tests/test_original_plan_audit_cli.py`
- Modify: `tests/test_original_plan_completion_report.py`
- Modify: `tests/test_original_plan_manifest.py`

- [x] **Step 1: Claim OP-019 only at `INTEGRATED`**

Register both repositories' adapter, schema, tests, route, and identical contract snapshots. Do not claim deployed or operated evidence.

- [x] **Step 2: Make CI audit the tracked service repository**

Checkout public `yeohj0710/wellnessbox` into `_evidence/wellnessbox`, expose its root with `WELLNESSBOX_EVIDENCE_ROOT`, and resolve that environment variable in the audit and completion-report CLIs.

- [x] **Step 3: Regenerate and validate completion evidence**

Run:

```text
python scripts/audit_original_plan_requirements.py --wellnessbox-root C:/dev/wellnessbox
python scripts/build_original_plan_completion_report.py --wellnessbox-root C:/dev/wellnessbox
python scripts/build_original_plan_completion_report.py --wellnessbox-root C:/dev/wellnessbox --check
```

Expected: audit PASS; complete 22, pending 97, external 1.

### Task 5: Verify, document, review, and publish

**Files:**
- Modify: `PROGRESS.md`
- Modify: `NEXT_STEPS.md`
- Modify: `SESSION_HANDOFF.md`

- [x] **Step 1: Run focused and core R&D regression tests**

Run the original-plan workflow test selection, recommendation/safety core tests, Ruff, `git diff --check`, full pytest baseline, and the 256-case frozen evaluation. Expected frozen-eval metric deltas: all zero.

- [x] **Step 2: Update the three required handoff files**

Record that OP-019 is integrated in source and contract tests, but the R&D process is still not deployed and the two production processes still do not run together.

- [x] **Step 3: Obtain an independent code review**

Review both repositories' exact diffs for field loss, unsafe consent defaults, schema drift, route bypasses, and unrelated user-owned changes. Resolve all Critical and Important findings.

- [x] **Step 4: Commit and push exact related files**

Commit `wellnessbox` first so the R&D evidence workflow can checkout the referenced service files. Then commit and push `wellnessbox-rnd`, excluding `docs/plans/2026-07-14-tips-evaluator-ui-overhaul.md`.

- [x] **Step 5: Verify both remote branches and CI runs**

Expected: local `HEAD` equals each `origin/main`; WellnessBox encoding/adapter CI and R&D Original plan evidence CI both conclude `success`.
