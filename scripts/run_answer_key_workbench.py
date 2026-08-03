"""두 AI의 블라인드 답안을 비교하고, 사람이 최종 결정한다.

100건을 맨손으로 쓰는 대신 이렇게 나눈다.

  export-ai-review   1차 답과 엔진 정보를 뺀 패킷을 만든다
  import-ai-review   다른 제공자 계열 AI의 독립 답안을 가져온다
  review-minimal     불일치·위험·합의 표본만 사람이 상세 검토한다
  approve-consensus  사람이 나머지 AI 합의안을 명시적으로 최종 승인한다
  seal               확정된 정답을 봉인한다. 그다음에 엔진을 돌린다

초안 출처가 측정 대상 엔진이면 거부한다. 상세 검토와 일괄 승인을 구분해 기록한다.
사람의 명시적 최종 승인 없이 AI 합의만으로 정답을 확정하지 않는다.

사용법:
  python scripts/run_answer_key_workbench.py draft  --indicator KPI-1
  python scripts/run_answer_key_workbench.py review --indicator KPI-1 --by 권혁찬
  python scripts/run_answer_key_workbench.py seal   --indicator KPI-1
  python scripts/run_answer_key_workbench.py status --indicator KPI-1
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from argparse import ArgumentParser
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wellnessbox_rnd.evals.adaptive_answer_key_review import (  # noqa: E402
    agent_family,
    approve_consensus_batch,
    build_adaptive_review_plan,
    build_blind_ai_review_packet,
    build_external_ai_request,
    register_blind_primary_ai_draft,
    register_independent_ai_review,
)
from wellnessbox_rnd.evals.answer_key_integrity import (  # noqa: E402
    MIN_SECONDS_PER_DECISION,
    audit_sealing_readiness,
    load_registry,
)
from wellnessbox_rnd.evals.answer_key_workbench import (  # noqa: E402
    CaseDraft,
    Workbench,
    adjudicated_answer_key,
    build_drafts,
    build_provenance,
    decide,
    discard_seal_with_audit_trail,
    load_workbench,
    reviewer_identity_is_traceable,
    save_workbench,
    summarise_adjudication,
)
from wellnessbox_rnd.evals.blinded_drafters import (  # noqa: E402
    DRAFT_SOURCES as BLINDED_DRAFT_SOURCES,
)
from wellnessbox_rnd.evals.blinded_drafters import (
    draft_cases as draft_blinded_cases,
)
from wellnessbox_rnd.evals.reference_corpus_drafters import (  # noqa: E402
    DRAFT_SOURCE as REFERENCE_DRAFT_SOURCE,
)
from wellnessbox_rnd.evals.reference_corpus_drafters import (
    draft_cases as draft_reference_cases,
)
from wellnessbox_rnd.evals.reference_standard import (  # noqa: E402
    load_contract,
    seal_reference_standard,
    write_json,
)
from wellnessbox_rnd.governance.reviewer_credentials import (  # noqa: E402
    load_registry as load_reviewer_identity_registry,
)
from wellnessbox_rnd.governance.reviewer_credentials import (  # noqa: E402
    registered_reviewer_identity_references,
    registered_reviewer_names,
)

ROOT = Path(__file__).resolve().parents[1]
WORKBENCH_DIR = ROOT / "data/original_plan/kpi/workbench"
SEAL_DIR = ROOT / "data/original_plan/kpi/seals"
SEAL_DISPOSAL_DIR = ROOT / "data/original_plan/kpi/seal_disposals"
BAR = "─" * 68
MIN_SECONDS_PER_CASE = MIN_SECONDS_PER_DECISION
COMMAND_MARKERS = ("python ", "scripts/", "scripts\\", "cd ", "--indicator", "git ")
BUILTIN_DRAFTERS = {
    "KPI-1": (draft_reference_cases, REFERENCE_DRAFT_SOURCE),
    "KPI-3": (draft_blinded_cases, BLINDED_DRAFT_SOURCES["KPI-3"]),
    "KPI-4": (draft_blinded_cases, BLINDED_DRAFT_SOURCES["KPI-4"]),
    "KPI-5": (draft_reference_cases, REFERENCE_DRAFT_SOURCE),
}


def _trusted_reviewer_context() -> tuple[set[str], set[str]]:
    registry = load_reviewer_identity_registry(ROOT)
    return (
        registered_reviewer_identity_references(registry),
        registered_reviewer_names(registry),
    )


def looks_like_a_shell_command(answer: str) -> bool:
    """Catch a pasted command line being swallowed as a review answer.

    Pasting several commands at once feeds every line after the first into this
    prompt, which would silently accept case after case. Better to stop.
    """
    folded = answer.strip().casefold()
    return any(marker in folded for marker in COMMAND_MARKERS)


def slug(indicator_id: str) -> str:
    return indicator_id.lower().replace("-", "")


def workbench_path(indicator_id: str) -> Path:
    return WORKBENCH_DIR / f"{slug(indicator_id)}_workbench_v1.json"


def seal_path(indicator_id: str) -> Path:
    return SEAL_DIR / f"{slug(indicator_id)}_reference_seal_v1.json"


def legacy_discarded_seal_path(indicator_id: str) -> Path:
    """Return a seal that was relocated before an audited disposal existed."""
    return (
        SEAL_DIR
        / "discarded"
        / f"{slug(indicator_id)}_reference_seal_v1.json"
    )


def seal_disposal_history_path(indicator_id: str) -> Path:
    return SEAL_DISPOSAL_DIR / f"{slug(indicator_id)}_seal_disposals_v1.json"


def seal_candidate_path(indicator_id: str) -> Path:
    """Find an active seal or a seal relocated before audited disposal."""
    active = seal_path(indicator_id)
    if active.is_file():
        return active
    legacy = legacy_discarded_seal_path(indicator_id)
    if legacy.is_file():
        return legacy
    return active


def say(message: str = "") -> None:
    print(message, flush=True)


def engine_logic_blinded_from() -> list[str]:
    registry = load_registry(ROOT)
    return sorted(
        entry["path"]
        for entry in registry["entries"]
        if entry["role"] == "engine_logic"
    )


def cmd_draft(args) -> int:
    target = workbench_path(args.indicator)
    if target.is_file() and not args.overwrite:
        say(f"이미 초안이 있습니다: {target}")
        say("다시 만들려면 --overwrite 를 붙이세요. 기존 판단 기록도 함께 사라집니다.")
        return 2

    if args.cases:
        if not args.drafting_agent:
            say("--cases 사용 시 --drafting-agent 를 입력해야 합니다.")
            return 2
        if not args.blinded_from_registry and not args.blinded_from:
            say(
                "--cases 사용 시 --blinded-from-registry 또는 "
                "--blinded-from <엔진 파일>을 입력해야 합니다."
            )
            return 2
        cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
        source = args.draft_source or "external_draft_file"
        drafting_agent = args.drafting_agent
        blinded_from = (
            engine_logic_blinded_from()
            if args.blinded_from_registry
            else args.blinded_from
        )
    else:
        if args.indicator not in BUILTIN_DRAFTERS:
            say(f"지원하지 않는 지표입니다: {args.indicator}")
            return 2
        drafter, default_source = BUILTIN_DRAFTERS[args.indicator]
        cases = drafter(args.indicator, ROOT, case_count=args.count)
        source = args.draft_source or default_source
        drafting_agent = args.drafting_agent or "codex"
        blinded_from = args.blinded_from or engine_logic_blinded_from()

    packaged = build_drafts(
        indicator_id=args.indicator,
        cases=cases,
        draft_source=source,
        drafting_agent=drafting_agent,
        blinded_from=blinded_from,
    )
    workbench = Workbench(
        args.indicator, [CaseDraft(**item) for item in packaged["drafts"]], {}
    )
    save_workbench(target, workbench)

    say(json.dumps(
        {
            "status": "READY",
            "workbench_path": str(target),
            "case_count": packaged["case_count"],
            "draft_source": source,
            "drafting_agent": packaged["drafting_agent"],
            "blinded_from": packaged["blinded_from"],
            "next": (
                "python scripts/run_answer_key_workbench.py review "
                f"--indicator {args.indicator} --by <이름>"
            ),
        },
        ensure_ascii=False, indent=2,
    ))
    return 0


def cmd_review(args) -> int:
    target = workbench_path(args.indicator)
    trusted_identity_refs, trusted_reviewer_names = _trusted_reviewer_context()
    if not target.is_file():
        say(f"초안이 없습니다: {target}. 먼저 draft 를 실행하세요.")
        return 2
    workbench = load_workbench(target)
    if getattr(args, "minimal", False):
        plan = build_adaptive_review_plan(workbench)
        if plan["status"] == "BLOCKED":
            say(json.dumps(plan, ensure_ascii=False, indent=2))
            return 2
        required = set(plan["pending_required_detail_ids"])
        pending = [draft for draft in workbench.drafts if draft.case_id in required]
    else:
        pending = workbench.pending()
    if not pending:
        next_step = (
            "approve-consensus 로 AI 합의안을 확인하세요."
            if workbench.ai_review
            and build_adaptive_review_plan(workbench)["status"]
            == "READY_FOR_BATCH_APPROVAL"
            else "남은 건이 없습니다. seal 로 넘어가세요."
        )
        say(next_step)
        return 0

    say(BAR)
    say(f" {args.indicator} 정답 확정  —  남은 {len(pending)}건 / 전체 {len(workbench.drafts)}건")
    say(BAR)
    peer_cases = workbench.ai_review.get("cases", {})
    choices = "Enter = 1차 초안 수락"
    if peer_cases:
        choices += " | p = 2차 AI 의견 수락"
    say(choices + " | e = 수정 | r = 반려 | q = 저장하고 종료")
    say("명령은 한 줄씩 실행하세요. 여러 줄을 붙여넣으면 답변으로 먹혀 중단됩니다.")
    say("수정은 성분을 쉼표로 구분해 입력합니다. 예: omega3, vitaminD, magnesium")

    rushed = 0
    for position, draft in enumerate(pending, start=1):
        say()
        say(f"[{position}/{len(pending)}] {draft.case_id}")
        say(f"  상황: {draft.prompt}")
        say(f"  초안: {', '.join(draft.draft_answer)}")
        if draft.draft_rationale:
            say(f"  근거: {draft.draft_rationale}")
        peer = peer_cases.get(draft.case_id)
        if peer:
            peer_answer = peer["proposed_answer"]
            relation = (
                "일치"
                if sorted(peer_answer) == sorted(draft.draft_answer)
                else "불일치"
            )
            say(f"  2차 AI({relation}): {', '.join(peer_answer)}")
            if peer.get("flags"):
                say(f"  2차 AI 플래그: {', '.join(peer['flags'])}")
            if peer.get("rationale"):
                say(f"  2차 AI 근거: {peer['rationale']}")
        started = time.monotonic()
        try:
            answer = input("  > ").strip()
        except EOFError:
            say("  입력이 끊겼습니다. 여기까지 저장하고 종료합니다.")
            break

        if looks_like_a_shell_command(answer):
            say("  ! 명령어가 입력됐습니다. 여러 줄을 한 번에 붙여넣지 마세요.")
            say("  ! 이 건은 저장하지 않고 종료합니다. 한 명령씩 따로 실행하세요.")
            break

        if answer.lower() == "q":
            break
        note = ""
        if answer.lower() == "r":
            note = input("  반려 사유: ").strip()
            final = None
        elif answer.lower() == "p" and peer:
            final = list(peer["proposed_answer"])
            note = "사람이 2차 AI 의견을 선택함"
        elif answer.lower() == "e":
            edited = input("  수정할 성분(쉼표 구분): ").strip()
            final = [item.strip() for item in edited.split(",") if item.strip()]
            if not final:
                say("  빈 값이라 건너뜁니다.")
                continue
        else:
            final = list(draft.draft_answer)

        elapsed = time.monotonic() - started
        if elapsed < MIN_SECONDS_PER_CASE:
            rushed += 1
            say(
                f"  ! {elapsed:.2f}초 만에 입력돼 저장하지 않았습니다. "
                f"사례를 읽고 최소 {MIN_SECONDS_PER_CASE:.1f}초 뒤 다시 판단하세요."
            )
            continue

        workbench.decisions[draft.case_id] = decide(
            draft=draft,
            final_answer=final,
            decided_by=args.by,
            note=note,
            review_duration_seconds=elapsed,
            trusted_reviewer_identity_refs=trusted_identity_refs,
            trusted_reviewer_names=trusted_reviewer_names,
        )
        save_workbench(target, workbench)

    summary = summarise_adjudication(workbench)
    summary["rushed_decision_count"] = rushed
    say()
    say(BAR)
    say(json.dumps(summary, ensure_ascii=False, indent=2))
    warnings = list(summary["warnings"])
    if rushed:
        warnings.append(f"{rushed}건이 {MIN_SECONDS_PER_CASE}초 미만에 처리됨")
    if warnings:
        say()
        say("주의: " + ", ".join(warnings))
    return 0


def cmd_status(args) -> int:
    target = workbench_path(args.indicator)
    if not target.is_file():
        say(json.dumps({"status": "NOT_STARTED", "workbench_path": str(target)},
                       ensure_ascii=False, indent=2))
        return 2
    workbench = load_workbench(target)
    summary = summarise_adjudication(workbench)
    if workbench.ai_review:
        summary["adaptive_review"] = build_adaptive_review_plan(workbench)
    say(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["complete"] else 2


def cmd_export_ai_review(args) -> int:
    target = workbench_path(args.indicator)
    if not target.is_file():
        say(f"초안이 없습니다: {target}")
        return 2
    packet = build_blind_ai_review_packet(
        load_workbench(target),
        required_blinded_from=engine_logic_blinded_from(),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(packet, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    say(json.dumps(
        {
            "status": "READY",
            "packet_path": str(output),
            "case_count": packet["case_count"],
            "packet_sha256": packet["packet_sha256"],
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


def cmd_export_external_ai_request(args) -> int:
    target = workbench_path(args.indicator)
    if not target.is_file():
        say(f"초안이 없습니다: {target}")
        return 2
    try:
        request = build_external_ai_request(
            load_workbench(target),
            required_blinded_from=engine_logic_blinded_from(),
            requested_role=args.role,
            required_provider_family=args.provider_family,
        )
    except ValueError as exc:
        say(json.dumps(
            {"status": "BLOCKED", "reason": str(exc)},
            ensure_ascii=False,
            indent=2,
        ))
        return 2
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(request, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    say(json.dumps(
        {
            "status": "READY",
            "request_path": str(output),
            "indicator_id": args.indicator,
            "requested_role": args.role,
            "provider_family": args.provider_family,
            "case_count": request["packet"]["case_count"],
            "packet_sha256": request["packet"]["packet_sha256"],
            "request_sha256": request["request_sha256"],
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


def cmd_validate_ai_response(args) -> int:
    target = workbench_path(args.indicator)
    if not target.is_file():
        say(f"초안이 없습니다: {target}")
        return 2
    response_path = Path(args.response)
    response_bytes = response_path.read_bytes()
    response = json.loads(response_bytes.decode("utf-8"))
    workbench = deepcopy(load_workbench(target))
    required = engine_logic_blinded_from()
    agent_key = "drafting_agent" if args.role == "primary" else "reviewing_agent"
    agent = str(response.get(agent_key, ""))
    if agent_family(agent) != args.provider_family:
        say(json.dumps(
            {
                "status": "BLOCKED",
                "reason": "ai_response_provider_family_mismatch",
                "expected": args.provider_family,
                "found": agent_family(agent) or "unknown",
            },
            ensure_ascii=False,
            indent=2,
        ))
        return 2
    try:
        if args.role == "primary":
            record = register_blind_primary_ai_draft(
                workbench,
                drafting_agent=agent,
                draft_source=response.get("draft_source", ""),
                blinded_from=response.get("blinded_from", []),
                required_blinded_from=required,
                packet_sha256=response.get("packet_sha256", ""),
                engine_output_consulted=bool(
                    response.get("engine_output_consulted", False)
                ),
                cases=response.get("cases", []),
                input_response_sha256=hashlib.sha256(response_bytes).hexdigest(),
            )
        else:
            record = register_independent_ai_review(
                workbench,
                reviewing_agent=agent,
                review_source=response.get("review_source", ""),
                blinded_from=response.get("blinded_from", []),
                required_blinded_from=required,
                packet_sha256=response.get("packet_sha256", ""),
                engine_output_consulted=bool(
                    response.get("engine_output_consulted", False)
                ),
                cases=response.get("cases", []),
            )
    except ValueError as exc:
        say(json.dumps(
            {"status": "BLOCKED", "reason": str(exc), "mutated": False},
            ensure_ascii=False,
            indent=2,
        ))
        return 2
    say(json.dumps(
        {
            "status": "READY_TO_IMPORT",
            "indicator_id": args.indicator,
            "role": args.role,
            "provider_family": args.provider_family,
            "case_count": record["case_count"],
            "response_sha256": hashlib.sha256(response_bytes).hexdigest(),
            "mutated": False,
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


def cmd_import_ai_review(args) -> int:
    target = workbench_path(args.indicator)
    if not target.is_file():
        say(f"초안이 없습니다: {target}")
        return 2
    workbench = load_workbench(target)
    response = json.loads(Path(args.response).read_text(encoding="utf-8"))
    required = engine_logic_blinded_from()
    try:
        review = register_independent_ai_review(
            workbench,
            reviewing_agent=response.get("reviewing_agent", ""),
            review_source=response.get("review_source", ""),
            blinded_from=response.get("blinded_from", []),
            required_blinded_from=required,
            packet_sha256=response.get("packet_sha256", ""),
            engine_output_consulted=bool(
                response.get("engine_output_consulted", False)
            ),
            cases=response.get("cases", []),
        )
    except ValueError as exc:
        say(json.dumps(
            {"status": "BLOCKED", "reason": str(exc)},
            ensure_ascii=False,
            indent=2,
        ))
        return 2
    save_workbench(target, workbench)
    plan = build_adaptive_review_plan(workbench)
    say(json.dumps(
        {
            "status": "READY",
            "reviewing_agent": review["reviewing_agent"],
            "case_count": review["case_count"],
            "adaptive_review": plan,
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


def cmd_import_primary_ai_draft(args) -> int:
    target = workbench_path(args.indicator)
    if not target.is_file():
        say(f"초안이 없습니다: {target}")
        return 2
    workbench = load_workbench(target)
    response_path = Path(args.response)
    response_bytes = response_path.read_bytes()
    response = json.loads(response_bytes.decode("utf-8"))
    promote_review_response = bool(
        getattr(args, "promote_review_response", False)
    )
    if promote_review_response:
        drafting_agent = response.get("reviewing_agent", "")
        draft_source = response.get("review_source", "")
        input_response_role = "independent_ai_review_promoted_to_primary"
    else:
        drafting_agent = response.get("drafting_agent", "")
        draft_source = response.get("draft_source", "")
        input_response_role = "primary_ai_draft"
    required = engine_logic_blinded_from()
    try:
        record = register_blind_primary_ai_draft(
            workbench,
            drafting_agent=drafting_agent,
            draft_source=draft_source,
            blinded_from=response.get("blinded_from", []),
            required_blinded_from=required,
            packet_sha256=response.get("packet_sha256", ""),
            engine_output_consulted=bool(
                response.get("engine_output_consulted", False)
            ),
            cases=response.get("cases", []),
            input_response_role=input_response_role,
            input_response_sha256=hashlib.sha256(response_bytes).hexdigest(),
        )
    except ValueError as exc:
        say(json.dumps(
            {"status": "BLOCKED", "reason": str(exc)},
            ensure_ascii=False,
            indent=2,
        ))
        return 2
    save_workbench(target, workbench)
    say(json.dumps(
        {
            "status": "READY_FOR_INDEPENDENT_AI_REVIEW",
            "drafting_agent": record["drafting_agent"],
            "case_count": record["case_count"],
            "next": (
                "같은 블라인드 패킷을 다른 제공자 계열 AI에 전달한 뒤 "
                "import-ai-review를 실행하세요."
            ),
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


def cmd_minimal_status(args) -> int:
    target = workbench_path(args.indicator)
    if not target.is_file():
        say(f"초안이 없습니다: {target}")
        return 2
    plan = build_adaptive_review_plan(load_workbench(target))
    say(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0 if plan["status"] in {
        "READY_FOR_BATCH_APPROVAL",
        "READY_TO_SEAL",
    } else 2


def cmd_review_minimal(args) -> int:
    args.minimal = True
    return cmd_review(args)


def cmd_approve_consensus(args) -> int:
    target = workbench_path(args.indicator)
    if not target.is_file():
        say(f"초안이 없습니다: {target}")
        return 2
    workbench = load_workbench(target)
    confirmation = f"{args.indicator} AI 합의안 일괄 승인"
    say("상세 검토하지 않은 AI 합의 사례를 일괄 승인합니다.")
    say(f"계속하려면 정확히 입력하세요: {confirmation}")
    try:
        answer = input("  > ").strip()
    except EOFError:
        answer = ""
    try:
        approval = approve_consensus_batch(
            workbench,
            approved_by=args.by,
            confirmation=answer,
        )
    except ValueError as exc:
        say(json.dumps(
            {"status": "BLOCKED", "reason": str(exc)},
            ensure_ascii=False,
            indent=2,
        ))
        return 2
    save_workbench(target, workbench)
    say(json.dumps(
        {"status": "APPROVED", "batch_approval": approval},
        ensure_ascii=False,
        indent=2,
    ))
    return 0


def cmd_seal(args) -> int:
    target = workbench_path(args.indicator)
    if not target.is_file():
        say(f"초안이 없습니다: {target}")
        return 2
    workbench = load_workbench(target)
    summary = summarise_adjudication(workbench)
    if not summary["complete"]:
        say(json.dumps(
            {"status": "BLOCKED", "reason": "adjudication_incomplete",
             "pending": summary["counts"]["pending"]},
            ensure_ascii=False, indent=2,
        ))
        return 2

    integrity = audit_sealing_readiness(ROOT, args.indicator)
    if integrity["status"] != "READY":
        say(json.dumps(integrity, ensure_ascii=False, indent=2))
        return 2

    destination = seal_path(args.indicator)
    if destination.is_file():
        say(json.dumps(
            {"status": "BLOCKED", "reason": "seal_already_exists", "path": str(destination)},
            ensure_ascii=False, indent=2,
        ))
        return 2

    reviewers = summary["reviewers"]
    if len(reviewers) != 1:
        say(json.dumps(
            {"status": "BLOCKED", "reason": "expected_exactly_one_reviewer",
             "reviewers": reviewers},
            ensure_ascii=False, indent=2,
        ))
        return 2

    try:
        provenance = build_provenance(
            workbench,
            summary,
            system_under_test_id=getattr(args, "system_under_test_id", ""),
            system_under_test_provider_family=getattr(
                args,
                "system_under_test_provider_family",
                "",
            ),
        )
    except ValueError as exc:
        say(json.dumps(
            {"status": "BLOCKED", "reason": str(exc)},
            ensure_ascii=False,
            indent=2,
        ))
        return 2

    provenance["integrity_audit"] = integrity["integrity_audit"]
    seal = seal_reference_standard(
        indicator_id=args.indicator,
        cases=adjudicated_answer_key(workbench),
        sealed_by=reviewers[0],
        sealed_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        contract=load_contract(ROOT),
        provenance=provenance,
    )
    if not seal["meets_minimum_sample"]:
        say(json.dumps(
            {
                "status": "BLOCKED",
                "reason": "minimum_sample_not_met",
                "case_count": seal["case_count"],
                "minimum_sample_count": seal["minimum_sample_count"],
            },
            ensure_ascii=False,
            indent=2,
        ))
        return 2
    write_json(destination, seal)

    say(json.dumps(
        {
            "status": "READY",
            "seal_path": str(destination),
            "case_count": seal["case_count"],
            "minimum_sample_count": seal["minimum_sample_count"],
            "edit_rate_pct": summary["edit_rate_pct"],
            "warnings": summary["warnings"],
            "seal_sha256": seal["seal_sha256"],
        },
        ensure_ascii=False, indent=2,
    ))
    return 0


def _disposal_identity_counts(
    history: dict,
    trusted_identity_refs: set[str],
    trusted_reviewer_names: set[str],
) -> tuple[int, int]:
    events = history.get("events", [])
    traceable = 0
    for event in events:
        actor = str(event.get("discarded_by", "")).strip()
        identity_ref = str(event.get("discarded_by_identity_ref", "")).strip()
        if reviewer_identity_is_traceable(
            actor,
            identity_ref,
            trusted_identity_refs=trusted_identity_refs,
            trusted_reviewer_names=trusted_reviewer_names,
        ):
            traceable += 1
    return traceable, len(events) - traceable


def cmd_discard_status(args) -> int:
    """Report disposal evidence without recording a human decision."""
    destination = seal_candidate_path(args.indicator)
    history_path = seal_disposal_history_path(args.indicator)
    history = {"events": []}
    if history_path.is_file():
        history = json.loads(history_path.read_text(encoding="utf-8"))
    trusted_identity_refs, trusted_reviewer_names = _trusted_reviewer_context()
    formal_count, unverified_count = _disposal_identity_counts(
        history, trusted_identity_refs, trusted_reviewer_names
    )
    if not destination.is_file():
        say(json.dumps(
            {
                "status": (
                    "AWAITING_IDENTITY_ATTESTATION"
                    if unverified_count
                    else "NO_SEAL_CANDIDATE"
                ),
                "indicator_id": args.indicator,
                "formal_disposal_count": formal_count,
                "unverified_disposal_count": unverified_count,
            },
            ensure_ascii=False,
            indent=2,
        ))
        return 2

    seal = json.loads(destination.read_text(encoding="utf-8"))
    if seal.get("indicator_id") != args.indicator:
        say(json.dumps(
            {
                "status": "BLOCKED",
                "reason": "seal_indicator_mismatch",
                "requested": args.indicator,
                "found": seal.get("indicator_id"),
            },
            ensure_ascii=False,
            indent=2,
        ))
        return 2

    actual_sha256 = hashlib.sha256(destination.read_bytes()).hexdigest()
    say(json.dumps(
        {
            "status": "AWAITING_HUMAN_CONFIRMATION",
            "indicator_id": args.indicator,
            "seal_path": str(destination),
            "file_sha256": actual_sha256,
            "embedded_seal_sha256": seal.get("seal_sha256"),
            "formal_disposal_count": formal_count,
            "unverified_disposal_count": unverified_count,
            "mutated": False,
            "next": (
                "사람이 폐기 사유를 확인한 뒤 discard-seal을 실행하고 "
                f"'{args.indicator} 봉인 폐기'를 직접 입력한다."
            ),
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


def cmd_discard_seal(args) -> int:
    destination = seal_candidate_path(args.indicator)
    trusted_identity_refs, trusted_reviewer_names = _trusted_reviewer_context()
    target = workbench_path(args.indicator)
    if not destination.is_file():
        say(f"폐기할 봉인이 없습니다: {seal_path(args.indicator)}")
        return 2
    if not target.is_file():
        say(f"워크벤치가 없습니다: {target}")
        return 2

    seal = json.loads(destination.read_text(encoding="utf-8"))
    if seal.get("indicator_id") != args.indicator:
        say(json.dumps(
            {
                "status": "BLOCKED",
                "reason": "seal_indicator_mismatch",
                "requested": args.indicator,
                "found": seal.get("indicator_id"),
            },
            ensure_ascii=False,
            indent=2,
        ))
        return 2

    confirmation = f"{args.indicator} 봉인 폐기"
    say(BAR)
    say(f"활성 봉인: {destination}")
    say(f"봉인 SHA-256: {seal.get('seal_sha256', '(없음)')}")
    say(f"폐기자: {args.by}")
    say(f"폐기 사유: {args.reason}")
    say("기존 봉인과 판단 기록은 archive에 보존하고 현재 판단 기록은 초기화합니다.")
    say(f"계속하려면 정확히 입력하세요: {confirmation}")
    try:
        answer = input("  > ").strip()
    except EOFError:
        answer = ""
    if answer != confirmation:
        say(json.dumps(
            {"status": "CANCELLED", "reason": "human_confirmation_not_received"},
            ensure_ascii=False,
            indent=2,
        ))
        return 2

    try:
        record = discard_seal_with_audit_trail(
            active_seal_path=destination,
            workbench_path=target,
            history_path=seal_disposal_history_path(args.indicator),
            archive_dir=SEAL_DISPOSAL_DIR / "archive",
            record_root=ROOT,
            discarded_by=args.by,
            reason=args.reason,
            trusted_reviewer_identity_refs=trusted_identity_refs,
            trusted_reviewer_names=trusted_reviewer_names,
        )
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        say(json.dumps(
            {"status": "BLOCKED", "reason": str(exc)},
            ensure_ascii=False,
            indent=2,
        ))
        return 2

    say(json.dumps(
        {
            "status": "DISCARDED",
            "indicator_id": args.indicator,
            "record": record,
            "next": (
                "python scripts/run_answer_key_workbench.py review "
                f"--indicator {args.indicator} --by <이름>"
            ),
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    draft = sub.add_parser("draft", help="독립 출처로 초안을 만든다")
    draft.add_argument("--indicator", required=True)
    draft.add_argument("--count", type=int, default=100)
    draft.add_argument("--cases", default=None, help="외부 초안 파일 경로")
    draft.add_argument("--draft-source", default=None)
    draft.add_argument(
        "--drafting-agent",
        default=None,
        help="초안을 만든 주체(예: codex, claude, 사람)",
    )
    draft.add_argument(
        "--blinded-from",
        action="append",
        default=None,
        help="초안 작성 때 읽지 않은 엔진 파일. 여러 번 입력할 수 있습니다.",
    )
    draft.add_argument(
        "--blinded-from-registry",
        action="store_true",
        help="모든 engine_logic 파일을 blinded_from에 기록합니다.",
    )
    draft.add_argument("--overwrite", action="store_true")
    draft.set_defaults(func=cmd_draft)

    review = sub.add_parser("review", help="한 건씩 확정한다")
    review.add_argument("--indicator", required=True)
    review.add_argument("--by", required=True, help="확정하는 사람 이름")
    review.set_defaults(func=cmd_review)

    export_ai = sub.add_parser(
        "export-ai-review",
        help="1차 답과 엔진 정보를 뺀 2차 AI 검토 패킷을 만든다",
    )
    export_ai.add_argument("--indicator", required=True)
    export_ai.add_argument("--output", required=True)
    export_ai.set_defaults(func=cmd_export_ai_review)

    export_request = sub.add_parser(
        "export-external-ai-request",
        help="외부 AI에 단독 전달할 블라인드 요청 파일을 만든다",
    )
    export_request.add_argument("--indicator", required=True)
    export_request.add_argument("--role", required=True, choices=("primary", "review"))
    export_request.add_argument(
        "--provider-family",
        required=True,
        choices=("anthropic", "google", "meta", "openai"),
    )
    export_request.add_argument("--output", required=True)
    export_request.set_defaults(func=cmd_export_external_ai_request)

    validate_response = sub.add_parser(
        "validate-ai-response",
        help="워크벤치를 바꾸지 않고 외부 AI 응답의 가져오기 가능 여부를 검사한다",
    )
    validate_response.add_argument("--indicator", required=True)
    validate_response.add_argument("--response", required=True)
    validate_response.add_argument(
        "--role", required=True, choices=("primary", "review")
    )
    validate_response.add_argument(
        "--provider-family",
        required=True,
        choices=("anthropic", "google", "meta", "openai"),
    )
    validate_response.set_defaults(func=cmd_validate_ai_response)

    import_ai = sub.add_parser(
        "import-ai-review",
        help="독립 2차 AI 의견을 검증해 워크벤치에 붙인다",
    )
    import_ai.add_argument("--indicator", required=True)
    import_ai.add_argument("--response", required=True)
    import_ai.set_defaults(func=cmd_import_ai_review)

    import_primary = sub.add_parser(
        "import-primary-ai-draft",
        help="KPI-3·4에 첫 번째 블라인드 AI 초안을 넣는다",
    )
    import_primary.add_argument("--indicator", required=True)
    import_primary.add_argument("--response", required=True)
    import_primary.add_argument(
        "--promote-review-response",
        action="store_true",
        help=(
            "블라인드 2차 의견 형식의 응답을 KPI-3·4 1차 초안으로 명시 전환한다. "
            "원래 응답 역할은 provenance에 보존한다."
        ),
    )
    import_primary.set_defaults(func=cmd_import_primary_ai_draft)

    minimal = sub.add_parser(
        "review-minimal",
        help="불일치·플래그·결정적 표본만 상세 검토한다",
    )
    minimal.add_argument("--indicator", required=True)
    minimal.add_argument("--by", required=True, help="확정하는 사람 이름")
    minimal.set_defaults(func=cmd_review_minimal)

    minimal_status = sub.add_parser(
        "minimal-status",
        help="적응형 상세 검토와 일괄 승인 준비 상태를 본다",
    )
    minimal_status.add_argument("--indicator", required=True)
    minimal_status.set_defaults(func=cmd_minimal_status)

    approve = sub.add_parser(
        "approve-consensus",
        help="상세 검토 뒤 남은 AI 합의안을 사람이 명시적으로 승인한다",
    )
    approve.add_argument("--indicator", required=True)
    approve.add_argument("--by", required=True, help="일괄 승인하는 사람 이름")
    approve.set_defaults(func=cmd_approve_consensus)

    status = sub.add_parser("status", help="진행 상황만 본다")
    status.add_argument("--indicator", required=True)
    status.set_defaults(func=cmd_status)

    seal = sub.add_parser("seal", help="확정된 정답을 봉인한다")
    seal.add_argument("--indicator", required=True)
    seal.add_argument(
        "--system-under-test-id",
        "--system-under-test-agent",
        dest="system_under_test_id",
        default="",
        help="측정 대상 엔진의 고유 ID. 초안 작성 주체와 같을 수 없습니다.",
    )
    seal.add_argument(
        "--system-under-test-provider-family",
        default="",
        help="KPI-4 상담 모델 제공자 계열(예: openai, anthropic). KPI-4는 필수입니다.",
    )
    seal.set_defaults(func=cmd_seal)

    discard = sub.add_parser("discard-seal", help="사람 확인 후 봉인과 판단 기록을 폐기한다")
    discard.add_argument("--indicator", required=True)
    discard.add_argument("--by", required=True, help="폐기하는 사람 이름")
    discard.add_argument("--reason", required=True, help="폐기 사유")
    discard.set_defaults(func=cmd_discard_seal)

    discard_status = sub.add_parser(
        "discard-status",
        help="봉인 폐기 후보와 정식 폐기 이력을 읽기 전용으로 확인한다",
    )
    discard_status.add_argument("--indicator", required=True)
    discard_status.set_defaults(func=cmd_discard_status)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
