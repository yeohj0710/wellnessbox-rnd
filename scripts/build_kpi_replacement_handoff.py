"""Build new KPI cases and the next blinded-response handoff package."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wellnessbox_rnd.evals.adaptive_answer_key_review import (  # noqa: E402
    build_external_ai_request,
)
from wellnessbox_rnd.evals.answer_key_integrity import (  # noqa: E402
    load_registry as load_engine_registry,
)
from wellnessbox_rnd.evals.answer_key_workbench import (  # noqa: E402
    CaseDraft,
    Workbench,
    load_workbench,
)
from wellnessbox_rnd.evals.blinded_drafters import (  # noqa: E402
    SPECIAL_POPULATION_AREAS,
)
from wellnessbox_rnd.evals.reference_corpus_drafters import (  # noqa: E402
    DRAFT_SOURCE,
    load_extract,
)
from wellnessbox_rnd.governance.reviewer_credentials import (  # noqa: E402
    load_registry as load_identity_registry,
)
from wellnessbox_rnd.governance.reviewer_credentials import (  # noqa: E402
    reviewer_identity_reference,
)

OUTPUT_DIR = ROOT / "data/original_plan/kpi/review_handoff/replacement_round"
PACKAGE_PATH = OUTPUT_DIR / "kpi_replacement_input_package.zip"
REPLACEMENT_REPORT = (
    ROOT
    / "data/original_plan/kpi/review_handoff/completed_review"
    / "kpi_replacement_required_v1.json"
)
WORKBENCH_DIR = ROOT / "data/original_plan/kpi/workbench"
COUNTS = {"KPI-1": 49, "KPI-4": 7, "KPI-5": 9}
REQUEST_NAMES = {
    "KPI-1": "kpi1_anthropic_review_request.json",
    "KPI-4": "kpi4_anthropic_primary_request.json",
    "KPI-5": "kpi5_anthropic_review_request.json",
}
RESPONSE_NAMES = {
    "KPI-1": "kpi1_response.json",
    "KPI-4": "kpi4_response.json",
    "KPI-5": "kpi5_response.json",
}
KPI1_PATTERN = re.compile(
    r"^영역 (?P<area>.+?) / 판정 「(?P<target>.+?)」 / 나이"
)
KPI4_PATTERN = re.compile(r"「(?P<area>[^」]+)」에서 「(?P<target>[^」]+)」")


def _slug(indicator_id: str) -> str:
    return indicator_id.lower().replace("-", "")


def _workbench(indicator_id: str) -> Workbench:
    return load_workbench(
        WORKBENCH_DIR / f"{_slug(indicator_id)}_workbench_v1.json"
    )


def _engine_logic_paths() -> list[str]:
    registry = load_engine_registry(ROOT)
    return sorted(
        entry["path"]
        for entry in registry["entries"]
        if entry.get("role") == "engine_logic"
    )


def _answer_vocabulary(workbench: Workbench) -> list[str]:
    return sorted(
        {
            token
            for draft in workbench.drafts
            for token in draft.draft_answer
            if token.strip()
        }
    )


def _accepted_keys(
    workbench: Workbench, pattern: re.Pattern[str]
) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for draft in workbench.drafts:
        decision = workbench.decisions.get(draft.case_id)
        if decision is None or decision.action == "rejected":
            continue
        match = pattern.search(draft.prompt)
        if match:
            keys.add((match.group("area"), match.group("target")))
    return keys


def _context_answer(
    base: list[str], context: dict[str, Any] | None
) -> tuple[list[str], list[str]]:
    if context is None:
        return sorted(set(base)), []
    answer = set(base)
    notes: list[str] = []
    for item in context["affected_ingredients"]:
        answer.add(item["rnd_ingredient_key"])
        notes.append(
            f"{item['rnd_ingredient_key']}: {item['counseling']} "
            f"(p{item['source']['page']})"
        )
    return sorted(answer), notes


def build_kpi1_replacements(
    workbench: Workbench, extract: dict[str, Any], blinded: list[str]
) -> list[CaseDraft]:
    accepted = _accepted_keys(workbench, KPI1_PATTERN)
    existing_prompts = {draft.prompt for draft in workbench.drafts}
    bases = [
        item
        for item in extract["recommendation_cases"]
        if (item["area_title"], item["target"]) in accepted
        and item.get("mapped_ingredients")
    ]
    contexts: list[dict[str, Any] | None] = [
        None,
        *extract["medication_contexts"],
    ]
    drafted: list[CaseDraft] = []
    adult_ages = (31, 37, 44, 50, 56, 62, 68, 74)
    child_ages = (8, 10, 12, 14, 16)
    pregnancy_ages = (27, 30, 33, 36, 39)

    for base_index, base in enumerate(bases):
        is_special = base["area_id"] in SPECIAL_POPULATION_AREAS
        if base["area_id"] == "43-children":
            ages = child_ages
        elif base["area_id"] == "38-pregnancy-lactation":
            ages = pregnancy_ages
        else:
            ages = adult_ages
        allowed_contexts = [None] if is_special else contexts
        ordered_contexts = [
            allowed_contexts[(base_index + offset + 3) % len(allowed_contexts)]
            for offset in range(len(allowed_contexts))
        ]
        for variant, context in enumerate(ordered_contexts):
            age = ages[(base_index + variant) % len(ages)]
            medication = context["drug"] if context else "없음"
            prompt = (
                f"영역 {base['area_title']} / 판정 「{base['target']}」 / "
                f"나이 {age} / 복용약 {medication}"
            )
            if prompt in existing_prompts:
                continue
            answer, context_notes = _context_answer(
                base["mapped_ingredients"], context
            )
            rationale = [
                f"{base['area_title']} · 원문 판정 「{base['target']}」 "
                f"({base['source']['file']} p{base['source']['page']})",
                *context_notes,
            ]
            drafted.append(
                CaseDraft(
                    case_id=f"kpi1-repl-{len(drafted) + 1:03}",
                    prompt=prompt,
                    draft_answer=answer,
                    draft_source=DRAFT_SOURCE,
                    draft_rationale=" · ".join(rationale),
                    drafting_agent="codex",
                    blinded_from=list(blinded),
                )
            )
            existing_prompts.add(prompt)
            break
        if len(drafted) == COUNTS["KPI-1"]:
            return drafted
    raise ValueError(f"kpi1_replacement_pool_too_small:{len(drafted)}")


def build_kpi4_replacements(
    workbench: Workbench, extract: dict[str, Any], blinded: list[str]
) -> list[CaseDraft]:
    accepted = _accepted_keys(workbench, KPI4_PATTERN)
    existing_prompts = {draft.prompt for draft in workbench.drafts}
    bases = [
        item
        for item in extract["recommendation_cases"]
        if (item["area_title"], item["target"]) in accepted
        and item.get("mapped_ingredients")
        and item["area_id"] not in SPECIAL_POPULATION_AREAS
    ]
    contexts = extract["medication_contexts"]
    drafted: list[CaseDraft] = []
    for index, base in enumerate(bases):
        context = contexts[(index + 2) % len(contexts)]
        prompt = (
            f"{context['drug']} 복용 중입니다. 「{base['area_title']}」에서 "
            f"「{base['target']}」이 목표인데, 함께 확인할 성분과 복용상 주의점은 "
            "무엇인가요?"
        )
        if prompt in existing_prompts:
            continue
        drafted.append(
            CaseDraft(
                case_id=f"kpi4-repl-{len(drafted) + 1:03}",
                prompt=prompt,
                draft_answer=[],
                draft_source="blind_primary_ai_response_v1@adaptive_answer_key_review",
                draft_rationale=(
                    f"질문 상황 출처: {base['source']['file']} "
                    f"p{base['source']['page']}"
                ),
                drafting_agent="",
                blinded_from=list(blinded),
            )
        )
        existing_prompts.add(prompt)
        if len(drafted) == COUNTS["KPI-4"]:
            return drafted
    raise ValueError(f"kpi4_replacement_pool_too_small:{len(drafted)}")


def build_kpi5_replacements(
    workbench: Workbench, extract: dict[str, Any], blinded: list[str]
) -> list[CaseDraft]:
    rejected_prompts = {
        draft.prompt
        for draft in workbench.drafts
        if workbench.decisions.get(draft.case_id)
        and workbench.decisions[draft.case_id].action == "rejected"
    }
    rules = [
        {"drug": context["drug"], **item}
        for context in extract["medication_contexts"]
        for item in context["affected_ingredients"]
    ]
    safe_rules = [
        rule
        for rule in rules
        if not any(
            rule["drug"] in prompt
            and rule["rnd_ingredient_key"] in prompt
            for prompt in rejected_prompts
        )
    ]
    drafted: list[CaseDraft] = []
    for rule in safe_rules:
        answer = sorted(
            {
                rule["kind"],
                rule["rnd_ingredient_key"],
                f"p{rule['source']['page']}",
                rule["book_nutrient"],
            }
        )
        drafted.append(
            CaseDraft(
                case_id=f"kpi5-repl-{len(drafted) + 1:03}",
                prompt=(
                    f"{rule['drug']} 복용자 상담에서 {rule['rnd_ingredient_key']} "
                    "관계의 라벨과 원문 근거를 함께 제시하면?"
                ),
                draft_answer=answer,
                draft_source=DRAFT_SOURCE,
                draft_rationale=(
                    f"{rule['counseling']} "
                    f"({rule['source']['file']} p{rule['source']['page']})"
                ),
                drafting_agent="codex",
                blinded_from=list(blinded),
            )
        )
        if len(drafted) == COUNTS["KPI-5"]:
            return drafted
    raise ValueError(f"kpi5_replacement_pool_too_small:{len(drafted)}")


def build_candidates() -> dict[str, list[CaseDraft]]:
    report = json.loads(REPLACEMENT_REPORT.read_text(encoding="utf-8"))
    if report.get("indicator_counts") != {
        "KPI-1": 49,
        "KPI-3": 0,
        "KPI-4": 7,
        "KPI-5": 9,
    }:
        raise ValueError("replacement_report_counts_changed")
    extract = load_extract(ROOT)
    blinded = _engine_logic_paths()
    return {
        "KPI-1": build_kpi1_replacements(
            _workbench("KPI-1"), extract, blinded
        ),
        "KPI-4": build_kpi4_replacements(
            _workbench("KPI-4"), extract, blinded
        ),
        "KPI-5": build_kpi5_replacements(
            _workbench("KPI-5"), extract, blinded
        ),
    }


def build_requests(
    candidates: dict[str, list[CaseDraft]],
) -> dict[str, dict[str, Any]]:
    blinded = _engine_logic_paths()
    requests: dict[str, dict[str, Any]] = {}
    for indicator_id, drafts in candidates.items():
        current = _workbench(indicator_id)
        temporary = Workbench(indicator_id, drafts)
        if indicator_id == "KPI-4":
            temporary.primary_ai_draft = {
                "answer_vocabulary": _answer_vocabulary(current)
            }
            role = "primary"
        else:
            role = "review"
        requests[indicator_id] = build_external_ai_request(
            temporary,
            required_blinded_from=blinded,
            requested_role=role,
            required_provider_family="anthropic",
        )
    return requests


def _identity_selection() -> dict[str, Any]:
    registry = load_identity_registry(ROOT)
    options = [
        {
            "registered_name": entry["name"],
            "organization": entry["organization"],
            "reviewer_identity_ref": reviewer_identity_reference(entry),
        }
        for entry in registry["registered_reviewers"]
        if entry.get("may_review_h005") is True
    ]
    if not options:
        raise ValueError("eligible_reviewer_identity_option_missing")
    return {
        "schema_version": "kpi_reviewer_identity_selection_v1",
        "selected_reviewer_identity_ref": "",
        "confirmed_at": "",
        "options": options,
    }


def _instructions() -> str:
    return (
        "KPI 교체 입력 자료\n\n"
        "1. 요청 JSON 3개를 각각 새 Claude 대화에 첨부합니다.\n"
        "2. 요청 파일의 지시대로 JSON만 받아 아래 이름으로 저장합니다.\n"
        "   - kpi1_response.json\n"
        "   - kpi4_response.json\n"
        "   - kpi5_response.json\n"
        "3. reviewer_identity_selection.json에서 등록 정보와 일치하는 항목의 "
        "reviewer_identity_ref를 selected_reviewer_identity_ref에 복사하고 "
        "confirmed_at에 시간대가 있는 ISO 8601 시각을 씁니다.\n"
        "4. MAKE_RETURN_ZIP.cmd를 실행합니다.\n"
        "5. 생성된 kpi_replacement_completed.zip 하나만 반환합니다.\n\n"
        "요청 건수: KPI-1 49건, KPI-4 7건, KPI-5 9건.\n"
        "요청 파일 외의 저장소·엔진 규칙·기존 정답은 첨부하지 않습니다.\n"
    )


def _return_script() -> str:
    files = ["reviewer_identity_selection.json", *RESPONSE_NAMES.values()]
    quoted = ",".join(f"'{name}'" for name in files)
    return (
        "@echo off\r\n"
        "setlocal\r\n"
        "powershell -NoProfile -ExecutionPolicy Bypass -Command "
        f'"$files=@({quoted}); '
        "$missing=$files|Where-Object{-not(Test-Path -LiteralPath $_)}; "
        "if($missing){Write-Error ('Missing: '+($missing -join ', ')); exit 2}; "
        "Compress-Archive -LiteralPath $files -DestinationPath "
        "'kpi_replacement_completed.zip' -Force\"\r\n"
        "if errorlevel 1 exit /b 1\r\n"
        "echo kpi_replacement_completed.zip\r\n"
    )


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    candidates = build_candidates()
    requests = build_requests(candidates)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(
        OUTPUT_DIR / "kpi_replacement_candidates_v1.json",
        {
            "schema_version": "kpi_replacement_candidates_v1",
            "counts": {key: len(value) for key, value in candidates.items()},
            "cases": {
                key: [asdict(item) for item in value]
                for key, value in candidates.items()
            },
        },
    )
    for indicator_id, request in requests.items():
        _write_json(OUTPUT_DIR / REQUEST_NAMES[indicator_id], request)
    _write_json(OUTPUT_DIR / "reviewer_identity_selection.json", _identity_selection())
    (OUTPUT_DIR / "START_HERE.txt").write_text(_instructions(), encoding="utf-8")
    (OUTPUT_DIR / "MAKE_RETURN_ZIP.cmd").write_bytes(
        _return_script().encode("utf-8")
    )

    package_files = [
        "START_HERE.txt",
        "MAKE_RETURN_ZIP.cmd",
        "reviewer_identity_selection.json",
        *REQUEST_NAMES.values(),
    ]
    with zipfile.ZipFile(PACKAGE_PATH, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in package_files:
            info = zipfile.ZipInfo(name, date_time=(2026, 8, 3, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (OUTPUT_DIR / name).read_bytes())
    report = {
        "status": "READY",
        "package": str(PACKAGE_PATH),
        "package_sha256": hashlib.sha256(PACKAGE_PATH.read_bytes()).hexdigest(),
        "counts": {key: len(value) for key, value in candidates.items()},
        "total": sum(len(value) for value in candidates.values()),
        "package_files": package_files,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
