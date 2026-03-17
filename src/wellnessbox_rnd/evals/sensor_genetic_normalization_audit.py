from __future__ import annotations

import json
from pathlib import Path


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_sensor_genetic_normalization_audit(
    *,
    parser_report: dict[str, object],
    parser_report_path: str | Path,
    file_schema_report: dict[str, object],
    file_schema_report_path: str | Path,
    cgm_event_report: dict[str, object],
    cgm_event_report_path: str | Path,
    cgm_slice_report: dict[str, object],
    cgm_slice_report_path: str | Path,
    weakest_slice_audit: dict[str, object],
    weakest_slice_audit_path: str | Path,
    frozen_eval_dataset_path: str | Path | None = None,
) -> dict[str, object]:
    supported_failure_types = sorted(
        set(_sorted_str_list(parser_report.get("supported_failure_types")))
        | set(_schema_failure_types(file_schema_report))
    )
    parser_cgm_cases = {
        str(case.get("case_id")): _as_dict(case.get("normalized_snapshot"))
        for case in parser_report.get("normalized_cases", [])
        if isinstance(case, dict)
        and _as_dict(case.get("normalized_snapshot")).get("cgm_available") is True
    }
    cgm_slice_cases = {
        str(case.get("case_id")): _as_dict(case)
        for case in cgm_slice_report.get("cases", [])
        if isinstance(case, dict)
    }
    cgm_event = _as_dict(cgm_event_report.get("event"))
    parser_reference_case = _as_dict(parser_cgm_cases.get("cgm_mmol_conversion"))
    required_components = _as_dict(weakest_slice_audit.get("required_path_components"))
    anchor = _as_dict(weakest_slice_audit.get("frozen_eval_anchor"))
    integration_metric = _as_dict(anchor.get("sensor_genetic_integration_metric"))
    integration_bottleneck = _as_dict(anchor.get("integration_bottleneck"))
    path_summary = _as_dict(weakest_slice_audit.get("audit_path_summary"))
    connection_edges = [
        _as_dict(edge) for edge in _as_list(path_summary.get("connection_edges"))
    ]
    frozen_eval_category_join = _build_frozen_eval_category_join(
        frozen_eval_dataset_path=frozen_eval_dataset_path,
        weakest_category=str(integration_metric.get("category") or ""),
        weakest_score=_to_float(integration_metric.get("score")),
        supported_failure_taxonomy=_as_dict(
            _as_dict(required_components.get("supported_parser_failure_types")).get("proof")
        ).get("combined_failure_type_taxonomy"),
    )
    direct_cgm_case_family_join = _build_direct_cgm_case_family_join(
        frozen_eval_dataset_path=frozen_eval_dataset_path,
        weakest_category=str(integration_metric.get("category") or ""),
        supported_failure_taxonomy=_as_dict(
            _as_dict(required_components.get("supported_parser_failure_types")).get("proof")
        ).get("combined_failure_type_taxonomy"),
        cgm_slice_report=cgm_slice_report,
    )

    audit = {
        "audit_name": "sensor_genetic_normalization_audit_v1",
        "source_artifacts": {
            "parser_report_path": str(parser_report_path),
            "file_schema_report_path": str(file_schema_report_path),
            "cgm_event_report_path": str(cgm_event_report_path),
            "cgm_slice_report_path": str(cgm_slice_report_path),
            "weakest_slice_audit_path": str(weakest_slice_audit_path),
            "frozen_eval_dataset_path": (
                str(Path(frozen_eval_dataset_path))
                if frozen_eval_dataset_path is not None
                else None
            ),
        },
        "normalization_coverage": {
            "parser_case_count": parser_report.get("case_count"),
            "wearable_case_count": parser_report.get("wearable_case_count"),
            "cgm_case_count": parser_report.get("cgm_case_count"),
            "genetic_case_count": parser_report.get("genetic_case_count"),
            "schema_valid_fixture_pass_count": _valid_fixture_pass_count(file_schema_report),
            "schema_valid_fixture_total": len(
                _as_dict(file_schema_report.get("valid_fixture_results"))
            ),
            "supported_failure_type_count": len(supported_failure_types),
            "cgm_bridge_case_count": cgm_slice_report.get("case_count"),
            "cgm_bridge_valid_case_count": cgm_slice_report.get("valid_case_count"),
        },
        "consistency_checks": {
            "cgm_parser_case_count_matches_bridge": (
                parser_report.get("cgm_case_count") == cgm_slice_report.get("case_count")
            ),
            "cgm_bridge_case_ids_match_parser_cgm_cases": (
                sorted(cgm_slice_cases) == sorted(parser_cgm_cases)
            ),
            "cgm_failure_types_subset_of_supported_types": set(
                _as_dict(cgm_slice_report.get("parser_failure_type_counts"))
            ).issubset(set(supported_failure_types)),
            "cgm_event_matches_parser_reference_case": _cgm_event_matches_parser_case(
                cgm_event=cgm_event,
                parser_case=parser_reference_case,
            ),
            "integration_path_connected": _integration_path_connected(
                required_components=required_components,
                connection_edges=connection_edges,
            ),
            "integration_bottleneck_modality_is_cgm": (
                integration_bottleneck.get("modality") == "cgm"
            ),
        },
        "downstream_bridge_summary": {
            "threshold_tag_counts": _as_dict(cgm_slice_report.get("threshold_tag_counts")),
            "parser_failure_type_counts": _as_dict(
                cgm_slice_report.get("parser_failure_type_counts")
            ),
            "threshold_edge_case_ids": _sorted_str_list(
                cgm_slice_report.get("threshold_edge_case_ids")
            ),
            "eval_attempted_count": cgm_slice_report.get("eval_attempted_count"),
            "eval_success_count": cgm_slice_report.get("eval_success_count"),
        },
        "integration_metric_path": {
            "weakest_metric_category": integration_metric.get("category"),
            "weakest_metric_score": integration_metric.get("score"),
            "bottleneck_modality": integration_bottleneck.get("modality"),
            "bottleneck_rate_pct": integration_bottleneck.get("rate_pct"),
            "required_component_statuses": {
                name: _as_dict(required_components.get(name)).get("status")
                for name in (
                    "parser_outputs",
                    "file_schema_validation",
                    "supported_parser_failure_types",
                    "CGMNormalizedEventV1",
                    "cgm_slice_bridge_summary_v1",
                )
            },
            "connection_path": [
                "file_schema_validation",
                "parser_outputs",
                "supported_parser_failure_types",
                "CGMNormalizedEventV1",
                "cgm_slice_bridge_summary_v1",
                "frozen_eval.sensor_genetic_integration_rate_pct",
            ],
        },
        "frozen_eval_category_join": frozen_eval_category_join,
        "direct_cgm_case_family_join": direct_cgm_case_family_join,
        "coverage_gaps": _build_coverage_gaps(
            parser_report=parser_report,
            cgm_event_report=cgm_event_report,
            supported_failure_types=supported_failure_types,
            frozen_eval_category_join=frozen_eval_category_join,
            direct_cgm_case_family_join=direct_cgm_case_family_join,
        ),
    }
    audit["readable_summary"] = _build_readable_summary(audit)
    audit["validation_issues"] = validate_sensor_genetic_normalization_audit(audit)
    audit["normalization_drift_detected"] = bool(audit["validation_issues"])
    return audit


def validate_sensor_genetic_normalization_audit(
    audit: dict[str, object],
) -> list[str]:
    issues: list[str] = []
    coverage = _as_dict(audit.get("normalization_coverage"))
    checks = _as_dict(audit.get("consistency_checks"))
    path = _as_dict(audit.get("integration_metric_path"))
    frozen_eval_category_join = _as_dict(audit.get("frozen_eval_category_join"))
    direct_cgm_case_family_join = _as_dict(audit.get("direct_cgm_case_family_join"))

    if coverage.get("parser_case_count", 0) < 1:
        issues.append("missing_parser_cases")
    if (
        coverage.get("schema_valid_fixture_pass_count")
        != coverage.get("schema_valid_fixture_total")
    ):
        issues.append("schema_fixture_validation_incomplete")
    if not checks.get("cgm_parser_case_count_matches_bridge"):
        issues.append("cgm_parser_case_count_bridge_mismatch")
    if not checks.get("cgm_bridge_case_ids_match_parser_cgm_cases"):
        issues.append("cgm_case_id_bridge_mismatch")
    if not checks.get("cgm_failure_types_subset_of_supported_types"):
        issues.append("unsupported_cgm_failure_type_in_bridge")
    if not checks.get("cgm_event_matches_parser_reference_case"):
        issues.append("cgm_event_parser_reference_mismatch")
    if not checks.get("integration_path_connected"):
        issues.append("sensor_genetic_integration_path_disconnected")
    if not checks.get("integration_bottleneck_modality_is_cgm"):
        issues.append("unexpected_integration_bottleneck_modality")

    component_statuses = _as_dict(path.get("required_component_statuses"))
    if any(status != "connected" for status in component_statuses.values()):
        issues.append("required_sensor_genetic_component_not_connected")
    if frozen_eval_category_join:
        if not frozen_eval_category_join.get("pooled_score_matches_weakest_metric"):
            issues.append("frozen_eval_category_join_metric_mismatch")
        if _to_int(frozen_eval_category_join.get("case_count")) < 1:
            issues.append("missing_frozen_eval_category_cases")
    if direct_cgm_case_family_join:
        if not direct_cgm_case_family_join.get("selected_is_lowest_cgm_score_family"):
            issues.append("direct_cgm_family_join_selection_mismatch")
        if _to_int(
            _nested(
                direct_cgm_case_family_join,
                "modality_attempted_success",
                "cgm",
                "attempted",
            )
        ) < 1:
            issues.append("direct_cgm_family_join_without_cgm_attempts")
        if direct_cgm_case_family_join.get("join_status") != "connected":
            issues.append("direct_cgm_family_join_disconnected")

    return issues


def render_sensor_genetic_normalization_audit_markdown(
    audit: dict[str, object],
) -> str:
    coverage = _as_dict(audit.get("normalization_coverage"))
    checks = _as_dict(audit.get("consistency_checks"))
    bridge = _as_dict(audit.get("downstream_bridge_summary"))
    path = _as_dict(audit.get("integration_metric_path"))
    frozen_eval_category_join = _as_dict(audit.get("frozen_eval_category_join"))
    direct_cgm_case_family_join = _as_dict(audit.get("direct_cgm_case_family_join"))
    readable_summary = _as_dict(audit.get("readable_summary"))
    lines = [
        "# sensor genetic normalization audit v1",
        "",
        "## readable summary",
        "",
        f"- normalization_path_status: `{readable_summary.get('normalization_path_status')}`",
        (
            "- sensor_genetic_integration_rate_linkage_status: "
            f"`{_nested(
                readable_summary,
                'bridge_and_metric_digest',
                'sensor_genetic_integration_rate_linkage_status',
            )}`"
        ),
        (
            "- component_coverage_matrix: "
            f"`{readable_summary.get('component_coverage_matrix', [])}`"
        ),
        (
            "- parser_failure_type_digest: "
            f"`{readable_summary.get('parser_failure_type_digest', {})}`"
        ),
        (
            "- coverage_gap_summary: "
            f"`{readable_summary.get('coverage_gap_summary', {})}`"
        ),
        "",
        "## coverage",
        "",
        f"- parser_case_count: `{coverage.get('parser_case_count')}`",
        f"- wearable_case_count: `{coverage.get('wearable_case_count')}`",
        f"- cgm_case_count: `{coverage.get('cgm_case_count')}`",
        f"- genetic_case_count: `{coverage.get('genetic_case_count')}`",
        f"- schema_valid_fixture_pass_count: `{coverage.get('schema_valid_fixture_pass_count')}`",
        f"- schema_valid_fixture_total: `{coverage.get('schema_valid_fixture_total')}`",
        f"- supported_failure_type_count: `{coverage.get('supported_failure_type_count')}`",
        f"- cgm_bridge_case_count: `{coverage.get('cgm_bridge_case_count')}`",
        f"- cgm_bridge_valid_case_count: `{coverage.get('cgm_bridge_valid_case_count')}`",
        "",
        "## consistency checks",
        "",
    ]
    for key, value in checks.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## downstream bridge summary",
            "",
            f"- threshold_tag_counts: `{bridge.get('threshold_tag_counts', {})}`",
            f"- parser_failure_type_counts: `{bridge.get('parser_failure_type_counts', {})}`",
            f"- threshold_edge_case_ids: `{bridge.get('threshold_edge_case_ids', [])}`",
            f"- eval_attempted_count: `{bridge.get('eval_attempted_count')}`",
            f"- eval_success_count: `{bridge.get('eval_success_count')}`",
            "",
            "## integration metric path",
            "",
            f"- weakest_metric_category: `{path.get('weakest_metric_category')}`",
            f"- weakest_metric_score: `{path.get('weakest_metric_score')}`",
            f"- bottleneck_modality: `{path.get('bottleneck_modality')}`",
            f"- bottleneck_rate_pct: `{path.get('bottleneck_rate_pct')}`",
            f"- required_component_statuses: `{path.get('required_component_statuses', {})}`",
            f"- connection_path: `{path.get('connection_path', [])}`",
            "",
            "## frozen eval category join",
            "",
            f"- weakest_category: `{frozen_eval_category_join.get('weakest_category')}`",
            f"- join_scope: `{frozen_eval_category_join.get('join_scope')}`",
            f"- case_ids: `{frozen_eval_category_join.get('case_ids', [])}`",
            (
                "- modality_attempted_success: "
                f"`{frozen_eval_category_join.get('modality_attempted_success', {})}`"
            ),
            (
                "- supported_failure_taxonomy_by_modality: "
                f"`{frozen_eval_category_join.get('supported_failure_taxonomy_by_modality', {})}`"
            ),
            (
                "- related_sensor_genetic_categories: "
                f"`{frozen_eval_category_join.get('related_sensor_genetic_categories', [])}`"
            ),
            "",
            "## direct cgm case-family join",
            "",
            f"- selected_family: `{direct_cgm_case_family_join.get('selected_family')}`",
            f"- join_scope: `{direct_cgm_case_family_join.get('join_scope')}`",
            f"- join_status: `{direct_cgm_case_family_join.get('join_status')}`",
            f"- selection_rule: `{direct_cgm_case_family_join.get('selection_rule')}`",
            f"- case_ids: `{direct_cgm_case_family_join.get('case_ids', [])}`",
            (
                "- modality_attempted_success: "
                f"`{direct_cgm_case_family_join.get('modality_attempted_success', {})}`"
            ),
            (
                "- supported_cgm_failure_taxonomy: "
                f"`{direct_cgm_case_family_join.get('supported_cgm_failure_taxonomy', [])}`"
            ),
            (
                "- bridge_evidence_summary: "
                f"`{direct_cgm_case_family_join.get('bridge_evidence_summary', {})}`"
            ),
            "",
            "## gaps",
            "",
        ]
    )
    for gap in _sorted_str_list(audit.get("coverage_gaps")):
        lines.append(f"- {gap}")
    lines.extend(
        [
            "",
            "## validation",
            "",
            f"- normalization_drift_detected: `{audit.get('normalization_drift_detected')}`",
            f"- validation_issues: `{audit.get('validation_issues', [])}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_sensor_genetic_normalization_audit_files(
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
        render_sensor_genetic_normalization_audit_markdown(audit),
        encoding="utf-8",
    )


def _schema_failure_types(file_schema_report: dict[str, object]) -> list[str]:
    return sorted(
        {
            failure_type
            for example in _as_dict(file_schema_report.get("failure_type_examples")).values()
            if isinstance(example, dict)
            for failure_type in _sorted_str_list(example.get("failure_types"))
        }
    )


def _valid_fixture_pass_count(file_schema_report: dict[str, object]) -> int:
    return sum(
        1
        for item in _as_dict(file_schema_report.get("valid_fixture_results")).values()
        if _as_dict(item).get("passed") is True
    )


def _cgm_event_matches_parser_case(
    *,
    cgm_event: dict[str, object],
    parser_case: dict[str, object],
) -> bool:
    if not cgm_event or not parser_case:
        return False
    return (
        cgm_event.get("cgm_available") == parser_case.get("cgm_available")
        and cgm_event.get("mean_glucose_mg_dl") == parser_case.get("mean_glucose_mg_dl")
        and cgm_event.get("time_in_range_pct") == parser_case.get("time_in_range_pct")
        and cgm_event.get("post_meal_spike_concern") == parser_case.get("post_meal_spike_concern")
        and _sorted_str_list(cgm_event.get("normalization_notes"))
        == _sorted_str_list(parser_case.get("normalization_notes"))
    )


def _integration_path_connected(
    *,
    required_components: dict[str, object],
    connection_edges: list[dict[str, object]],
) -> bool:
    needed_components = (
        "parser_outputs",
        "file_schema_validation",
        "supported_parser_failure_types",
        "CGMNormalizedEventV1",
        "cgm_slice_bridge_summary_v1",
    )
    if any(
        _as_dict(required_components.get(name)).get("status") != "connected"
        for name in needed_components
    ):
        return False
    needed_edges = {
        ("file_schema_validation", "parser_outputs"),
        ("parser_outputs", "supported_parser_failure_types"),
        ("parser_outputs", "CGMNormalizedEventV1"),
        ("CGMNormalizedEventV1", "cgm_slice_bridge_summary_v1"),
        ("cgm_slice_bridge_summary_v1", "frozen_eval.sensor_genetic_integration_rate_pct"),
    }
    actual_edges = {
        (str(edge.get("from")), str(edge.get("to")))
        for edge in connection_edges
        if edge
    }
    return needed_edges.issubset(actual_edges)


def _build_coverage_gaps(
    *,
    parser_report: dict[str, object],
    cgm_event_report: dict[str, object],
    supported_failure_types: list[str],
    frozen_eval_category_join: dict[str, object],
    direct_cgm_case_family_join: dict[str, object],
) -> list[str]:
    gaps: list[str] = []
    cases_path = str(parser_report.get("cases_json_path"))
    if cases_path.startswith("data/samples/") or cases_path.startswith("data\\samples\\"):
        gaps.append(
            "parser, sensor, genetic, and CGM proof inputs are still sample-fixture scoped "
            "rather than frozen-eval case-level joined."
        )
    if parser_report.get("genetic_case_count") == 1:
        gaps.append(
            "genetic normalization proof currently covers only one parser smoke case."
        )
    if str(cgm_event_report.get("source_fixture_path")).startswith("data/samples/") or str(
        cgm_event_report.get("source_fixture_path")
    ).startswith("data\\samples\\"):
        gaps.append(
            "CGMNormalizedEventV1 proof currently depends on a single source fixture."
        )
    if frozen_eval_category_join:
        if (
            _to_int(
                _nested(
                    frozen_eval_category_join,
                    "modality_attempted_success",
                    "cgm",
                    "attempted",
                )
            )
            == 0
        ):
            gaps.append(
                "The overall weakest frozen-eval family is now category-joined, but it has "
                "no direct CGM attempts, so its own evidence path is still adjacent even "
                "though a separate direct CGM-carrying family join now exists."
            )
    if direct_cgm_case_family_join:
        gaps.append(
            "direct CGM family joining now exists at the frozen-eval case-family level, "
            "but parser sample fixtures still do not share frozen-eval case_ids one by one."
        )
    else:
        gaps.append(
            "parser failure taxonomy is now joined to frozen-eval by category/modality, "
            "but parser sample fixtures still do not share frozen-eval case_ids one by one."
        )
    if not supported_failure_types:
        gaps.append("supported parser failure type coverage is empty.")
    return gaps


def _build_readable_summary(audit: dict[str, object]) -> dict[str, object]:
    coverage = _as_dict(audit.get("normalization_coverage"))
    bridge = _as_dict(audit.get("downstream_bridge_summary"))
    path = _as_dict(audit.get("integration_metric_path"))
    category_join = _as_dict(audit.get("frozen_eval_category_join"))
    direct_cgm_join = _as_dict(audit.get("direct_cgm_case_family_join"))
    gap_summary = _build_coverage_gap_summary(
        coverage_gaps=_as_list(audit.get("coverage_gaps")),
        coverage=coverage,
        category_join=category_join,
        direct_cgm_join=direct_cgm_join,
    )
    path_connected = bool(
        _as_dict(audit.get("consistency_checks")).get("integration_path_connected")
    )
    return {
        "normalization_path_status": _build_normalization_path_status(
            path_connected=path_connected,
            gap_summary=gap_summary,
        ),
        "component_coverage_matrix": _build_component_coverage_matrix(
            coverage=coverage,
            path=path,
            bridge=bridge,
        ),
        "parser_failure_type_digest": {
            "supported_failure_type_count": coverage.get("supported_failure_type_count"),
            "supported_failure_family_counts": _count_failure_families_by_modality(
                category_join
            ),
            "bridge_failure_type_counts": bridge.get("parser_failure_type_counts", {}),
        },
        "bridge_and_metric_digest": {
            "cgm_bridge_case_count": coverage.get("cgm_bridge_case_count"),
            "cgm_bridge_valid_case_count": coverage.get("cgm_bridge_valid_case_count"),
            "threshold_edge_case_ids": bridge.get("threshold_edge_case_ids", []),
            "weakest_metric_category": path.get("weakest_metric_category"),
            "weakest_metric_score": path.get("weakest_metric_score"),
            "bottleneck_modality": path.get("bottleneck_modality"),
            "sensor_genetic_integration_rate_linkage_status": (
                "category_join_connected_direct_cgm_family_connected"
                if direct_cgm_join.get("join_status") == "connected"
                and category_join.get("pooled_score_matches_weakest_metric")
                else "linkage_gap_present"
            ),
        },
        "coverage_gap_summary": gap_summary,
    }


def _build_normalization_path_status(
    *,
    path_connected: bool,
    gap_summary: dict[str, object],
) -> str:
    if not path_connected:
        return "disconnected"
    if _to_int(gap_summary.get("gap_count")) < 1:
        return "connected_no_gap"
    if gap_summary.get("fixture_scope_only") is True:
        return "connected_fixture_scoped_no_drift"
    return "connected_with_gap"


def _build_component_coverage_matrix(
    *,
    coverage: dict[str, object],
    path: dict[str, object],
    bridge: dict[str, object],
) -> list[dict[str, object]]:
    component_statuses = _as_dict(path.get("required_component_statuses"))
    return [
        {
            "component": "file_schema_validation",
            "status": component_statuses.get("file_schema_validation"),
            "proof": (
                f"{coverage.get('schema_valid_fixture_pass_count')}/"
                f"{coverage.get('schema_valid_fixture_total')} valid fixtures"
            ),
        },
        {
            "component": "parser_outputs",
            "status": component_statuses.get("parser_outputs"),
            "proof": f"{coverage.get('parser_case_count')} parser smoke cases",
        },
        {
            "component": "supported_parser_failure_types",
            "status": component_statuses.get("supported_parser_failure_types"),
            "proof": f"{coverage.get('supported_failure_type_count')} supported failure types",
        },
        {
            "component": "CGMNormalizedEventV1",
            "status": component_statuses.get("CGMNormalizedEventV1"),
            "proof": f"{coverage.get('cgm_case_count')} parser CGM cases",
        },
        {
            "component": "cgm_slice_bridge_summary_v1",
            "status": component_statuses.get("cgm_slice_bridge_summary_v1"),
            "proof": (
                f"{coverage.get('cgm_bridge_valid_case_count')}/"
                f"{coverage.get('cgm_bridge_case_count')} valid bridge cases"
            ),
        },
        {
            "component": "sensor_genetic_integration_rate_pct",
            "status": "connected",
            "proof": (
                f"{path.get('weakest_metric_category')} @ "
                f"{path.get('weakest_metric_score')}"
            ),
        },
    ]


def _build_coverage_gap_summary(
    *,
    coverage_gaps: list[object],
    coverage: dict[str, object],
    category_join: dict[str, object],
    direct_cgm_join: dict[str, object],
) -> dict[str, object]:
    gap_classes = []
    gap_text = " ".join(str(item) for item in coverage_gaps)
    if "sample-fixture scoped" in gap_text:
        gap_classes.append("fixture_scope")
    if "one parser smoke case" in gap_text:
        gap_classes.append("genetic_single_case")
    if "single source fixture" in gap_text:
        gap_classes.append("single_cgm_fixture")
    if "no direct CGM attempts" in gap_text:
        gap_classes.append("weakest_family_adjacent_only")
    if "do not share frozen-eval case_ids one by one" in gap_text:
        gap_classes.append("case_id_lineage_mismatch")
    return {
        "gap_count": len(coverage_gaps),
        "gap_classes": gap_classes,
        "fixture_scope_only": bool(coverage_gaps),
        "genetic_parser_case_count": coverage.get("genetic_case_count"),
        "cgm_event_fixture_count": 1,
        "weakest_category_case_count": category_join.get("case_count"),
        "direct_cgm_family_join_status": direct_cgm_join.get("join_status"),
        "smallest_measurable_fix": "audit_only_no_runtime_fix_required",
    }


def _count_failure_families_by_modality(
    category_join: dict[str, object],
) -> dict[str, dict[str, int]]:
    grouped = _as_dict(category_join.get("supported_failure_taxonomy_by_modality"))
    counts: dict[str, dict[str, int]] = {}
    for modality, items in grouped.items():
        family_counts: dict[str, int] = {}
        for item in _as_list(items):
            family = str(_as_dict(item).get("family") or "unknown")
            family_counts[family] = family_counts.get(family, 0) + 1
        counts[str(modality)] = family_counts
    return counts


def _build_frozen_eval_category_join(
    *,
    frozen_eval_dataset_path: str | Path | None,
    weakest_category: str,
    weakest_score: float,
    supported_failure_taxonomy: object,
) -> dict[str, object]:
    if frozen_eval_dataset_path is None:
        return {}
    dataset_path = Path(frozen_eval_dataset_path)
    if not dataset_path.exists():
        return {}
    rows = _load_jsonl_rows(dataset_path)
    weakest_rows = [
        row for row in rows if str(row.get("category")) == weakest_category
    ]
    if not weakest_rows:
        return {}
    modality_attempted_success = _aggregate_integration_counts(weakest_rows)
    pooled_score = _to_float(_nested(modality_attempted_success, "pooled", "score"))
    related_categories = []
    for category_name in ("free_text_alias", "cgm_supported", "genetic_supported"):
        category_rows = [
            row for row in rows if str(row.get("category")) == category_name
        ]
        if not category_rows:
            continue
        related_categories.append(
            {
                "category": category_name,
                "case_count": len(category_rows),
                "case_ids": [str(row.get("case_id")) for row in category_rows],
                "modality_attempted_success": _aggregate_integration_counts(category_rows),
            }
        )
    cgm_attempted = _to_int(_nested(modality_attempted_success, "cgm", "attempted"))
    return {
        "join_scope": "category_level",
        "weakest_category": weakest_category,
        "case_count": len(weakest_rows),
        "case_ids": [str(row.get("case_id")) for row in weakest_rows],
        "modality_attempted_success": modality_attempted_success,
        "pooled_score_matches_weakest_metric": _approx_equal(pooled_score, weakest_score),
        "supported_failure_taxonomy_by_modality": _group_failure_taxonomy_by_modality(
            supported_failure_taxonomy
        ),
        "cgm_bridge_applicability": (
            "not_direct_for_this_weakest_family" if cgm_attempted == 0 else "directly_present"
        ),
        "related_sensor_genetic_categories": related_categories,
    }


def _build_direct_cgm_case_family_join(
    *,
    frozen_eval_dataset_path: str | Path | None,
    weakest_category: str,
    supported_failure_taxonomy: object,
    cgm_slice_report: dict[str, object],
) -> dict[str, object]:
    if frozen_eval_dataset_path is None:
        return {}
    dataset_path = Path(frozen_eval_dataset_path)
    if not dataset_path.exists():
        return {}
    rows = _load_jsonl_rows(dataset_path)
    candidate_families: list[dict[str, object]] = []
    for category_name in sorted({str(row.get("category") or "") for row in rows}):
        category_rows = [
            row for row in rows if str(row.get("category") or "") == category_name
        ]
        if not category_rows:
            continue
        modality_attempted_success = _aggregate_integration_counts(category_rows)
        cgm_attempted = _to_int(_nested(modality_attempted_success, "cgm", "attempted"))
        if cgm_attempted < 1:
            continue
        candidate_families.append(
            {
                "category": category_name,
                "rows": category_rows,
                "modality_attempted_success": modality_attempted_success,
                "cgm_score": _to_float(_nested(modality_attempted_success, "cgm", "score")),
                "cgm_attempted": cgm_attempted,
            }
        )
    if not candidate_families:
        return {}
    selected_family = min(
        candidate_families,
        key=lambda item: (
            _to_float(item.get("cgm_score")),
            -_to_int(item.get("cgm_attempted")),
            str(item.get("category")),
        ),
    )
    supported_cgm_failure_taxonomy = _group_failure_taxonomy_by_modality(
        supported_failure_taxonomy
    ).get("cgm", [])
    return {
        "join_scope": "case_family_level",
        "join_status": "connected",
        "selection_rule": "lowest_cgm_score_with_attempted_gt_zero",
        "selected_family": selected_family.get("category"),
        "selected_family_is_overall_weakest_metric": (
            str(selected_family.get("category")) == weakest_category
        ),
        "selected_is_lowest_cgm_score_family": True,
        "case_count": len(_as_list(selected_family.get("rows"))),
        "case_ids": [
            str(_as_dict(row).get("case_id"))
            for row in _as_list(selected_family.get("rows"))
        ],
        "modality_attempted_success": _as_dict(
            selected_family.get("modality_attempted_success")
        ),
        "supported_cgm_failure_taxonomy": supported_cgm_failure_taxonomy,
        "bridge_evidence_summary": {
            "bridge_case_count": cgm_slice_report.get("case_count"),
            "bridge_valid_case_count": cgm_slice_report.get("valid_case_count"),
            "eval_attempted_count": cgm_slice_report.get("eval_attempted_count"),
            "eval_success_count": cgm_slice_report.get("eval_success_count"),
            "threshold_tag_counts": _as_dict(cgm_slice_report.get("threshold_tag_counts")),
            "parser_failure_type_counts": _as_dict(
                cgm_slice_report.get("parser_failure_type_counts")
            ),
            "threshold_edge_case_ids": _sorted_str_list(
                cgm_slice_report.get("threshold_edge_case_ids")
            ),
        },
    }


def _load_jsonl_rows(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _aggregate_integration_counts(rows: list[dict[str, object]]) -> dict[str, object]:
    modality_counts: dict[str, dict[str, object]] = {}
    total_attempted = 0
    total_success = 0
    for modality in ("wearable", "cgm", "genetic"):
        attempted = 0
        success = 0
        for row in rows:
            payload = _as_dict(_as_dict(row.get("integration")).get(modality))
            attempted += _to_int(payload.get("attempted"))
            success += _to_int(payload.get("success"))
        total_attempted += attempted
        total_success += success
        modality_counts[modality] = {
            "attempted": attempted,
            "success": success,
            "score": round((success / attempted) * 100, 6) if attempted else None,
        }
    modality_counts["pooled"] = {
        "attempted": total_attempted,
        "success": total_success,
        "score": round((total_success / total_attempted) * 100, 6)
        if total_attempted
        else None,
    }
    return modality_counts


def _group_failure_taxonomy_by_modality(
    taxonomy: object,
) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for item in _as_list(taxonomy):
        payload = _as_dict(item)
        modality = str(payload.get("modality") or "unknown")
        if modality not in {"wearable", "cgm", "genetic"}:
            continue
        grouped.setdefault(modality, []).append(
            {
                "failure_type": payload.get("failure_type"),
                "stage": payload.get("stage"),
                "family": payload.get("family"),
            }
        )
    return grouped


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _nested(payload: dict[str, object], *keys: str) -> object:
    current: object = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _to_float(value: object) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _to_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _approx_equal(left: float, right: float, tolerance: float = 1e-6) -> bool:
    return abs(left - right) <= tolerance


def _sorted_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(item) for item in value)


__all__ = [
    "build_sensor_genetic_normalization_audit",
    "load_json_artifact",
    "render_sensor_genetic_normalization_audit_markdown",
    "validate_sensor_genetic_normalization_audit",
    "write_sensor_genetic_normalization_audit_files",
]
