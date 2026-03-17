from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_weakest_slice_frozen_eval_audit(
    *,
    eval_report: dict[str, object],
    eval_report_path: str | Path,
    pro_report: dict[str, object],
    pro_report_path: str | Path,
    parser_report: dict[str, object],
    parser_report_path: str | Path,
    file_schema_report: dict[str, object],
    file_schema_report_path: str | Path,
    cgm_event_report: dict[str, object],
    cgm_event_report_path: str | Path,
    cgm_slice_report: dict[str, object],
    cgm_slice_report_path: str | Path,
    followup_report: dict[str, object],
    followup_report_path: str | Path,
    next_action_report: dict[str, object],
    next_action_report_path: str | Path,
    next_action_blocked_report: dict[str, object] | None = None,
    next_action_blocked_report_path: str | Path | None = None,
    safety_report: dict[str, object],
    safety_report_path: str | Path,
) -> dict[str, object]:
    weakest_slice_summary = _as_dict(eval_report.get("weakest_slice_summary"))
    summary = _as_dict(eval_report.get("summary"))
    integration_metric = _as_dict(summary.get("sensor_genetic_integration_rate_pct"))
    integration_details = _as_dict(integration_metric.get("details"))
    weakest_by_metric = _as_dict(weakest_slice_summary.get("weakest_category_by_metric"))
    weakest_overall = _as_dict(weakest_slice_summary.get("weakest_category_overall"))
    metrics_by_family = _metrics_by_family(weakest_by_metric, weakest_overall)
    pro_improvement_metric = _as_dict(_as_dict(pro_report.get("improvement_metric")))

    parser_failure_types = _sorted_str_list(parser_report.get("supported_failure_types"))
    parser_failure_taxonomy = _failure_type_taxonomy_entries(
        parser_failure_types,
        default_stage="parser_normalization_fallback",
    )
    file_schema_failure_types = sorted(
        {
            failure_type
            for result in _as_dict(file_schema_report.get("failure_type_examples")).values()
            if isinstance(result, dict)
            for failure_type in _sorted_str_list(result.get("failure_types"))
        }
    )
    file_schema_failure_taxonomy = _failure_type_taxonomy_entries(
        file_schema_failure_types,
        default_stage="file_schema_validation",
    )
    combined_failure_types = sorted(set(parser_failure_types) | set(file_schema_failure_types))
    combined_failure_taxonomy = _failure_type_taxonomy_entries(
        combined_failure_types,
        default_stage="unknown",
    )
    cgm_event = _as_dict(cgm_event_report.get("event"))
    cgm_event_eval_projection = _as_dict(
        _as_dict(cgm_event.get("eval_integration_projection")).get("cgm")
    )
    cgm_slice_connected_flows = _as_dict(cgm_slice_report.get("connected_flows"))
    followup_not_connected = _sorted_str_list(
        followup_report.get("not_directly_connected_in_this_contract")
    )
    next_action_branch_fixtures = _next_action_branch_fixtures(
        primary_report=next_action_report,
        primary_report_path=next_action_report_path,
        blocked_report=next_action_blocked_report,
        blocked_report_path=next_action_blocked_report_path,
    )
    next_action_issue_counts = [
        int(branch.get("issue_count", 0))
        for branch in next_action_branch_fixtures
        if branch.get("issue_count") is not None
    ]

    required_components = {
        "PROImprovementSummaryV1_shared_event_path": {
            "status": "connected"
            if _as_dict(pro_improvement_metric.get("shared_event_path_proof")).get(
                "valid_case_count"
            )
            else "missing",
            "artifact_path": str(pro_report_path),
            "proof": {
                "shared_event_schema_version": pro_improvement_metric.get(
                    "shared_event_schema_version"
                ),
                "shared_event_adapter": pro_improvement_metric.get("shared_event_adapter"),
                "shared_event_unifier": pro_improvement_metric.get("shared_event_unifier"),
                "shared_event_validator": pro_improvement_metric.get("shared_event_validator"),
                "single_path_status": _as_dict(
                    pro_improvement_metric.get("single_path_status")
                ),
                "shared_event_path_proof": _as_dict(
                    pro_improvement_metric.get("shared_event_path_proof")
                ),
                "synthetic_dataset_summary": _as_dict(
                    pro_improvement_metric.get("synthetic_dataset_summary")
                ),
            },
            "connected_to": [
                "weakest_slice_summary",
                "frozen_eval.efficacy_improvement_pp",
            ],
        },
        "parser_outputs": {
            "status": "connected" if parser_report.get("case_count") else "missing",
            "artifact_path": str(parser_report_path),
            "proof": {
                "case_count": parser_report.get("case_count"),
                "wearable_case_count": parser_report.get("wearable_case_count"),
                "cgm_case_count": parser_report.get("cgm_case_count"),
                "genetic_case_count": parser_report.get("genetic_case_count"),
            },
            "connected_to": [
                "supported_parser_failure_types",
                "CGMNormalizedEventV1",
                "sensor_genetic_integration_rate_pct",
            ],
        },
        "file_schema_validation": {
            "status": "connected"
            if _all_schema_fixtures_pass(file_schema_report)
            else "missing",
            "artifact_path": str(file_schema_report_path),
            "proof": {
                "valid_fixture_pass_count": _valid_fixture_pass_count(file_schema_report),
                "valid_fixture_total": len(
                    _as_dict(file_schema_report.get("valid_fixture_results"))
                ),
                "failure_type_examples": sorted(
                    _as_dict(file_schema_report.get("failure_type_examples"))
                ),
            },
            "connected_to": [
                "parser_outputs",
                "supported_parser_failure_types",
                "sensor_genetic_integration_rate_pct",
            ],
        },
        "supported_parser_failure_types": {
            "status": "connected" if combined_failure_types else "missing",
            "artifact_path": str(parser_report_path),
            "proof": {
                "failure_contract_version": parser_report.get("failure_contract_version"),
                "parser_supported_failure_types": parser_failure_types,
                "parser_supported_failure_taxonomy": parser_failure_taxonomy,
                "schema_failure_type_examples": file_schema_failure_types,
                "schema_failure_type_taxonomy": file_schema_failure_taxonomy,
                "combined_failure_type_count": len(combined_failure_types),
                "combined_failure_type_taxonomy": combined_failure_taxonomy,
                "taxonomy_stage_counts": _count_taxonomy_field(
                    combined_failure_taxonomy,
                    key="stage",
                ),
                "taxonomy_modality_counts": _count_taxonomy_field(
                    combined_failure_taxonomy,
                    key="modality",
                ),
                "taxonomy_family_counts": _count_taxonomy_field(
                    combined_failure_taxonomy,
                    key="family",
                ),
                "taxonomy_field_counts": _count_taxonomy_field(
                    combined_failure_taxonomy,
                    key="field",
                ),
                "taxonomy_ambiguity_count": sum(
                    1
                    for item in combined_failure_taxonomy
                    if str(item.get("family")) == "unclassified"
                    or str(item.get("modality")) == "unknown"
                ),
                "taxonomy_field_ambiguity_count": sum(
                    1
                    for item in combined_failure_taxonomy
                    if str(item.get("field")) == "unknown"
                ),
            },
            "connected_to": [
                "parser_outputs",
                "cgm_slice_bridge_summary_v1",
                "sensor_genetic_integration_rate_pct",
            ],
        },
        "CGMNormalizedEventV1": {
            "status": "connected" if cgm_event_report.get("valid") else "missing",
            "artifact_path": str(cgm_event_report_path),
            "proof": {
                "threshold_tags": _sorted_str_list(cgm_event.get("threshold_tags")),
                "eval_attempted": cgm_event_eval_projection.get("attempted"),
                "eval_success": cgm_event_eval_projection.get("success"),
                "validation_issues": _sorted_str_list(cgm_event_report.get("validation_issues")),
            },
            "connected_to": [
                "parser_outputs",
                "cgm_slice_bridge_summary_v1",
                "sensor_genetic_integration_rate_pct",
            ],
        },
        "cgm_slice_bridge_summary_v1": {
            "status": "connected" if cgm_slice_report.get("case_count") else "missing",
            "artifact_path": str(cgm_slice_report_path),
            "proof": {
                "case_count": cgm_slice_report.get("case_count"),
                "eval_success_count": cgm_slice_report.get("eval_success_count"),
                "invalid_case_count": cgm_slice_report.get("invalid_case_count"),
                "threshold_edge_case_ids": _sorted_str_list(
                    cgm_slice_report.get("threshold_edge_case_ids")
                ),
                "parser_failure_type_counts": _as_dict(
                    cgm_slice_report.get("parser_failure_type_counts")
                ),
            },
            "connected_to": [
                "CGMNormalizedEventV1",
                "supported_parser_failure_types",
                "sensor_genetic_integration_rate_pct",
            ],
        },
        "FollowUpTransitionEventV1": {
            "status": "connected"
            if followup_report.get("invalid_case_count") == 0
            else "missing",
            "artifact_path": str(followup_report_path),
            "proof": {
                "case_count": followup_report.get("case_count"),
                "valid_case_count": followup_report.get("valid_case_count"),
                "invalid_case_count": followup_report.get("invalid_case_count"),
                "not_directly_connected_in_this_contract": followup_not_connected,
            },
            "connected_to": [
                "NextActionWorkflowEventV1",
                "weakest_slice_summary",
            ],
        },
        "NextActionWorkflowEventV1": {
            "status": "connected"
            if next_action_branch_fixtures
            and all(
                issue_count == 0 for issue_count in next_action_issue_counts
            )
            else "missing",
            "artifact_path": str(next_action_report_path),
            "proof": {
                "response_status": next_action_report.get("response_status"),
                "next_action": next_action_report.get("next_action"),
                "projected_workflow_state": next_action_report.get("projected_workflow_state"),
                "issue_count": next_action_report.get("issue_count"),
                "branch_fixtures": next_action_branch_fixtures,
            },
            "connected_to": [
                "FollowUpTransitionEventV1",
                "structured_safety_evidence_linkage",
                "weakest_slice_summary",
            ],
        },
        "structured_safety_evidence_linkage": {
            "status": "connected" if safety_report.get("issue_count") == 0 else "missing",
            "artifact_path": str(safety_report_path),
            "proof": {
                "response_status": safety_report.get("response_status"),
                "safety_status": safety_report.get("safety_status"),
                "next_action": safety_report.get("next_action"),
                "rule_count": safety_report.get("rule_count"),
                "reference_backed_rule_count": safety_report.get("reference_backed_rule_count"),
                "fixture_rule_ids": _safety_fixture_rule_ids(safety_report),
                "issue_count": safety_report.get("issue_count"),
            },
            "connected_to": [
                "NextActionWorkflowEventV1",
                "safety_reference_accuracy_pct",
                "weakest_slice_summary",
            ],
        },
    }

    connection_edges = [
        {
            "from": "PROImprovementSummaryV1_shared_event_path",
            "to": "frozen_eval.efficacy_improvement_pp",
            "why": (
                "shared baseline/follow-up PRO event computation provides the proof "
                "surface behind the efficacy KPI path"
            ),
        },
        {
            "from": "PROImprovementSummaryV1_shared_event_path",
            "to": "weakest_slice_summary",
            "why": (
                "shared-event PRO improvement proof explains which weakest family currently "
                "owns the efficacy metric"
            ),
        },
        {
            "from": "file_schema_validation",
            "to": "parser_outputs",
            "why": "accepted aliases and failure examples constrain parser entry formats",
        },
        {
            "from": "parser_outputs",
            "to": "supported_parser_failure_types",
            "why": "normalization notes materialize the supported malformed-input fallback family",
        },
        {
            "from": "parser_outputs",
            "to": "CGMNormalizedEventV1",
            "why": "normalized CGM fields become threshold tags plus eval/replay projections",
        },
        {
            "from": "CGMNormalizedEventV1",
            "to": "cgm_slice_bridge_summary_v1",
            "why": (
                "single-event tags and eval success roll up into slice-level "
                "threshold and failure counts"
            ),
        },
        {
            "from": "cgm_slice_bridge_summary_v1",
            "to": "frozen_eval.sensor_genetic_integration_rate_pct",
            "why": (
                "eval success counts and parser failure families explain the "
                "CGM-side integration bottleneck"
            ),
        },
        {
            "from": "FollowUpTransitionEventV1",
            "to": "weakest_slice_summary",
            "why": (
                "synthetic longitudinal next_action and closed_loop_state "
                "provide dataset-level follow-up proof"
            ),
        },
        {
            "from": "NextActionWorkflowEventV1",
            "to": "FollowUpTransitionEventV1",
            "why": (
                "runtime next_action projection uses the same workflow-state "
                "language audited in follow-up transitions"
            ),
        },
        {
            "from": "structured_safety_evidence_linkage",
            "to": "NextActionWorkflowEventV1",
            "why": (
                "safety blockers and evidence linkage explain why workflow "
                "next_action escalates or stays blocked"
            ),
        },
        {
            "from": "structured_safety_evidence_linkage",
            "to": "frozen_eval.safety_reference_accuracy_pct",
            "why": (
                "rule/evidence linkage provides the proof surface behind the "
                "safety-reference KPI"
            ),
        },
    ]

    structured_safety_evidence_linkage_audit = _build_structured_safety_evidence_linkage_audit(
        required_components=required_components,
        metrics_by_family=metrics_by_family,
        eval_report=eval_report,
        next_action_branch_fixtures=next_action_branch_fixtures,
    )
    weakest_slice_frozen_eval_compatible_audit_path = (
        _build_weakest_slice_frozen_eval_compatible_audit_path(
            required_components=required_components,
            weakest_overall=weakest_overall,
            weakest_sensor_metric=_as_dict(
                weakest_by_metric.get("sensor_genetic_integration_rate_pct")
            ),
            integration_bottleneck=integration_details,
            cgm_slice_connected_flows=cgm_slice_connected_flows,
            followup_not_connected=followup_not_connected,
            structured_safety_evidence_linkage_audit=(
                structured_safety_evidence_linkage_audit
            ),
        )
    )
    remaining_gaps = _build_remaining_gaps(
        parser_report=parser_report,
        followup_not_connected=followup_not_connected,
        next_action_branch_fixtures=next_action_branch_fixtures,
        safety_report=safety_report,
        weakest_overall=weakest_overall,
        weakest_by_metric=weakest_by_metric,
        cgm_slice_connected_flows=cgm_slice_connected_flows,
        structured_safety_evidence_linkage_audit=structured_safety_evidence_linkage_audit,
    )

    connected_component_count = sum(
        1 for item in required_components.values() if item["status"] == "connected"
    )

    return {
        "audit_name": "weakest_slice_frozen_eval_audit_v1",
        "frozen_eval_anchor": {
            "eval_report_path": str(eval_report_path),
            "dataset_path": eval_report.get("dataset_path"),
            "case_count": eval_report.get("case_count"),
            "weakest_category_overall": weakest_overall,
            "sensor_genetic_integration_metric": weakest_by_metric.get(
                "sensor_genetic_integration_rate_pct"
            ),
            "efficacy_metric": weakest_by_metric.get("efficacy_improvement_pp"),
            "safety_reference_metric": weakest_by_metric.get("safety_reference_accuracy_pct"),
            "next_action_metric": weakest_by_metric.get("next_action_accuracy_pct"),
            "integration_bottleneck": {
                "modality": integration_details.get("bottleneck_modality"),
                "rate_pct": integration_details.get("bottleneck_rate_pct"),
                "modality_breakdown": integration_details.get("modality_breakdown"),
            },
        },
        "required_path_components": required_components,
        "structured_safety_evidence_linkage_audit": (
            structured_safety_evidence_linkage_audit
        ),
        "weakest_slice_frozen_eval_compatible_audit_path": (
            weakest_slice_frozen_eval_compatible_audit_path
        ),
        "audit_path_summary": {
            "all_required_components_present": connected_component_count
            == len(required_components),
            "connected_component_count": connected_component_count,
            "missing_component_count": len(required_components) - connected_component_count,
            "frozen_eval_compatible": bool(weakest_slice_summary),
            "connection_edges": connection_edges,
            "remaining_gaps": remaining_gaps,
        },
    }


def write_weakest_slice_frozen_eval_audit_files(
    audit: dict[str, object],
    *,
    output_json_path: str | Path,
    output_md_path: str | Path,
) -> None:
    json_path = Path(output_json_path)
    md_path = Path(output_md_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_weakest_slice_frozen_eval_audit_markdown(audit), encoding="utf-8")


def build_weakest_slice_frozen_eval_summary(
    *,
    audit: dict[str, object],
    audit_path: str | Path,
    eval_report: dict[str, object],
    eval_report_path: str | Path,
) -> dict[str, object]:
    weakest_slice_summary = _as_dict(eval_report.get("weakest_slice_summary"))
    weakest_by_metric = _as_dict(weakest_slice_summary.get("weakest_category_by_metric"))
    overall = _as_dict(weakest_slice_summary.get("weakest_category_overall"))
    category_counts = Counter(
        str(item.get("category"))
        for item in eval_report.get("case_results", [])
        if isinstance(item, dict) and item.get("category") is not None
    )
    metrics_by_family: dict[str, list[str]] = defaultdict(list)
    for metric_name, item in weakest_by_metric.items():
        category = _as_dict(item).get("category")
        if isinstance(category, str):
            metrics_by_family[category].append(metric_name)
    overall_category = overall.get("category")
    if isinstance(overall_category, str):
        metrics_by_family.setdefault(overall_category, [])

    required_components = _as_dict(audit.get("required_path_components"))
    remaining_gaps = _sorted_str_list(
        _as_dict(audit.get("audit_path_summary")).get("remaining_gaps")
    )
    family_summaries: list[dict[str, object]] = []
    still_empty_families: list[str] = []
    sensor_family = _sensor_family(audit)
    workflow_family = _workflow_family(audit)
    pro_family = _pro_family(audit)

    for family in sorted(metrics_by_family):
        weakest_metrics = sorted(metrics_by_family[family])
        mapped_contracts = _contracts_for_family(family=family, weakest_metrics=weakest_metrics)
        connected_contracts = [
            contract_name
            for contract_name in mapped_contracts
            if _as_dict(required_components.get(contract_name)).get("status") == "connected"
        ]
        if mapped_contracts and len(connected_contracts) == len(mapped_contracts):
            coverage_status = "connected"
        elif connected_contracts:
            coverage_status = "partial"
        else:
            coverage_status = "empty"
        if coverage_status == "empty":
            still_empty_families.append(family)

        family_summaries.append(
            {
                "family": family,
                "case_count": category_counts.get(family, 0),
                "weakest_metrics": weakest_metrics,
                "coverage_status": coverage_status,
                "contracts_filled": connected_contracts,
                "contracts_expected_for_current_audit": mapped_contracts,
                "uncovered_metrics": [
                    metric_name
                    for metric_name in weakest_metrics
                    if not _metric_contracts(metric_name)
                ],
                "parser_failure_types": (
                    _parser_failure_summary(required_components)
                    if family == sensor_family
                    else {}
                ),
                "cgm_bridge_summary": (
                    _cgm_bridge_summary(required_components)
                    if family == sensor_family
                    else {}
                ),
                "pro_improvement_path": (
                    _pro_improvement_summary(required_components)
                    if family == pro_family
                    else {}
                ),
                "workflow_safety_linkage": (
                    _workflow_safety_summary(required_components)
                    | {
                        "next_action_workflow_category_join": _workflow_category_join_summary(
                            audit
                        )
                    }
                    if family == workflow_family
                    else {}
                ),
                "structured_safety_evidence_audit": (
                    _family_structured_safety_evidence_summary(
                        family=family,
                        audit=audit,
                    )
                    if family.startswith("safety_")
                    else {}
                ),
                "remaining_gaps": _family_gaps(
                    family=family,
                    remaining_gaps=remaining_gaps,
                    audit=audit,
                ),
            }
        )

    return {
        "summary_name": "weakest_slice_frozen_eval_summary_v1",
        "source_artifacts": {
            "audit_path": str(audit_path),
            "eval_report_path": str(eval_report_path),
        },
        "frozen_eval_anchor": {
            "dataset_path": eval_report.get("dataset_path"),
            "case_count": eval_report.get("case_count"),
            "weakest_category_overall": overall,
            "weakest_category_by_metric": weakest_by_metric,
        },
        "case_family_summaries": family_summaries,
        "readable_summary": {
            "family_contract_matrix": _family_contract_matrix(family_summaries),
            "parser_failure_digest": _readable_parser_failure_digest(family_summaries),
            "cgm_bridge_digest": _readable_cgm_bridge_digest(family_summaries),
            "workflow_safety_digest": _readable_workflow_safety_digest(family_summaries),
            "still_empty_weakest_families": still_empty_families,
        },
        "structured_safety_evidence_completeness": _summary_structured_safety_completeness(
            family_summaries
        ),
        "still_empty_weakest_families": still_empty_families,
        "audit_layer_gap_count": len(remaining_gaps),
        "audit_layer_gaps": remaining_gaps,
    }


def write_weakest_slice_frozen_eval_summary_files(
    summary: dict[str, object],
    *,
    output_json_path: str | Path,
    output_md_path: str | Path,
) -> None:
    json_path = Path(output_json_path)
    md_path = Path(output_md_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_weakest_slice_frozen_eval_summary_markdown(summary), encoding="utf-8")


def render_weakest_slice_frozen_eval_audit_markdown(audit: dict[str, object]) -> str:
    anchor = _as_dict(audit.get("frozen_eval_anchor"))
    overall = _as_dict(anchor.get("weakest_category_overall"))
    sensor_metric = _as_dict(anchor.get("sensor_genetic_integration_metric"))
    efficacy_metric = _as_dict(anchor.get("efficacy_metric"))
    bottleneck = _as_dict(anchor.get("integration_bottleneck"))
    path_summary = _as_dict(audit.get("audit_path_summary"))
    safety_audit = _as_dict(audit.get("structured_safety_evidence_linkage_audit"))
    compatible_path = _as_dict(
        audit.get("weakest_slice_frozen_eval_compatible_audit_path")
    )
    lines = [
        "# weakest slice frozen eval audit v1",
        "",
        "## frozen eval anchor",
        "",
        f"- eval_report_path: {anchor.get('eval_report_path')}",
        f"- dataset_path: {anchor.get('dataset_path')}",
        f"- case_count: {anchor.get('case_count')}",
        f"- weakest_category_overall: {overall.get('category')}",
        f"- weakest_overall_metrics: {overall.get('metrics')}",
        f"- weakest_sensor_genetic_metric_category: {sensor_metric.get('category')}",
        f"- weakest_sensor_genetic_metric_score: {sensor_metric.get('score')}",
        f"- weakest_efficacy_metric_category: {efficacy_metric.get('category')}",
        f"- weakest_efficacy_metric_score: {efficacy_metric.get('score')}",
        f"- integration_bottleneck_modality: {bottleneck.get('modality')}",
        f"- integration_bottleneck_rate_pct: {bottleneck.get('rate_pct')}",
        "",
        "## required path components",
        "",
        "| component | status | artifact_path | proof | connected_to |",
        "| --- | --- | --- | --- | --- |",
    ]

    for component_name, item in _as_dict(audit.get("required_path_components")).items():
        lines.append(
            "| "
            f"{component_name} | {item['status']} | {item['artifact_path']} | "
            f"`{item['proof']}` | `{item['connected_to']}` |"
        )

    lines.extend(["", "## audit path summary", ""])
    lines.append(
        f"- all_required_components_present: {path_summary.get('all_required_components_present')}"
    )
    lines.append(f"- frozen_eval_compatible: {path_summary.get('frozen_eval_compatible')}")
    lines.append(f"- connected_component_count: {path_summary.get('connected_component_count')}")
    lines.append(f"- missing_component_count: {path_summary.get('missing_component_count')}")
    lines.extend(["", "## structured safety evidence completeness", ""])
    lines.append(
        f"- weakest_safety_families: `{safety_audit.get('weakest_safety_families', [])}`"
    )
    lines.append(
        "- families_with_structured_safety_path: "
        f"`{safety_audit.get('families_with_structured_safety_path', [])}`"
    )
    lines.append(
        "- families_missing_structured_safety_path: "
        f"`{safety_audit.get('families_missing_structured_safety_path', [])}`"
    )
    lines.append(
        "- linkage_path: "
        f"`{safety_audit.get('linkage_path', [])}`"
    )
    lines.append(
        "- reference_linkage_status: "
        f"`{safety_audit.get('reference_linkage_status')}`"
    )
    lines.append(
        "- reference_linkage_completeness: "
        f"`{safety_audit.get('reference_linkage_completeness', {})}`"
    )
    lines.append(
        "- next_action_workflow_category_join: "
        f"`{safety_audit.get('next_action_workflow_category_join', {})}`"
    )
    lines.append(
        "- frozen_eval_category_join: "
        f"`{safety_audit.get('frozen_eval_category_join', {})}`"
    )
    lines.extend(["", "## weakest-slice compatible audit path", ""])
    lines.append(
        f"- path_name: {compatible_path.get('path_name')}"
    )
    lines.append(
        f"- path_status: {compatible_path.get('path_status')}"
    )
    lines.append(
        f"- frozen_eval_compatible: {compatible_path.get('frozen_eval_compatible')}"
    )
    lines.append(
        "- sensor_genetic_anchor: "
        f"`{compatible_path.get('sensor_genetic_anchor', {})}`"
    )
    lines.append(
        "- weakest_overall_anchor: "
        f"`{compatible_path.get('weakest_overall_anchor', {})}`"
    )
    lines.append(
        f"- connected_edge_count: {compatible_path.get('connected_edge_count')}"
    )
    lines.append(
        f"- bridge_only_edge_count: {compatible_path.get('bridge_only_edge_count')}"
    )
    lines.append(
        f"- missing_edge_count: {compatible_path.get('missing_edge_count')}"
    )
    lines.extend(
        [
            "",
            "| from | to | status | edge_type | evidence |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for edge in compatible_path.get("path_edges", []):
        lines.append(
            "| "
            f"{edge.get('from')} | {edge.get('to')} | {edge.get('status')} | "
            f"{edge.get('edge_type')} | `{edge.get('evidence', {})}` |"
        )
    lines.extend(["", "## connection edges", ""])
    for edge in path_summary.get("connection_edges", []):
        lines.append(f"- {edge['from']} -> {edge['to']}: {edge['why']}")
    lines.extend(["", "## remaining gaps", ""])
    for gap in path_summary.get("remaining_gaps", []):
        lines.append(f"- {gap}")
    return "\n".join(lines) + "\n"


def render_weakest_slice_frozen_eval_summary_markdown(summary: dict[str, object]) -> str:
    anchor = _as_dict(summary.get("frozen_eval_anchor"))
    overall = _as_dict(anchor.get("weakest_category_overall"))
    efficacy_metric_category = _as_dict(anchor.get("weakest_category_by_metric")).get(
        "efficacy_improvement_pp",
        {},
    )
    readable_summary = _as_dict(summary.get("readable_summary"))
    safety_completeness = _as_dict(summary.get("structured_safety_evidence_completeness"))
    lines = [
        "# weakest slice frozen eval summary v1",
        "",
        "## anchor",
        "",
        f"- audit_path: {summary['source_artifacts']['audit_path']}",
        f"- eval_report_path: {summary['source_artifacts']['eval_report_path']}",
        f"- dataset_path: {anchor.get('dataset_path')}",
        f"- case_count: {anchor.get('case_count')}",
        f"- weakest_category_overall: {overall.get('category')}",
        f"- weakest_overall_metrics: {overall.get('metrics')}",
        f"- weakest_efficacy_metric_category: {_as_dict(efficacy_metric_category).get('category')}",
        "- structured_safety_linked_families: "
        f"{safety_completeness.get('linked_families', [])}",
        "- structured_safety_missing_families: "
        f"{safety_completeness.get('missing_families', [])}",
        f"- still_empty_weakest_families: {summary.get('still_empty_weakest_families')}",
        "",
        "## readable digest",
        "",
        "| family | case_count | coverage_status | contracts_filled | contracts_missing |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in readable_summary.get("family_contract_matrix", []):
        lines.append(
            "| "
            f"{item['family']} | {item['case_count']} | {item['coverage_status']} | "
            f"`{item['contracts_filled']}` | `{item['contracts_missing']}` |"
        )

    lines.extend(["", "## parser and cgm digest", ""])
    lines.append(
        f"- parser_failure_digest: `{readable_summary.get('parser_failure_digest', {})}`"
    )
    lines.append(
        f"- cgm_bridge_digest: `{readable_summary.get('cgm_bridge_digest', {})}`"
    )
    lines.extend(["", "## workflow and safety digest", ""])
    lines.append(
        "- workflow_safety_digest: "
        f"`{readable_summary.get('workflow_safety_digest', {})}`"
    )
    lines.append(
        "- still_empty_weakest_families_digest: "
        f"`{readable_summary.get('still_empty_weakest_families', [])}`"
    )
    lines.extend([
        "",
        "## case family coverage",
        "",
        "| family | case_count | weakest_metrics | coverage_status | contracts_filled |",
        "| --- | --- | --- | --- | --- |",
    ])
    for item in summary.get("case_family_summaries", []):
        lines.append(
            "| "
            f"{item['family']} | {item['case_count']} | `{item['weakest_metrics']}` | "
            f"{item['coverage_status']} | `{item['contracts_filled']}` |"
        )

    lines.extend(["", "## structured safety evidence completeness", ""])
    lines.append(
        f"- linked_family_count: {safety_completeness.get('linked_family_count')}"
    )
    lines.append(
        f"- missing_family_count: {safety_completeness.get('missing_family_count')}"
    )
    lines.append(
        f"- linked_case_count: {safety_completeness.get('linked_case_count')}"
    )
    lines.append(
        f"- missing_case_count: {safety_completeness.get('missing_case_count')}"
    )
    lines.append(
        "- reference_linkage_status_counts: "
        f"`{safety_completeness.get('reference_linkage_status_counts', {})}`"
    )
    lines.append(
        "- linked_families: "
        f"`{safety_completeness.get('linked_families', [])}`"
    )
    lines.append(
        "- missing_families: "
        f"`{safety_completeness.get('missing_families', [])}`"
    )

    lines.extend(["", "## family details", ""])
    for item in summary.get("case_family_summaries", []):
        lines.append(f"### {item['family']}")
        lines.append(f"- case_count: {item['case_count']}")
        lines.append(f"- weakest_metrics: `{item['weakest_metrics']}`")
        lines.append(f"- coverage_status: `{item['coverage_status']}`")
        lines.append(
            "- contracts_expected_for_current_audit: "
            f"`{item['contracts_expected_for_current_audit']}`"
        )
        lines.append(f"- contracts_filled: `{item['contracts_filled']}`")
        if item["parser_failure_types"]:
            lines.append(f"- parser_failure_types: `{item['parser_failure_types']}`")
        if item["cgm_bridge_summary"]:
            lines.append(f"- cgm_bridge_summary: `{item['cgm_bridge_summary']}`")
        if item["pro_improvement_path"]:
            lines.append(f"- pro_improvement_path: `{item['pro_improvement_path']}`")
        if item["workflow_safety_linkage"]:
            lines.append(f"- workflow_safety_linkage: `{item['workflow_safety_linkage']}`")
        if item.get("structured_safety_evidence_audit"):
            lines.append(
                "- structured_safety_evidence_audit: "
                f"`{item['structured_safety_evidence_audit']}`"
            )
        lines.append(f"- remaining_gaps: `{item['remaining_gaps']}`")
        lines.append("")

    lines.extend(["## audit layer gaps", ""])
    for gap in summary.get("audit_layer_gaps", []):
        lines.append(f"- {gap}")
    return "\n".join(lines) + "\n"


def _build_remaining_gaps(
    *,
    parser_report: dict[str, object],
    followup_not_connected: list[str],
    next_action_branch_fixtures: list[dict[str, object]],
    safety_report: dict[str, object],
    weakest_overall: dict[str, object],
    weakest_by_metric: dict[str, object],
    cgm_slice_connected_flows: dict[str, object],
    structured_safety_evidence_linkage_audit: dict[str, object],
) -> list[str]:
    gaps: list[str] = []
    parser_cases_path = str(parser_report.get("cases_json_path"))
    if parser_cases_path.startswith("data/samples/"):
        gaps.append(
            "parser and CGM bridge proofs are sample-fixture based, so they do not yet join to "
            "frozen-eval case_ids one by one."
        )
    if "sensor_genetic_normalized_event" in followup_not_connected:
        gaps.append(
            "FollowUpTransitionEventV1 still declares sensor_genetic_normalized_event as "
            "not directly connected inside its own contract."
        )
    next_action_category_join = _as_dict(
        structured_safety_evidence_linkage_audit.get("next_action_workflow_category_join")
    )
    if any(
        str(branch.get("request_fixture_path")).startswith("data\\samples")
        or str(branch.get("request_fixture_path")).startswith("data/samples")
        for branch in next_action_branch_fixtures
    ):
        if next_action_category_join.get("join_status") != "connected":
            gaps.append(
                "NextActionWorkflowEventV1 proof is still request-fixture scoped rather than a "
                "category-wide frozen-eval aggregation."
            )
        elif int(next_action_category_join.get("matched_case_count", 0)) < int(
            next_action_category_join.get("category_case_count", 0)
        ):
            gaps.append(
                "NextActionWorkflowEventV1 now joins weakest safety_blocked cases at the "
                "category level, but the current request fixture only covers part of the "
                "observed weakest-slice response_status/next_action distribution."
            )
    safety_request_path = str(safety_report.get("request_fixture_path"))
    safety_category_join = _as_dict(
        structured_safety_evidence_linkage_audit.get("frozen_eval_category_join")
    )
    if safety_request_path.startswith("data\\samples") or safety_request_path.startswith(
        "data/samples"
    ):
        if safety_category_join.get("join_status") != "connected":
            gaps.append(
                "Structured safety evidence linkage proof is still request-fixture scoped rather "
                "than joined across weakest-slice frozen-eval cases."
            )
        elif safety_category_join.get("fixture_rule_overlap_count", 0) != safety_category_join.get(
            "fixture_rule_count",
            0,
        ):
            gaps.append(
                "Structured safety evidence linkage now joins weakest safety_blocked cases at the "
                "category level, but the current request-fixture rule bundle still only partially "
                "overlaps the observed weakest-slice rule families."
            )
    if (
        weakest_overall.get("category")
        != _as_dict(weakest_by_metric.get("sensor_genetic_integration_rate_pct")).get("category")
    ):
        gaps.append(
            "The overall weakest frozen-eval category and the sensor/genetic weakest metric "
            "category are different, so this audit layer still bridges two weakest-slice anchors."
        )
    if "cgm_weakest_slice_audit" not in cgm_slice_connected_flows:
        gaps.append(
            "cgm_slice_bridge_summary_v1 is missing its explicit cgm_weakest_slice_audit flow."
        )
    return gaps


def _family_contract_matrix(
    family_summaries: list[dict[str, object]],
) -> list[dict[str, object]]:
    matrix: list[dict[str, object]] = []
    for item in family_summaries:
        expected = _sorted_str_list(item.get("contracts_expected_for_current_audit"))
        filled = _sorted_str_list(item.get("contracts_filled"))
        matrix.append(
            {
                "family": item.get("family"),
                "case_count": item.get("case_count"),
                "coverage_status": item.get("coverage_status"),
                "contracts_filled": filled,
                "contracts_missing": sorted(set(expected) - set(filled)),
            }
        )
    return matrix


def _readable_parser_failure_digest(
    family_summaries: list[dict[str, object]],
) -> dict[str, object]:
    for item in family_summaries:
        parser_failure_types = _as_dict(item.get("parser_failure_types"))
        if parser_failure_types:
            return {
                "family": item.get("family"),
                "combined_failure_type_count": parser_failure_types.get(
                    "combined_failure_type_count"
                ),
                "taxonomy_stage_counts": _as_dict(
                    parser_failure_types.get("taxonomy_stage_counts")
                ),
                "taxonomy_modality_counts": _as_dict(
                    parser_failure_types.get("taxonomy_modality_counts")
                ),
                "taxonomy_family_counts": _as_dict(
                    parser_failure_types.get("taxonomy_family_counts")
                ),
                "taxonomy_field_counts": _as_dict(
                    parser_failure_types.get("taxonomy_field_counts")
                ),
                "taxonomy_field_ambiguity_count": parser_failure_types.get(
                    "taxonomy_field_ambiguity_count"
                ),
                "parser_supported_failure_types": _sorted_str_list(
                    parser_failure_types.get("parser_supported_failure_types")
                ),
                "schema_failure_type_examples": _sorted_str_list(
                    parser_failure_types.get("schema_failure_type_examples")
                ),
            }
    return {}


def _readable_cgm_bridge_digest(
    family_summaries: list[dict[str, object]],
) -> dict[str, object]:
    for item in family_summaries:
        cgm_bridge_summary = _as_dict(item.get("cgm_bridge_summary"))
        if cgm_bridge_summary:
            return {"family": item.get("family")} | cgm_bridge_summary
    return {}


def _readable_workflow_safety_digest(
    family_summaries: list[dict[str, object]],
) -> dict[str, object]:
    for item in family_summaries:
        workflow_safety_linkage = _as_dict(item.get("workflow_safety_linkage"))
        structured_safety = _as_dict(item.get("structured_safety_evidence_audit"))
        if workflow_safety_linkage or structured_safety:
            next_action_join = _as_dict(
                workflow_safety_linkage.get("next_action_workflow_category_join")
            )
            frozen_eval_category_join = _as_dict(
                structured_safety.get("frozen_eval_category_join")
            )
            return {
                "family": item.get("family"),
                "followup_not_directly_connected": _sorted_str_list(
                    _as_dict(workflow_safety_linkage.get("followup_transition")).get(
                        "not_directly_connected_in_this_contract"
                    )
                ),
                "next_action_branch_fixture_count": len(
                    _as_list(
                        _as_dict(workflow_safety_linkage.get("next_action_workflow")).get(
                            "branch_fixtures"
                        )
                    )
                ),
                "next_action_category_join_coverage_pct": next_action_join.get(
                    "coverage_pct"
                ),
                "safety_reference_linkage_status": structured_safety.get(
                    "reference_linkage_status"
                ),
                "safety_rule_overlap_count": frozen_eval_category_join.get(
                    "fixture_rule_overlap_count"
                ),
                "safety_rule_count": frozen_eval_category_join.get("fixture_rule_count"),
            }
    return {}


def _build_weakest_slice_frozen_eval_compatible_audit_path(
    *,
    required_components: dict[str, object],
    weakest_overall: dict[str, object],
    weakest_sensor_metric: dict[str, object],
    integration_bottleneck: dict[str, object],
    cgm_slice_connected_flows: dict[str, object],
    followup_not_connected: list[str],
    structured_safety_evidence_linkage_audit: dict[str, object],
) -> dict[str, object]:
    safety_category_join = _as_dict(
        structured_safety_evidence_linkage_audit.get("frozen_eval_category_join")
    )
    next_action_category_join = _as_dict(
        structured_safety_evidence_linkage_audit.get("next_action_workflow_category_join")
    )

    path_nodes = [
        _path_node(required_components, "file_schema_validation"),
        _path_node(required_components, "parser_outputs"),
        _path_node(required_components, "supported_parser_failure_types"),
        _path_node(required_components, "CGMNormalizedEventV1"),
        _path_node(required_components, "cgm_slice_bridge_summary_v1"),
        _path_node(required_components, "FollowUpTransitionEventV1"),
        _path_node(required_components, "NextActionWorkflowEventV1"),
        _path_node(required_components, "structured_safety_evidence_linkage"),
        {
            "name": "weakest_slice_summary",
            "status": "connected" if weakest_overall else "missing",
            "artifact_path": "frozen_eval.eval_report.weakest_slice_summary",
        },
    ]

    path_edges = [
        _path_edge(
            "file_schema_validation",
            "parser_outputs",
            source_status=_component_status(required_components, "file_schema_validation"),
            target_status=_component_status(required_components, "parser_outputs"),
            evidence={
                "connection_basis": "schema fixtures constrain parser entry formats",
            },
        ),
        _path_edge(
            "parser_outputs",
            "supported_parser_failure_types",
            source_status=_component_status(required_components, "parser_outputs"),
            target_status=_component_status(
                required_components,
                "supported_parser_failure_types",
            ),
            evidence={
                "connection_basis": (
                    "parser normalization notes materialize supported failure families"
                ),
            },
        ),
        _path_edge(
            "supported_parser_failure_types",
            "CGMNormalizedEventV1",
            source_status=_component_status(
                required_components,
                "supported_parser_failure_types",
            ),
            target_status=_component_status(required_components, "CGMNormalizedEventV1"),
            evidence={
                "connection_basis": (
                    "supported malformed-input families explain normalized CGM event limits"
                ),
            },
        ),
        _path_edge(
            "CGMNormalizedEventV1",
            "cgm_slice_bridge_summary_v1",
            source_status=_component_status(required_components, "CGMNormalizedEventV1"),
            target_status=_component_status(
                required_components,
                "cgm_slice_bridge_summary_v1",
            ),
            evidence={
                "explicit_flow_present": "cgm_weakest_slice_audit"
                in cgm_slice_connected_flows,
            },
        ),
        _path_edge(
            "cgm_slice_bridge_summary_v1",
            "FollowUpTransitionEventV1",
            source_status=_component_status(
                required_components,
                "cgm_slice_bridge_summary_v1",
            ),
            target_status=_component_status(required_components, "FollowUpTransitionEventV1"),
            bridge_only="sensor_genetic_normalized_event" in followup_not_connected,
            edge_type="cross_contract_bridge",
            evidence={
                "not_directly_connected_in_this_contract": followup_not_connected,
            },
        ),
        _path_edge(
            "FollowUpTransitionEventV1",
            "NextActionWorkflowEventV1",
            source_status=_component_status(required_components, "FollowUpTransitionEventV1"),
            target_status=_component_status(required_components, "NextActionWorkflowEventV1"),
            evidence={
                "category_join_status": next_action_category_join.get("join_status"),
                "category_coverage_pct": next_action_category_join.get("coverage_pct"),
            },
        ),
        _path_edge(
            "NextActionWorkflowEventV1",
            "structured_safety_evidence_linkage",
            source_status=_component_status(required_components, "NextActionWorkflowEventV1"),
            target_status=_component_status(
                required_components,
                "structured_safety_evidence_linkage",
            ),
            evidence={
                "safety_family_join_status": safety_category_join.get("join_status"),
                "fixture_rule_overlap_count": safety_category_join.get(
                    "fixture_rule_overlap_count"
                ),
                "fixture_rule_count": safety_category_join.get("fixture_rule_count"),
            },
        ),
        _path_edge(
            "structured_safety_evidence_linkage",
            "weakest_slice_summary",
            source_status=_component_status(
                required_components,
                "structured_safety_evidence_linkage",
            ),
            target_status="connected" if weakest_overall else "missing",
            evidence={
                "overall_weakest_category": weakest_overall.get("category"),
                "safety_category_join_status": safety_category_join.get("join_status"),
            },
        ),
    ]

    connected_edge_count = sum(
        1 for edge in path_edges if edge.get("status") == "connected"
    )
    bridge_only_edge_count = sum(
        1 for edge in path_edges if edge.get("status") == "bridge_only"
    )
    missing_edge_count = sum(1 for edge in path_edges if edge.get("status") == "missing")
    if missing_edge_count > 0:
        path_status = "missing_links"
    elif bridge_only_edge_count > 0:
        path_status = "bridge_connected_with_direct_gap"
    else:
        path_status = "directly_connected"

    return {
        "path_name": "parser_to_cgm_to_workflow_to_safety_weakest_slice_path_v1",
        "path_status": path_status,
        "frozen_eval_compatible": bool(weakest_overall),
        "sensor_genetic_anchor": {
            "metric": "sensor_genetic_integration_rate_pct",
            "category": weakest_sensor_metric.get("category"),
            "score": weakest_sensor_metric.get("score"),
            "bottleneck_modality": integration_bottleneck.get("bottleneck_modality"),
            "bottleneck_rate_pct": integration_bottleneck.get("bottleneck_rate_pct"),
        },
        "weakest_overall_anchor": {
            "category": weakest_overall.get("category"),
            "metrics": weakest_overall.get("metrics"),
            "case_count": weakest_overall.get("case_count"),
        },
        "path_nodes": path_nodes,
        "path_edges": path_edges,
        "connected_edge_count": connected_edge_count,
        "bridge_only_edge_count": bridge_only_edge_count,
        "missing_edge_count": missing_edge_count,
        "direct_gap_edges": [
            edge for edge in path_edges if edge.get("status") != "connected"
        ],
    }


def _path_node(
    required_components: dict[str, object],
    component_name: str,
) -> dict[str, object]:
    component = _as_dict(required_components.get(component_name))
    return {
        "name": component_name,
        "status": component.get("status"),
        "artifact_path": component.get("artifact_path"),
    }


def _path_edge(
    source_name: str,
    target_name: str,
    *,
    source_status: str,
    target_status: str,
    evidence: dict[str, object],
    bridge_only: bool = False,
    edge_type: str = "contract_edge",
) -> dict[str, object]:
    if source_status != "connected" or target_status != "connected":
        status = "missing"
    elif bridge_only:
        status = "bridge_only"
    else:
        status = "connected"
    return {
        "from": source_name,
        "to": target_name,
        "status": status,
        "edge_type": edge_type,
        "evidence": evidence,
    }


def _component_status(
    required_components: dict[str, object],
    component_name: str,
) -> str:
    return str(_as_dict(required_components.get(component_name)).get("status") or "missing")


def validate_structured_safety_evidence_linkage_audit(
    audit: dict[str, object],
) -> list[str]:
    safety_audit = _as_dict(audit.get("structured_safety_evidence_linkage_audit"))
    issues: list[str] = []

    weakest_families = _sorted_str_list(safety_audit.get("weakest_safety_families"))
    linked_families = _sorted_str_list(
        safety_audit.get("families_with_structured_safety_path")
    )
    missing_families = _sorted_str_list(
        safety_audit.get("families_missing_structured_safety_path")
    )

    if sorted(set(linked_families) | set(missing_families)) != weakest_families:
        issues.append("weakest_safety_family_partition_mismatch")
    if set(linked_families) & set(missing_families):
        issues.append("weakest_safety_family_overlap")

    completeness = _as_dict(safety_audit.get("reference_linkage_completeness"))
    rule_count = completeness.get("rule_count")
    reference_backed_rule_count = completeness.get("reference_backed_rule_count")
    linkage_status = safety_audit.get("reference_linkage_status")

    if linkage_status == "reference_backed" and not reference_backed_rule_count:
        issues.append("reference_backed_status_without_reference_backed_rule")
    if linkage_status == "deterministic_only" and not rule_count:
        issues.append("deterministic_only_status_without_rules")
    if not _sorted_str_list(safety_audit.get("linkage_path")):
        issues.append("missing_structured_safety_linkage_path")

    frozen_eval_category_join = _as_dict(safety_audit.get("frozen_eval_category_join"))
    next_action_category_join = _as_dict(
        safety_audit.get("next_action_workflow_category_join")
    )
    if "safety_blocked" in linked_families:
        if frozen_eval_category_join.get("join_status") != "connected":
            issues.append("missing_safety_blocked_category_join")
        elif int(frozen_eval_category_join.get("category_case_count", 0)) <= 0:
            issues.append("empty_safety_blocked_category_join")
        elif sum(_as_dict(frozen_eval_category_join.get("actual_status_counts")).values()) != int(
            frozen_eval_category_join.get("category_case_count", 0)
        ):
            issues.append("safety_blocked_status_count_mismatch")
        elif sum(
            _as_dict(frozen_eval_category_join.get("actual_next_action_counts")).values()
        ) != int(frozen_eval_category_join.get("category_case_count", 0)):
            issues.append("safety_blocked_next_action_count_mismatch")
        if next_action_category_join.get("join_status") != "connected":
            issues.append("missing_safety_blocked_next_action_category_join")
        elif int(next_action_category_join.get("category_case_count", 0)) <= 0:
            issues.append("empty_safety_blocked_next_action_category_join")
        elif sum(
            _as_dict(next_action_category_join.get("actual_status_counts")).values()
        ) != int(next_action_category_join.get("category_case_count", 0)):
            issues.append("safety_blocked_next_action_status_count_mismatch")
        elif sum(
            _as_dict(next_action_category_join.get("actual_next_action_counts")).values()
        ) != int(next_action_category_join.get("category_case_count", 0)):
            issues.append("safety_blocked_next_action_action_count_mismatch")
        elif int(next_action_category_join.get("matched_case_count", 0)) > int(
            next_action_category_join.get("category_case_count", 0)
        ):
            issues.append("safety_blocked_next_action_match_count_overflow")

    return issues


def _contracts_for_family(*, family: str, weakest_metrics: list[str]) -> list[str]:
    contracts: list[str] = []
    for metric_name in weakest_metrics:
        for contract_name in _metric_contracts(metric_name):
            if contract_name not in contracts:
                contracts.append(contract_name)
    if not contracts and family == "safety_blocked":
        contracts.extend(
            [
                "FollowUpTransitionEventV1",
                "NextActionWorkflowEventV1",
                "structured_safety_evidence_linkage",
            ]
        )
    return contracts


def _metric_contracts(metric_name: str) -> list[str]:
    if metric_name == "efficacy_improvement_pp":
        return ["PROImprovementSummaryV1_shared_event_path"]
    if metric_name == "sensor_genetic_integration_rate_pct":
        return [
            "parser_outputs",
            "file_schema_validation",
            "supported_parser_failure_types",
            "CGMNormalizedEventV1",
            "cgm_slice_bridge_summary_v1",
        ]
    if metric_name in {
        "next_action_accuracy_pct",
        "explanation_quality_accuracy_pct",
        "safety_reference_accuracy_pct",
    }:
        return [
            "FollowUpTransitionEventV1",
            "NextActionWorkflowEventV1",
            "structured_safety_evidence_linkage",
        ]
    return []


def _metrics_by_family(
    weakest_by_metric: dict[str, object],
    weakest_overall: dict[str, object],
) -> dict[str, list[str]]:
    metrics_by_family: dict[str, list[str]] = defaultdict(list)
    for metric_name, item in weakest_by_metric.items():
        category = _as_dict(item).get("category")
        if isinstance(category, str):
            metrics_by_family[category].append(metric_name)
    overall_category = weakest_overall.get("category")
    if isinstance(overall_category, str):
        metrics_by_family.setdefault(overall_category, [])
    return {family: sorted(metrics) for family, metrics in metrics_by_family.items()}


def _sensor_family(audit: dict[str, object]) -> str | None:
    anchor = _as_dict(audit.get("frozen_eval_anchor"))
    metric = _as_dict(anchor.get("sensor_genetic_integration_metric"))
    category = metric.get("category")
    return category if isinstance(category, str) else None


def _pro_family(audit: dict[str, object]) -> str | None:
    anchor = _as_dict(audit.get("frozen_eval_anchor"))
    metric = _as_dict(anchor.get("efficacy_metric"))
    category = metric.get("category")
    return category if isinstance(category, str) else None


def _workflow_family(audit: dict[str, object]) -> str | None:
    anchor = _as_dict(audit.get("frozen_eval_anchor"))
    overall = _as_dict(anchor.get("weakest_category_overall"))
    category = overall.get("category")
    return category if isinstance(category, str) else None


def _parser_failure_summary(required_components: dict[str, object]) -> dict[str, object]:
    component = _as_dict(required_components.get("supported_parser_failure_types"))
    proof = _as_dict(component.get("proof"))
    return {
        "failure_contract_version": proof.get("failure_contract_version"),
        "parser_supported_failure_types": _sorted_str_list(
            proof.get("parser_supported_failure_types")
        ),
        "parser_supported_failure_taxonomy": _as_list(
            proof.get("parser_supported_failure_taxonomy")
        ),
        "schema_failure_type_examples": _sorted_str_list(
            proof.get("schema_failure_type_examples")
        ),
        "schema_failure_type_taxonomy": _as_list(
            proof.get("schema_failure_type_taxonomy")
        ),
        "combined_failure_type_count": proof.get("combined_failure_type_count"),
        "taxonomy_stage_counts": _as_dict(proof.get("taxonomy_stage_counts")),
        "taxonomy_modality_counts": _as_dict(proof.get("taxonomy_modality_counts")),
        "taxonomy_family_counts": _as_dict(proof.get("taxonomy_family_counts")),
        "taxonomy_field_counts": _as_dict(proof.get("taxonomy_field_counts")),
        "taxonomy_ambiguity_count": proof.get("taxonomy_ambiguity_count"),
        "taxonomy_field_ambiguity_count": proof.get("taxonomy_field_ambiguity_count"),
    }


def _cgm_bridge_summary(required_components: dict[str, object]) -> dict[str, object]:
    event_component = _as_dict(required_components.get("CGMNormalizedEventV1"))
    slice_component = _as_dict(required_components.get("cgm_slice_bridge_summary_v1"))
    event_proof = _as_dict(event_component.get("proof"))
    slice_proof = _as_dict(slice_component.get("proof"))
    return {
        "threshold_tags": _sorted_str_list(event_proof.get("threshold_tags")),
        "eval_attempted": event_proof.get("eval_attempted"),
        "eval_success": event_proof.get("eval_success"),
        "slice_case_count": slice_proof.get("case_count"),
        "slice_eval_success_count": slice_proof.get("eval_success_count"),
        "threshold_edge_case_ids": _sorted_str_list(slice_proof.get("threshold_edge_case_ids")),
        "parser_failure_type_counts": _as_dict(slice_proof.get("parser_failure_type_counts")),
    }


def _pro_improvement_summary(required_components: dict[str, object]) -> dict[str, object]:
    component = _as_dict(required_components.get("PROImprovementSummaryV1_shared_event_path"))
    proof = _as_dict(component.get("proof"))
    return {
        "shared_event_schema_version": proof.get("shared_event_schema_version"),
        "shared_event_adapter": proof.get("shared_event_adapter"),
        "shared_event_unifier": proof.get("shared_event_unifier"),
        "shared_event_validator": proof.get("shared_event_validator"),
        "single_path_status": _as_dict(proof.get("single_path_status")),
        "shared_event_path_proof": _as_dict(proof.get("shared_event_path_proof")),
        "synthetic_dataset_summary": _as_dict(proof.get("synthetic_dataset_summary")),
    }


def _workflow_safety_summary(required_components: dict[str, object]) -> dict[str, object]:
    followup_proof = _as_dict(
        _as_dict(required_components.get("FollowUpTransitionEventV1")).get("proof")
    )
    next_action_proof = _as_dict(
        _as_dict(required_components.get("NextActionWorkflowEventV1")).get("proof")
    )
    safety_proof = _as_dict(
        _as_dict(required_components.get("structured_safety_evidence_linkage")).get("proof")
    )
    return {
        "followup_transition": {
            "case_count": followup_proof.get("case_count"),
            "valid_case_count": followup_proof.get("valid_case_count"),
            "not_directly_connected_in_this_contract": _sorted_str_list(
                followup_proof.get("not_directly_connected_in_this_contract")
            ),
        },
        "next_action_workflow": {
            "response_status": next_action_proof.get("response_status"),
            "next_action": next_action_proof.get("next_action"),
            "projected_workflow_state": next_action_proof.get("projected_workflow_state"),
            "issue_count": next_action_proof.get("issue_count"),
            "branch_fixtures": _as_list(next_action_proof.get("branch_fixtures")),
        },
        "structured_safety_evidence": {
            "response_status": safety_proof.get("response_status"),
            "safety_status": safety_proof.get("safety_status"),
            "next_action": safety_proof.get("next_action"),
            "rule_count": safety_proof.get("rule_count"),
            "reference_backed_rule_count": safety_proof.get("reference_backed_rule_count"),
            "issue_count": safety_proof.get("issue_count"),
        },
    }


def _workflow_category_join_summary(audit: dict[str, object]) -> dict[str, object]:
    safety_audit = _as_dict(audit.get("structured_safety_evidence_linkage_audit"))
    return _as_dict(safety_audit.get("next_action_workflow_category_join"))


def _build_structured_safety_evidence_linkage_audit(
    *,
    required_components: dict[str, object],
    metrics_by_family: dict[str, list[str]],
    eval_report: dict[str, object],
    next_action_branch_fixtures: list[dict[str, object]],
) -> dict[str, object]:
    safety_component = _as_dict(required_components.get("structured_safety_evidence_linkage"))
    safety_proof = _as_dict(safety_component.get("proof"))
    next_action_component = _as_dict(required_components.get("NextActionWorkflowEventV1"))
    next_action_proof = _as_dict(next_action_component.get("proof"))
    weakest_safety_families = sorted(
        family for family in metrics_by_family if family.startswith("safety_")
    )
    linked_families = [
        family
        for family in weakest_safety_families
        if "structured_safety_evidence_linkage"
        in _contracts_for_family(family=family, weakest_metrics=metrics_by_family.get(family, []))
    ]
    missing_families = [
        family for family in weakest_safety_families if family not in linked_families
    ]
    rule_count = safety_proof.get("rule_count")
    reference_backed_rule_count = safety_proof.get("reference_backed_rule_count")
    issue_count = safety_proof.get("issue_count")

    if safety_component.get("status") != "connected":
        reference_linkage_status = "missing"
    elif reference_backed_rule_count:
        reference_linkage_status = "reference_backed"
    else:
        reference_linkage_status = "deterministic_only"

    reference_coverage_pct = 0.0
    if (
        isinstance(rule_count, int)
        and rule_count > 0
        and isinstance(reference_backed_rule_count, int)
    ):
        reference_coverage_pct = (reference_backed_rule_count / rule_count) * 100.0

    frozen_eval_category_join = _build_frozen_eval_safety_family_join(
        eval_report=eval_report,
        family="safety_blocked",
        safety_proof=safety_proof,
        next_action_proof=next_action_proof,
    )
    next_action_workflow_category_join = _build_frozen_eval_next_action_family_join(
        eval_report=eval_report,
        family="safety_blocked",
        next_action_branch_fixtures=next_action_branch_fixtures,
    )

    return {
        "weakest_safety_families": weakest_safety_families,
        "families_with_structured_safety_path": linked_families,
        "families_missing_structured_safety_path": missing_families,
        "linkage_path": [
            "structured_safety_evidence_linkage",
            "NextActionWorkflowEventV1",
            "FollowUpTransitionEventV1",
            "weakest_slice_summary",
            "frozen_eval.safety_reference_accuracy_pct",
        ],
        "reference_linkage_status": reference_linkage_status,
        "reference_linkage_completeness": {
            "rule_count": rule_count,
            "reference_backed_rule_count": reference_backed_rule_count,
            "reference_coverage_pct": reference_coverage_pct,
            "issue_count": issue_count,
        },
        "next_action_workflow_category_join": next_action_workflow_category_join,
        "frozen_eval_category_join": frozen_eval_category_join,
    }


def _family_structured_safety_evidence_summary(
    *,
    family: str,
    audit: dict[str, object],
) -> dict[str, object]:
    safety_audit = _as_dict(audit.get("structured_safety_evidence_linkage_audit"))
    linked_families = _sorted_str_list(
        safety_audit.get("families_with_structured_safety_path")
    )
    missing_families = _sorted_str_list(
        safety_audit.get("families_missing_structured_safety_path")
    )
    if family in linked_families:
        return {
            "path_status": "connected",
            "linkage_path": list(safety_audit.get("linkage_path", [])),
            "reference_linkage_status": safety_audit.get("reference_linkage_status"),
            "reference_linkage_completeness": _as_dict(
                safety_audit.get("reference_linkage_completeness")
            ),
            "next_action_workflow_category_join": _as_dict(
                safety_audit.get("next_action_workflow_category_join")
            ),
            "frozen_eval_category_join": _as_dict(
                safety_audit.get("frozen_eval_category_join")
            ),
        }
    if family in missing_families:
        return {
            "path_status": "missing",
            "missing_reason": (
                "No structured safety evidence contract bundle is mapped to this "
                "weakest safety family in the current audit layer."
            ),
        }
    return {}


def _summary_structured_safety_completeness(
    family_summaries: list[dict[str, object]],
) -> dict[str, object]:
    safety_families = [
        item for item in family_summaries if str(item.get("family")).startswith("safety_")
    ]
    linked_families = [
        str(item.get("family"))
        for item in safety_families
        if _as_dict(item.get("structured_safety_evidence_audit")).get("path_status")
        == "connected"
    ]
    missing_families = [
        str(item.get("family"))
        for item in safety_families
        if _as_dict(item.get("structured_safety_evidence_audit")).get("path_status")
        == "missing"
    ]
    status_counts = Counter(
        str(_as_dict(item.get("structured_safety_evidence_audit")).get("reference_linkage_status"))
        for item in safety_families
        if _as_dict(item.get("structured_safety_evidence_audit")).get("reference_linkage_status")
    )
    return {
        "linked_family_count": len(linked_families),
        "missing_family_count": len(missing_families),
        "linked_case_count": sum(
            int(item.get("case_count", 0))
            for item in safety_families
            if str(item.get("family")) in linked_families
        ),
        "missing_case_count": sum(
            int(item.get("case_count", 0))
            for item in safety_families
            if str(item.get("family")) in missing_families
        ),
        "linked_families": linked_families,
        "missing_families": missing_families,
        "reference_linkage_status_counts": dict(status_counts),
    }


def _build_frozen_eval_safety_family_join(
    *,
    eval_report: dict[str, object],
    family: str,
    safety_proof: dict[str, object],
    next_action_proof: dict[str, object],
) -> dict[str, object]:
    family_cases = [
        item
        for item in _as_list(eval_report.get("case_results"))
        if _as_dict(item).get("category") == family
    ]
    if not family_cases:
        return {
            "family": family,
            "join_status": "missing",
            "missing_reason": "No frozen-eval cases for this safety family were available.",
        }

    status_counts: Counter[str] = Counter()
    next_action_counts: Counter[str] = Counter()
    rule_counts: Counter[str] = Counter()
    case_ids: list[str] = []
    for case in family_cases:
        case_dict = _as_dict(case)
        actual = _as_dict(case_dict.get("actual"))
        case_id = case_dict.get("case_id")
        if isinstance(case_id, str):
            case_ids.append(case_id)
        status = actual.get("status")
        if isinstance(status, str):
            status_counts[status] += 1
        next_action = actual.get("next_action")
        if isinstance(next_action, str):
            next_action_counts[next_action] += 1
        for rule_id in _sorted_str_list(actual.get("rule_ids")):
            rule_counts[rule_id] += 1

    fixture_rule_ids = _safety_fixture_rule_ids(safety_proof)
    observed_rule_ids = sorted(rule_counts)
    fixture_rule_overlap = sorted(set(fixture_rule_ids) & set(observed_rule_ids))

    return {
        "family": family,
        "join_status": "connected",
        "category_case_count": len(family_cases),
        "case_ids": sorted(case_ids),
        "actual_status_counts": dict(sorted(status_counts.items())),
        "actual_next_action_counts": dict(sorted(next_action_counts.items())),
        "observed_rule_id_counts": dict(sorted(rule_counts.items())),
        "fixture_response_status": safety_proof.get("response_status"),
        "fixture_next_action": safety_proof.get("next_action"),
        "fixture_rule_ids": fixture_rule_ids,
        "fixture_rule_count": len(fixture_rule_ids),
        "fixture_rule_overlap_ids": fixture_rule_overlap,
        "fixture_rule_overlap_count": len(fixture_rule_overlap),
        "fixture_next_action_seen_in_family": safety_proof.get("next_action")
        in next_action_counts,
        "workflow_contract_next_action": next_action_proof.get("next_action"),
        "workflow_contract_next_action_seen_in_family": next_action_proof.get("next_action")
        in next_action_counts,
    }


def _build_frozen_eval_next_action_family_join(
    *,
    eval_report: dict[str, object],
    family: str,
    next_action_branch_fixtures: list[dict[str, object]],
) -> dict[str, object]:
    family_cases = [
        item
        for item in _as_list(eval_report.get("case_results"))
        if _as_dict(item).get("category") == family
    ]
    if not family_cases:
        return {
            "family": family,
            "join_status": "missing",
            "missing_reason": "No frozen-eval cases for this safety family were available.",
        }

    status_counts: Counter[str] = Counter()
    next_action_counts: Counter[str] = Counter()
    matched_case_count = 0
    matched_case_ids: list[str] = []
    case_ids: list[str] = []
    matched_case_ids_set: set[str] = set()
    branch_summaries: list[dict[str, object]] = []
    for case in family_cases:
        case_dict = _as_dict(case)
        actual = _as_dict(case_dict.get("actual"))
        case_id = case_dict.get("case_id")
        if isinstance(case_id, str):
            case_ids.append(case_id)
        status = actual.get("status")
        if isinstance(status, str):
            status_counts[status] += 1
        next_action = actual.get("next_action")
        if isinstance(next_action, str):
            next_action_counts[next_action] += 1

    branch_seen_statuses: set[str] = set()
    branch_seen_actions: set[str] = set()
    for branch in next_action_branch_fixtures:
        fixture_response_status = branch.get("response_status")
        fixture_next_action = branch.get("next_action")
        branch_matched_case_ids: list[str] = []
        for case in family_cases:
            case_dict = _as_dict(case)
            actual = _as_dict(case_dict.get("actual"))
            case_id = case_dict.get("case_id")
            status = actual.get("status")
            next_action = actual.get("next_action")
            if status == fixture_response_status and next_action == fixture_next_action:
                if isinstance(case_id, str):
                    branch_matched_case_ids.append(case_id)
                    matched_case_ids_set.add(case_id)
        if isinstance(fixture_response_status, str) and fixture_response_status in status_counts:
            branch_seen_statuses.add(fixture_response_status)
        if isinstance(fixture_next_action, str) and fixture_next_action in next_action_counts:
            branch_seen_actions.add(fixture_next_action)
        branch_summaries.append(
            {
                "request_fixture_path": branch.get("request_fixture_path"),
                "response_status": fixture_response_status,
                "next_action": fixture_next_action,
                "projected_workflow_state": branch.get("projected_workflow_state"),
                "issue_count": branch.get("issue_count"),
                "matched_case_count": len(branch_matched_case_ids),
                "matched_case_ids": sorted(branch_matched_case_ids),
            }
        )

    matched_case_ids = sorted(matched_case_ids_set)
    matched_case_count = len(matched_case_ids)

    category_case_count = len(family_cases)
    unmatched_next_actions = {
        action: count
        for action, count in sorted(next_action_counts.items())
        if action not in branch_seen_actions
    }
    coverage_pct = 0.0
    if category_case_count > 0:
        coverage_pct = (matched_case_count / category_case_count) * 100.0

    return {
        "family": family,
        "join_status": "connected",
        "category_case_count": category_case_count,
        "case_ids": sorted(case_ids),
        "actual_status_counts": dict(sorted(status_counts.items())),
        "actual_next_action_counts": dict(sorted(next_action_counts.items())),
        "fixture_branches": branch_summaries,
        "fixture_response_status_seen_in_family": all(
            branch.get("response_status") in status_counts for branch in next_action_branch_fixtures
        ),
        "fixture_next_action_seen_in_family": all(
            branch.get("next_action") in next_action_counts
            for branch in next_action_branch_fixtures
        ),
        "matched_case_count": matched_case_count,
        "matched_case_ids": sorted(matched_case_ids),
        "coverage_pct": coverage_pct,
        "unmatched_next_action_counts": unmatched_next_actions,
    }


def _next_action_branch_fixtures(
    *,
    primary_report: dict[str, object],
    primary_report_path: str | Path,
    blocked_report: dict[str, object] | None,
    blocked_report_path: str | Path | None,
) -> list[dict[str, object]]:
    branches: list[dict[str, object]] = []
    for report, fallback_path in (
        (primary_report, primary_report_path),
        (blocked_report, blocked_report_path),
    ):
        report_dict = _as_dict(report)
        if not report_dict:
            continue
        branch = {
            "request_fixture_path": str(
                report_dict.get("request_fixture_path") or fallback_path or ""
            ),
            "response_status": report_dict.get("response_status"),
            "next_action": report_dict.get("next_action"),
            "projected_workflow_state": report_dict.get("projected_workflow_state"),
            "issue_count": report_dict.get("issue_count"),
        }
        if branch not in branches:
            branches.append(branch)
    return branches


def _safety_fixture_rule_ids(safety_proof: dict[str, object]) -> list[str]:
    proof_rule_ids = _sorted_str_list(safety_proof.get("fixture_rule_ids"))
    if proof_rule_ids:
        return proof_rule_ids
    example_event = _as_dict(safety_proof.get("example_event"))
    rule_links = _as_list(example_event.get("rule_links"))
    rule_ids = sorted(
        {
            str(_as_dict(rule_link).get("rule_id"))
            for rule_link in rule_links
            if _as_dict(rule_link).get("rule_id") is not None
        }
    )
    return rule_ids


def _family_gaps(*, family: str, remaining_gaps: list[str], audit: dict[str, object]) -> list[str]:
    sensor_family = _sensor_family(audit)
    pro_family = _pro_family(audit)
    workflow_family = _workflow_family(audit)
    family_gaps: list[str] = []
    for gap in remaining_gaps:
        lower_gap = gap.lower()
        if family == sensor_family and any(
            token in lower_gap for token in ("parser", "cgm", "sensor/genetic")
        ):
            family_gaps.append(gap)
        elif family == pro_family and any(
            token in lower_gap
            for token in (
                "baseline/follow-up pro",
                "baseline_followup_pro",
                "shared-event pro",
                "pro single-path",
            )
        ):
            family_gaps.append(gap)
        elif family == workflow_family and any(
            token in lower_gap for token in ("followup", "workflow", "safety")
        ):
            family_gaps.append(gap)
    if not family_gaps and not _contracts_for_family(family=family, weakest_metrics=[]):
        family_gaps.append(
            "No dedicated contract bundle is mapped to this weakest family in the "
            "current audit layer."
        )
    return family_gaps


def _all_schema_fixtures_pass(report: dict[str, object]) -> bool:
    results = _as_dict(report.get("valid_fixture_results"))
    return bool(results) and all(_as_dict(item).get("passed") for item in results.values())


def _valid_fixture_pass_count(report: dict[str, object]) -> int:
    return sum(
        1
        for item in _as_dict(report.get("valid_fixture_results")).values()
        if _as_dict(item).get("passed")
    )


def _failure_type_taxonomy_entries(
    failure_types: list[str],
    *,
    default_stage: str,
) -> list[dict[str, str]]:
    return [
        {
            "failure_type": failure_type,
            "stage": _classify_failure_stage(
                failure_type,
                default_stage=default_stage,
            ),
            "modality": _classify_failure_modality(failure_type),
            "family": _classify_failure_family(failure_type),
            "field": _classify_failure_field(failure_type),
        }
        for failure_type in failure_types
    ]


def _classify_failure_stage(failure_type: str, *, default_stage: str) -> str:
    if failure_type.endswith("_invalid_numeric_ignored"):
        return "parser_normalization_fallback"
    if "::" in failure_type:
        return "file_schema_validation"
    return default_stage


def _classify_failure_modality(failure_type: str) -> str:
    if failure_type.startswith("wearable_") or "::wearable_summary::" in failure_type:
        return "wearable"
    if failure_type.startswith("cgm_") or "::cgm_summary::" in failure_type:
        return "cgm"
    if failure_type.startswith("genetic_") or "::gene_profile::" in failure_type:
        return "genetic"
    return "unknown"


def _classify_failure_family(failure_type: str) -> str:
    if failure_type.endswith("_invalid_numeric_ignored"):
        return "invalid_numeric_ignored"
    if failure_type.startswith("missing_required_field::"):
        return "missing_required_field"
    if failure_type.startswith("missing_unit::"):
        return "missing_unit"
    if failure_type.startswith("invalid_value_type::"):
        return "invalid_value_type"
    if failure_type.startswith("invalid_payload_type::"):
        return "invalid_payload_type"
    if failure_type.startswith("invalid_numeric_value::"):
        return "invalid_numeric_value"
    if failure_type.startswith("invalid_integer_value::"):
        return "invalid_integer_value"
    return "unclassified"


def _classify_failure_field(failure_type: str) -> str:
    if failure_type.endswith("_invalid_numeric_ignored"):
        raw_field = failure_type[: -len("_invalid_numeric_ignored")]
        if "_" in raw_field:
            _, raw_field = raw_field.split("_", 1)
        return raw_field or "unknown"
    if "::" in failure_type:
        parts = failure_type.split("::")
        if len(parts) >= 3:
            return parts[-1] or "unknown"
    return "unknown"


def _count_taxonomy_field(
    taxonomy_entries: list[dict[str, str]],
    *,
    key: str,
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item in taxonomy_entries:
        counts[str(item.get(key))] += 1
    return dict(sorted(counts.items()))


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _sorted_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(item) for item in value)


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_weakest_slice_frozen_eval_audit",
    "build_weakest_slice_frozen_eval_summary",
    "load_json_artifact",
    "render_weakest_slice_frozen_eval_audit_markdown",
    "render_weakest_slice_frozen_eval_summary_markdown",
    "validate_structured_safety_evidence_linkage_audit",
    "write_weakest_slice_frozen_eval_summary_files",
    "write_weakest_slice_frozen_eval_audit_files",
]
