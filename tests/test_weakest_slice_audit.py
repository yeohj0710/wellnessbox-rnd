from pathlib import Path

from wellnessbox_rnd.evals.weakest_slice_audit import (
    build_weakest_slice_frozen_eval_audit,
    render_weakest_slice_frozen_eval_audit_markdown,
    validate_structured_safety_evidence_linkage_audit,
    write_weakest_slice_frozen_eval_audit_files,
)


def test_build_weakest_slice_frozen_eval_audit_connects_required_components() -> None:
    audit = build_weakest_slice_frozen_eval_audit(
        eval_report={
            "dataset_path": "data/frozen_eval/frozen_eval_v1.jsonl",
            "case_count": 256,
            "case_results": [
                {
                    "case_id": "eval-001",
                    "category": "safety_blocked",
                    "actual": {
                        "status": "blocked",
                        "next_action": "collect_more_input",
                        "rule_ids": ["INTAKE-SURVEY-001", "SAFETY-PREG-001"],
                    },
                },
                {
                    "case_id": "eval-002",
                    "category": "safety_blocked",
                    "actual": {
                        "status": "ok",
                        "next_action": "start_plan",
                        "rule_ids": ["INTAKE-SURVEY-001", "SAFETY-ANTICOAG-001"],
                    },
                },
            ],
            "summary": {
                "sensor_genetic_integration_rate_pct": {
                    "score": 90.0,
                    "details": {
                        "bottleneck_modality": "cgm",
                        "bottleneck_rate_pct": 72.0,
                        "modality_breakdown": {"cgm": {"attempted": 50, "success": 36}},
                    },
                }
            },
            "weakest_slice_summary": {
                "weakest_category_overall": {
                    "category": "safety_blocked",
                    "metrics": ["next_action_accuracy_pct"],
                    "case_count": 17,
                },
                "weakest_category_by_metric": {
                    "sensor_genetic_integration_rate_pct": {
                        "category": "free_text_alias",
                        "score": 66.6,
                    },
                "safety_reference_accuracy_pct": {
                    "category": "safety_blocked",
                    "score": 98.0,
                },
                "efficacy_improvement_pp": {
                    "category": "safety_warning",
                    "score": 4.0,
                },
                "next_action_accuracy_pct": {
                    "category": "safety_blocked",
                    "score": 94.0,
                    },
                },
            },
        },
        eval_report_path="eval_report.json",
        pro_report={
            "improvement_metric": {
                "shared_event_schema_version": "baseline_followup_pro_event_v1",
                "shared_event_adapter": "summarize_pro_improvement_from_event_v1",
                "shared_event_unifier": "coerce_baseline_followup_pro_event_v1",
                "shared_event_validator": "validate_pro_improvement_summary_from_event_v1",
                "single_path_status": {
                    "event_adapter_only_public_entrypoint": True,
                    "snapshot_pair_entrypoint_internal_only": True,
                    "record_or_event_payloads_unified_by": (
                        "coerce_baseline_followup_pro_event_v1"
                    ),
                },
                "shared_event_path_proof": {
                    "valid_case_count": 480,
                    "invalid_case_count": 0,
                },
                "synthetic_dataset_summary": {
                    "improved_case_count": 10,
                    "worsened_case_count": 2,
                    "unchanged_case_count": 1,
                },
            }
        },
        pro_report_path="pro_report.json",
        parser_report={
            "failure_contract_version": "sensor_genetic_parser_failure_contract_v1",
            "case_count": 4,
            "wearable_case_count": 2,
            "cgm_case_count": 2,
            "genetic_case_count": 1,
            "cases_json_path": "data/samples/sensor_genetic_parser_cases_v1.json",
            "supported_failure_types": [
                "cgm_mean_glucose_invalid_numeric_ignored",
                "cgm_time_in_range_invalid_numeric_ignored",
            ],
        },
        parser_report_path="parser_report.json",
        file_schema_report={
            "valid_fixture_results": {
                "wearable_summary_csv": {"passed": True},
                "cgm_summary_csv": {"passed": True},
                "gene_profile_json": {"passed": True},
            },
            "failure_type_examples": {
                "bad_cgm": {"failure_types": ["missing_unit::cgm_summary::avg_glucose"]},
            },
        },
        file_schema_report_path="schema_report.json",
        cgm_event_report={
            "valid": True,
            "validation_issues": [],
            "event": {
                "threshold_tags": ["cgm_available"],
                "eval_integration_projection": {"cgm": {"attempted": 1, "success": 1}},
            },
        },
        cgm_event_report_path="cgm_event.json",
        cgm_slice_report={
            "case_count": 2,
            "eval_success_count": 1,
            "invalid_case_count": 0,
            "threshold_edge_case_ids": ["case-1"],
            "parser_failure_type_counts": {"cgm_mean_glucose_invalid_numeric_ignored": 1},
            "connected_flows": {"cgm_weakest_slice_audit": ["eval_success_count"]},
        },
        cgm_slice_report_path="cgm_slice.json",
        followup_report={
            "case_count": 480,
            "valid_case_count": 480,
            "invalid_case_count": 0,
            "not_directly_connected_in_this_contract": ["sensor_genetic_normalized_event"],
        },
        followup_report_path="followup.json",
        next_action_report={
            "request_fixture_path": "data/samples/api_recommend_start_plan_request_v1.json",
            "response_status": "ok",
            "next_action": "start_plan",
            "projected_workflow_state": "recommendation_ready",
            "issue_count": 0,
        },
        next_action_report_path="next_action.json",
        next_action_blocked_report={
            "request_fixture_path": (
                "data/samples/api_recommend_blocked_collect_more_input_request_v1.json"
            ),
            "response_status": "blocked",
            "next_action": "collect_more_input",
            "projected_workflow_state": "baseline_questionnaire_due",
            "issue_count": 0,
        },
        next_action_blocked_report_path="next_action_blocked.json",
        safety_report={
            "request_fixture_path": (
                "data/samples/api_recommend_structured_safety_block_request_v1.json"
            ),
            "response_status": "blocked",
            "safety_status": "blocked",
            "next_action": "trigger_safety_recheck",
            "rule_count": 2,
            "reference_backed_rule_count": 0,
            "issue_count": 0,
        },
        safety_report_path="safety.json",
    )

    assert audit["audit_path_summary"]["all_required_components_present"] is True
    assert (
        audit["required_path_components"]["supported_parser_failure_types"]["proof"][
            "combined_failure_type_count"
        ]
        == 3
    )
    assert audit["required_path_components"]["supported_parser_failure_types"]["proof"][
        "taxonomy_stage_counts"
    ] == {
        "file_schema_validation": 1,
        "parser_normalization_fallback": 2,
    }
    assert audit["required_path_components"]["supported_parser_failure_types"]["proof"][
        "taxonomy_modality_counts"
    ] == {"cgm": 3}
    assert audit["required_path_components"]["supported_parser_failure_types"]["proof"][
        "taxonomy_family_counts"
    ] == {
        "invalid_numeric_ignored": 2,
        "missing_unit": 1,
    }
    assert audit["required_path_components"]["supported_parser_failure_types"]["proof"][
        "taxonomy_field_counts"
    ] == {
        "avg_glucose": 1,
        "mean_glucose": 1,
        "time_in_range": 1,
    }
    assert audit["required_path_components"]["supported_parser_failure_types"]["proof"][
        "taxonomy_ambiguity_count"
    ] == 0
    assert audit["required_path_components"]["supported_parser_failure_types"]["proof"][
        "taxonomy_field_ambiguity_count"
    ] == 0
    assert audit["required_path_components"]["PROImprovementSummaryV1_shared_event_path"] == {
        "status": "connected",
        "artifact_path": "pro_report.json",
        "proof": {
            "shared_event_schema_version": "baseline_followup_pro_event_v1",
            "shared_event_adapter": "summarize_pro_improvement_from_event_v1",
            "shared_event_unifier": "coerce_baseline_followup_pro_event_v1",
            "shared_event_validator": "validate_pro_improvement_summary_from_event_v1",
            "single_path_status": {
                "event_adapter_only_public_entrypoint": True,
                "snapshot_pair_entrypoint_internal_only": True,
                "record_or_event_payloads_unified_by": (
                    "coerce_baseline_followup_pro_event_v1"
                ),
            },
            "shared_event_path_proof": {
                "valid_case_count": 480,
                "invalid_case_count": 0,
            },
            "synthetic_dataset_summary": {
                "improved_case_count": 10,
                "worsened_case_count": 2,
                "unchanged_case_count": 1,
            },
        },
        "connected_to": ["weakest_slice_summary", "frozen_eval.efficacy_improvement_pp"],
    }
    assert audit["required_path_components"]["CGMNormalizedEventV1"]["status"] == "connected"
    assert any(
        "sensor_genetic_normalized_event" in gap
        for gap in audit["audit_path_summary"]["remaining_gaps"]
    )
    assert audit["frozen_eval_anchor"]["integration_bottleneck"]["modality"] == "cgm"
    assert audit["frozen_eval_anchor"]["efficacy_metric"] == {
        "category": "safety_warning",
        "score": 4.0,
    }
    assert audit["structured_safety_evidence_linkage_audit"] == {
        "weakest_safety_families": ["safety_blocked", "safety_warning"],
        "families_with_structured_safety_path": ["safety_blocked"],
        "families_missing_structured_safety_path": ["safety_warning"],
        "linkage_path": [
            "structured_safety_evidence_linkage",
            "NextActionWorkflowEventV1",
            "FollowUpTransitionEventV1",
            "weakest_slice_summary",
            "frozen_eval.safety_reference_accuracy_pct",
        ],
        "reference_linkage_status": "deterministic_only",
        "reference_linkage_completeness": {
            "rule_count": 2,
            "reference_backed_rule_count": 0,
            "reference_coverage_pct": 0.0,
            "issue_count": 0,
        },
        "next_action_workflow_category_join": {
            "family": "safety_blocked",
            "join_status": "connected",
            "category_case_count": 2,
            "case_ids": ["eval-001", "eval-002"],
            "actual_status_counts": {"blocked": 1, "ok": 1},
            "actual_next_action_counts": {
                "collect_more_input": 1,
                "start_plan": 1,
            },
            "fixture_branches": [
                {
                    "request_fixture_path": "data/samples/api_recommend_start_plan_request_v1.json",
                    "response_status": "ok",
                    "next_action": "start_plan",
                    "projected_workflow_state": "recommendation_ready",
                    "issue_count": 0,
                    "matched_case_count": 1,
                    "matched_case_ids": ["eval-002"],
                },
                {
                    "request_fixture_path": (
                        "data/samples/api_recommend_blocked_collect_more_input_request_v1.json"
                    ),
                    "response_status": "blocked",
                    "next_action": "collect_more_input",
                    "projected_workflow_state": "baseline_questionnaire_due",
                    "issue_count": 0,
                    "matched_case_count": 1,
                    "matched_case_ids": ["eval-001"],
                },
            ],
            "fixture_response_status_seen_in_family": True,
            "fixture_next_action_seen_in_family": True,
            "matched_case_count": 2,
            "matched_case_ids": ["eval-001", "eval-002"],
            "coverage_pct": 100.0,
            "unmatched_next_action_counts": {},
        },
        "frozen_eval_category_join": {
            "family": "safety_blocked",
            "join_status": "connected",
            "category_case_count": 2,
            "case_ids": ["eval-001", "eval-002"],
            "actual_status_counts": {"blocked": 1, "ok": 1},
            "actual_next_action_counts": {
                "collect_more_input": 1,
                "start_plan": 1,
            },
            "observed_rule_id_counts": {
                "INTAKE-SURVEY-001": 2,
                "SAFETY-ANTICOAG-001": 1,
                "SAFETY-PREG-001": 1,
            },
            "fixture_response_status": "blocked",
            "fixture_next_action": "trigger_safety_recheck",
            "fixture_rule_ids": [],
            "fixture_rule_count": 0,
            "fixture_rule_overlap_ids": [],
            "fixture_rule_overlap_count": 0,
            "fixture_next_action_seen_in_family": False,
            "workflow_contract_next_action": "start_plan",
            "workflow_contract_next_action_seen_in_family": True,
        },
    }
    assert audit["weakest_slice_frozen_eval_compatible_audit_path"] == {
        "path_name": "parser_to_cgm_to_workflow_to_safety_weakest_slice_path_v1",
        "path_status": "bridge_connected_with_direct_gap",
        "frozen_eval_compatible": True,
        "sensor_genetic_anchor": {
            "metric": "sensor_genetic_integration_rate_pct",
            "category": "free_text_alias",
            "score": 66.6,
            "bottleneck_modality": "cgm",
            "bottleneck_rate_pct": 72.0,
        },
        "weakest_overall_anchor": {
            "category": "safety_blocked",
            "metrics": ["next_action_accuracy_pct"],
            "case_count": 17,
        },
        "path_nodes": [
            {
                "name": "file_schema_validation",
                "status": "connected",
                "artifact_path": "schema_report.json",
            },
            {
                "name": "parser_outputs",
                "status": "connected",
                "artifact_path": "parser_report.json",
            },
            {
                "name": "supported_parser_failure_types",
                "status": "connected",
                "artifact_path": "parser_report.json",
            },
            {
                "name": "CGMNormalizedEventV1",
                "status": "connected",
                "artifact_path": "cgm_event.json",
            },
            {
                "name": "cgm_slice_bridge_summary_v1",
                "status": "connected",
                "artifact_path": "cgm_slice.json",
            },
            {
                "name": "FollowUpTransitionEventV1",
                "status": "connected",
                "artifact_path": "followup.json",
            },
            {
                "name": "NextActionWorkflowEventV1",
                "status": "connected",
                "artifact_path": "next_action.json",
            },
            {
                "name": "structured_safety_evidence_linkage",
                "status": "connected",
                "artifact_path": "safety.json",
            },
            {
                "name": "weakest_slice_summary",
                "status": "connected",
                "artifact_path": "frozen_eval.eval_report.weakest_slice_summary",
            },
        ],
        "path_edges": [
            {
                "from": "file_schema_validation",
                "to": "parser_outputs",
                "status": "connected",
                "edge_type": "contract_edge",
                "evidence": {
                    "connection_basis": "schema fixtures constrain parser entry formats",
                },
            },
            {
                "from": "parser_outputs",
                "to": "supported_parser_failure_types",
                "status": "connected",
                "edge_type": "contract_edge",
                "evidence": {
                    "connection_basis": (
                        "parser normalization notes materialize supported failure families"
                    ),
                },
            },
            {
                "from": "supported_parser_failure_types",
                "to": "CGMNormalizedEventV1",
                "status": "connected",
                "edge_type": "contract_edge",
                "evidence": {
                    "connection_basis": (
                        "supported malformed-input families explain normalized CGM event limits"
                    ),
                },
            },
            {
                "from": "CGMNormalizedEventV1",
                "to": "cgm_slice_bridge_summary_v1",
                "status": "connected",
                "edge_type": "contract_edge",
                "evidence": {"explicit_flow_present": True},
            },
            {
                "from": "cgm_slice_bridge_summary_v1",
                "to": "FollowUpTransitionEventV1",
                "status": "bridge_only",
                "edge_type": "cross_contract_bridge",
                "evidence": {
                    "not_directly_connected_in_this_contract": [
                        "sensor_genetic_normalized_event"
                    ],
                },
            },
            {
                "from": "FollowUpTransitionEventV1",
                "to": "NextActionWorkflowEventV1",
                "status": "connected",
                "edge_type": "contract_edge",
                "evidence": {
                    "category_join_status": "connected",
                    "category_coverage_pct": 100.0,
                },
            },
            {
                "from": "NextActionWorkflowEventV1",
                "to": "structured_safety_evidence_linkage",
                "status": "connected",
                "edge_type": "contract_edge",
                "evidence": {
                    "safety_family_join_status": "connected",
                    "fixture_rule_overlap_count": 0,
                    "fixture_rule_count": 0,
                },
            },
            {
                "from": "structured_safety_evidence_linkage",
                "to": "weakest_slice_summary",
                "status": "connected",
                "edge_type": "contract_edge",
                "evidence": {
                    "overall_weakest_category": "safety_blocked",
                    "safety_category_join_status": "connected",
                },
            },
        ],
        "connected_edge_count": 7,
        "bridge_only_edge_count": 1,
        "missing_edge_count": 0,
        "direct_gap_edges": [
            {
                "from": "cgm_slice_bridge_summary_v1",
                "to": "FollowUpTransitionEventV1",
                "status": "bridge_only",
                "edge_type": "cross_contract_bridge",
                "evidence": {
                    "not_directly_connected_in_this_contract": [
                        "sensor_genetic_normalized_event"
                    ],
                },
            }
        ],
    }
    assert not any(
        "NextActionWorkflowEventV1 now joins weakest safety_blocked cases" in gap
        for gap in audit["audit_path_summary"]["remaining_gaps"]
    )
    assert validate_structured_safety_evidence_linkage_audit(audit) == []


def test_write_weakest_slice_frozen_eval_audit_files_creates_json_and_markdown(
    tmp_path: Path,
) -> None:
    audit = {
        "audit_name": "weakest_slice_frozen_eval_audit_v1",
        "frozen_eval_anchor": {
            "eval_report_path": "eval_report.json",
            "dataset_path": "data/frozen_eval/frozen_eval_v1.jsonl",
            "case_count": 256,
            "weakest_category_overall": {"category": "safety_blocked", "metrics": ["x"]},
            "efficacy_metric": {"category": "safety_warning", "score": 4.0},
            "sensor_genetic_integration_metric": {"category": "free_text_alias", "score": 66.6},
            "integration_bottleneck": {"modality": "cgm", "rate_pct": 72.0},
        },
        "required_path_components": {
            "PROImprovementSummaryV1_shared_event_path": {
                "status": "connected",
                "artifact_path": "pro_report.json",
                "proof": {"shared_event_path_proof": {"valid_case_count": 480}},
                "connected_to": ["frozen_eval.efficacy_improvement_pp"],
            },
            "parser_outputs": {
                "status": "connected",
                "artifact_path": "parser_report.json",
                "proof": {"case_count": 4},
                "connected_to": ["CGMNormalizedEventV1"],
            }
        },
        "audit_path_summary": {
            "all_required_components_present": True,
            "frozen_eval_compatible": True,
            "connected_component_count": 1,
            "missing_component_count": 0,
            "connection_edges": [
                {"from": "parser_outputs", "to": "CGMNormalizedEventV1", "why": "proof"}
            ],
            "remaining_gaps": ["fixture scoped"],
        },
    }

    output_json = tmp_path / "weakest_slice_audit.json"
    output_md = tmp_path / "weakest_slice_audit.md"
    write_weakest_slice_frozen_eval_audit_files(
        audit,
        output_json_path=output_json,
        output_md_path=output_md,
    )

    assert output_json.exists()
    assert output_md.exists()
    markdown = render_weakest_slice_frozen_eval_audit_markdown(audit)
    assert "weakest_efficacy_metric_category" in markdown
    assert "required path components" in markdown
    assert "structured safety evidence completeness" in markdown
    assert "weakest-slice compatible audit path" in markdown
    assert "next_action_workflow_category_join" in markdown
    assert "remaining gaps" in markdown
