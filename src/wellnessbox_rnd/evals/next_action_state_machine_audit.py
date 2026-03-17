from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from wellnessbox_rnd.schemas.next_action_state_machine import (
    next_action_state_transition_matrix,
    phase_sensitive_followup_actions,
)


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_next_action_state_machine_audit(
    *,
    followup_report: dict[str, object],
    followup_report_path: str | Path,
    next_action_report: dict[str, object],
    next_action_report_path: str | Path,
) -> dict[str, object]:
    dataset_path = Path(str(followup_report.get("dataset_path")))
    action_counts = _load_followup_action_counts(dataset_path)
    transition_matrix = next_action_state_transition_matrix()
    phase_sensitive_actions = phase_sensitive_followup_actions()
    next_action_scope = str(next_action_report.get("state_machine_scope") or "")
    next_action_phase_actions = _sorted_str_list(
        next_action_report.get("phase_sensitive_followup_actions")
    )
    shared_followup_actions = _shared_followup_actions(transition_matrix)
    runtime_only_actions = _runtime_only_actions(transition_matrix)
    drift_findings = _build_drift_findings(
        transition_matrix=transition_matrix,
        phase_sensitive_actions=phase_sensitive_actions,
        shared_followup_actions=shared_followup_actions,
    )

    audit = {
        "audit_name": "next_action_state_machine_audit_v1",
        "source_artifacts": {
            "followup_report_path": str(followup_report_path),
            "next_action_report_path": str(next_action_report_path),
        },
        "explicit_contract_status": {
            "followup_contract_schema_version": followup_report.get("schema_version"),
            "next_action_contract_schema_version": next_action_report.get("schema_version"),
            "next_action_state_machine_scope": next_action_scope,
            "phase_sensitive_followup_actions": phase_sensitive_actions,
            "shared_followup_actions": shared_followup_actions,
            "runtime_only_actions": runtime_only_actions,
            "next_action_contract_declares_phase_sensitive_actions": (
                next_action_phase_actions == phase_sensitive_actions
            ),
        },
        "transition_matrix": transition_matrix,
        "shared_action_transition_matrix": [
            item
            for item in transition_matrix
            if str(item.get("next_action")) in shared_followup_actions
        ],
        "dataset_action_distribution": {
            "step0_action_counts": dict(action_counts["step0"]),
            "step_positive_action_counts": dict(action_counts["step_positive"]),
        },
        "drift_findings": drift_findings,
        "readable_summary": _build_readable_summary(
            transition_matrix=transition_matrix,
            drift_findings=drift_findings,
            shared_followup_actions=shared_followup_actions,
            runtime_only_actions=runtime_only_actions,
        ),
    }
    audit["validation_issues"] = validate_next_action_state_machine_audit(audit)
    return audit


def validate_next_action_state_machine_audit(
    audit: dict[str, object],
) -> list[str]:
    issues: list[str] = []
    contract_status = _as_dict(audit.get("explicit_contract_status"))
    drift_findings = _as_list(audit.get("drift_findings"))
    dataset_distribution = _as_dict(audit.get("dataset_action_distribution"))
    readable_summary = _as_dict(audit.get("readable_summary"))

    if contract_status.get("next_action_state_machine_scope") != "runtime_request_decision":
        issues.append("next_action_contract_missing_runtime_scope")
    if not contract_status.get("next_action_contract_declares_phase_sensitive_actions"):
        issues.append("next_action_contract_missing_phase_sensitive_actions")
    if "continue_plan" not in _sorted_str_list(contract_status.get("shared_followup_actions")):
        issues.append("continue_plan_missing_from_shared_followup_actions")
    if "re_optimize" not in _sorted_str_list(contract_status.get("shared_followup_actions")):
        issues.append("re_optimize_missing_from_shared_followup_actions")
    if "collect_more_input" not in _sorted_str_list(contract_status.get("runtime_only_actions")):
        issues.append("collect_more_input_should_remain_runtime_only")

    step0_counts = _as_dict(dataset_distribution.get("step0_action_counts"))
    step_positive_counts = _as_dict(dataset_distribution.get("step_positive_action_counts"))
    if int(step_positive_counts.get("continue_plan", 0)) <= 0:
        issues.append("missing_followup_continue_plan_examples")
    if int(step0_counts.get("re_optimize", 0)) <= 0:
        issues.append("missing_step0_re_optimize_examples")
    if not drift_findings:
        issues.append("missing_drift_findings")
    if readable_summary.get("unexpected_drift_count") != 0:
        issues.append("unexpected_shared_state_machine_drift_detected")

    return issues


def render_next_action_state_machine_audit_markdown(
    audit: dict[str, object],
) -> str:
    status = _as_dict(audit.get("explicit_contract_status"))
    distribution = _as_dict(audit.get("dataset_action_distribution"))
    readable_summary = _as_dict(audit.get("readable_summary"))
    lines = [
        "# next action state machine audit v1",
        "",
        "## readable summary",
        "",
        f"- audit_status: `{readable_summary.get('audit_status')}`",
        f"- shared_followup_actions: `{status.get('shared_followup_actions', [])}`",
        f"- runtime_only_actions: `{status.get('runtime_only_actions', [])}`",
        (
            "- continue_plan_alignment: "
            f"`{readable_summary.get('continue_plan_alignment', {})}`"
        ),
        (
            "- re_optimize_alignment: "
            f"`{readable_summary.get('re_optimize_alignment', {})}`"
        ),
        f"- unexpected_drift_count: `{readable_summary.get('unexpected_drift_count')}`",
        "",
        "## contract status",
        "",
        f"- followup_contract_schema_version: `{status.get('followup_contract_schema_version')}`",
        (
            "- next_action_contract_schema_version: "
            f"`{status.get('next_action_contract_schema_version')}`"
        ),
        f"- next_action_state_machine_scope: `{status.get('next_action_state_machine_scope')}`",
        (
            "- phase_sensitive_followup_actions: "
            f"`{status.get('phase_sensitive_followup_actions', [])}`"
        ),
        "- next_action_contract_declares_phase_sensitive_actions: "
        f"`{status.get('next_action_contract_declares_phase_sensitive_actions')}`",
        "",
        "## dataset action distribution",
        "",
        f"- step0_action_counts: `{distribution.get('step0_action_counts', {})}`",
        f"- step_positive_action_counts: `{distribution.get('step_positive_action_counts', {})}`",
        "",
        "## transition matrix",
        "",
        "| next_action | runtime_workflow_state | followup_step0_state | "
        "followup_step_positive_state | phase_sensitive |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in _as_list(audit.get("transition_matrix")):
        matrix_item = _as_dict(item)
        lines.append(
            "| "
            f"{matrix_item.get('next_action')} | "
            f"{matrix_item.get('runtime_workflow_state')} | "
            f"{matrix_item.get('followup_step0_state')} | "
            f"{matrix_item.get('followup_step_positive_state')} | "
            f"{matrix_item.get('phase_sensitive')} |"
        )
    lines.extend(["", "## shared action transition matrix", ""])
    for item in _as_list(audit.get("shared_action_transition_matrix")):
        matrix_item = _as_dict(item)
        lines.append(
            "- "
            f"{matrix_item.get('next_action')}: "
            f"runtime=`{matrix_item.get('runtime_workflow_state')}`, "
            f"step0=`{matrix_item.get('followup_step0_state')}`, "
            f"step_positive=`{matrix_item.get('followup_step_positive_state')}`"
        )
    lines.extend(["", "## drift findings", ""])
    for finding in _as_list(audit.get("drift_findings")):
        finding_dict = _as_dict(finding)
        lines.append(
            "- "
            f"{finding_dict.get('next_action')}: "
            f"runtime=`{finding_dict.get('runtime_workflow_state')}`, "
            f"step0=`{finding_dict.get('followup_step0_state')}`, "
            f"step_positive=`{finding_dict.get('followup_step_positive_state')}`, "
            f"kind=`{finding_dict.get('drift_kind')}`"
        )
    lines.extend(
        [
            "",
            "## validation",
            "",
            f"- validation_issues: `{audit.get('validation_issues', [])}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_next_action_state_machine_audit_files(
    *,
    audit: dict[str, object],
    json_path: str | Path,
    md_path: str | Path,
) -> None:
    json_file = Path(json_path)
    md_file = Path(md_path)
    json_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    md_file.write_text(
        render_next_action_state_machine_audit_markdown(audit),
        encoding="utf-8",
    )


def _load_followup_action_counts(dataset_path: Path) -> dict[str, Counter[str]]:
    step0: Counter[str] = Counter()
    step_positive: Counter[str] = Counter()
    for line in dataset_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        labels = _as_dict(payload.get("labels"))
        action = str(labels.get("next_action"))
        if not action:
            continue
        trajectory_step = int(payload.get("trajectory_step", 0))
        if trajectory_step == 0:
            step0[action] += 1
        else:
            step_positive[action] += 1
    return {"step0": step0, "step_positive": step_positive}


def _build_drift_findings(
    *,
    transition_matrix: list[dict[str, object]],
    phase_sensitive_actions: list[str],
    shared_followup_actions: list[str],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for item in transition_matrix:
        action = str(item.get("next_action"))
        if action not in phase_sensitive_actions:
            continue
        step0_matches = bool(item.get("runtime_matches_followup_step0"))
        step_positive_matches = bool(item.get("runtime_matches_followup_step_positive"))
        if action in shared_followup_actions and (step0_matches or step_positive_matches):
            drift_kind = "expected_phase_sensitive_divergence"
        elif action in shared_followup_actions:
            drift_kind = "unexpected_shared_drift"
        else:
            drift_kind = "runtime_only_action_outside_followup_contract"
        findings.append(
            {
                "next_action": action,
                "runtime_workflow_state": item.get("runtime_workflow_state"),
                "followup_step0_state": item.get("followup_step0_state"),
                "followup_step_positive_state": item.get("followup_step_positive_state"),
                "drift_type": "phase_sensitive_followup_alignment",
                "drift_kind": drift_kind,
            }
        )
    return findings


def _build_readable_summary(
    *,
    transition_matrix: list[dict[str, object]],
    drift_findings: list[dict[str, object]],
    shared_followup_actions: list[str],
    runtime_only_actions: list[str],
) -> dict[str, object]:
    continue_plan = _find_transition(transition_matrix, "continue_plan")
    re_optimize = _find_transition(transition_matrix, "re_optimize")
    unexpected_drift_count = sum(
        1
        for finding in drift_findings
        if _as_dict(finding).get("drift_kind") == "unexpected_shared_drift"
    )
    return {
        "audit_status": (
            "explicit_shared_contract_no_unexpected_drift"
            if unexpected_drift_count == 0
            else "unexpected_shared_drift_present"
        ),
        "shared_followup_action_count": len(shared_followup_actions),
        "runtime_only_action_count": len(runtime_only_actions),
        "continue_plan_alignment": {
            "runtime_workflow_state": continue_plan.get("runtime_workflow_state"),
            "followup_step0_state": continue_plan.get("followup_step0_state"),
            "followup_step_positive_state": continue_plan.get(
                "followup_step_positive_state"
            ),
            "runtime_matches_followup_step_positive": continue_plan.get(
                "runtime_matches_followup_step_positive"
            ),
        },
        "re_optimize_alignment": {
            "runtime_workflow_state": re_optimize.get("runtime_workflow_state"),
            "followup_step0_state": re_optimize.get("followup_step0_state"),
            "followup_step_positive_state": re_optimize.get(
                "followup_step_positive_state"
            ),
            "runtime_matches_followup_step0": re_optimize.get(
                "runtime_matches_followup_step0"
            ),
            "runtime_matches_followup_step_positive": re_optimize.get(
                "runtime_matches_followup_step_positive"
            ),
        },
        "unexpected_drift_count": unexpected_drift_count,
    }


def _shared_followup_actions(
    transition_matrix: list[dict[str, object]],
) -> list[str]:
    return sorted(
        str(item.get("next_action"))
        for item in transition_matrix
        if str(item.get("next_action")) not in {"blocked", "collect_more_input"}
    )


def _runtime_only_actions(
    transition_matrix: list[dict[str, object]],
) -> list[str]:
    return sorted(
        str(item.get("next_action"))
        for item in transition_matrix
        if str(item.get("next_action")) in {"blocked", "collect_more_input"}
    )


def _find_transition(
    transition_matrix: list[dict[str, object]],
    action: str,
) -> dict[str, object]:
    for item in transition_matrix:
        if str(item.get("next_action")) == action:
            return item
    return {}


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _sorted_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(item) for item in value)


__all__ = [
    "build_next_action_state_machine_audit",
    "load_json_artifact",
    "render_next_action_state_machine_audit_markdown",
    "validate_next_action_state_machine_audit",
    "write_next_action_state_machine_audit_files",
]
