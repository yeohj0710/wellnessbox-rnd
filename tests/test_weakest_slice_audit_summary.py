from pathlib import Path

from wellnessbox_rnd.evals.weakest_slice_audit import (
    build_weakest_slice_frozen_eval_summary,
    render_weakest_slice_frozen_eval_summary_markdown,
    write_weakest_slice_frozen_eval_summary_files,
)


def test_build_weakest_slice_frozen_eval_summary_groups_contracts_by_family() -> None:
    summary = build_weakest_slice_frozen_eval_summary(
        audit={
            "frozen_eval_anchor": {
                "weakest_category_overall": {"category": "safety_blocked"},
                "efficacy_metric": {"category": "safety_warning"},
                "sensor_genetic_integration_metric": {"category": "free_text_alias"},
            },
            "required_path_components": {
                "PROImprovementSummaryV1_shared_event_path": {
                    "status": "connected",
                    "proof": {
                        "shared_event_schema_version": "baseline_followup_pro_event_v1",
                        "shared_event_adapter": "summarize_pro_improvement_from_event_v1",
                        "shared_event_unifier": "coerce_baseline_followup_pro_event_v1",
                        "shared_event_validator": (
                            "validate_pro_improvement_summary_from_event_v1"
                        ),
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
                            "improved_case_count": 356,
                            "worsened_case_count": 93,
                            "unchanged_case_count": 31,
                        },
                    },
                },
                "parser_outputs": {"status": "connected"},
                "file_schema_validation": {"status": "connected"},
                "supported_parser_failure_types": {
                    "status": "connected",
                    "proof": {
                        "failure_contract_version": "sensor_genetic_parser_failure_contract_v1",
                        "parser_supported_failure_types": [
                            "cgm_mean_glucose_invalid_numeric_ignored"
                        ],
                        "parser_supported_failure_taxonomy": [
                            {
                                "failure_type": "cgm_mean_glucose_invalid_numeric_ignored",
                                "stage": "parser_normalization_fallback",
                                "modality": "cgm",
                                "family": "invalid_numeric_ignored",
                                "field": "mean_glucose",
                            }
                        ],
                        "schema_failure_type_examples": [
                            "missing_unit::cgm_summary::avg_glucose"
                        ],
                        "schema_failure_type_taxonomy": [
                            {
                                "failure_type": "missing_unit::cgm_summary::avg_glucose",
                                "stage": "file_schema_validation",
                                "modality": "cgm",
                                "family": "missing_unit",
                                "field": "avg_glucose",
                            }
                        ],
                        "combined_failure_type_count": 2,
                        "taxonomy_stage_counts": {
                            "file_schema_validation": 1,
                            "parser_normalization_fallback": 1,
                        },
                        "taxonomy_modality_counts": {"cgm": 2},
                        "taxonomy_family_counts": {
                            "invalid_numeric_ignored": 1,
                            "missing_unit": 1,
                        },
                        "taxonomy_field_counts": {
                            "avg_glucose": 1,
                            "mean_glucose": 1,
                        },
                        "taxonomy_ambiguity_count": 0,
                        "taxonomy_field_ambiguity_count": 0,
                    },
                },
                "CGMNormalizedEventV1": {
                    "status": "connected",
                    "proof": {
                        "threshold_tags": ["cgm_available"],
                        "eval_attempted": 1,
                        "eval_success": 1,
                    },
                },
                "cgm_slice_bridge_summary_v1": {
                    "status": "connected",
                    "proof": {
                        "case_count": 2,
                        "eval_success_count": 1,
                        "threshold_edge_case_ids": ["case-1"],
                        "parser_failure_type_counts": {
                            "cgm_mean_glucose_invalid_numeric_ignored": 1
                        },
                    },
                },
                "FollowUpTransitionEventV1": {
                    "status": "connected",
                    "proof": {
                        "case_count": 480,
                        "valid_case_count": 480,
                        "not_directly_connected_in_this_contract": [
                            "sensor_genetic_normalized_event"
                        ],
                    },
                },
                "NextActionWorkflowEventV1": {
                    "status": "connected",
                    "proof": {
                        "response_status": "ok",
                        "next_action": "start_plan",
                        "projected_workflow_state": "recommendation_ready",
                        "issue_count": 0,
                        "branch_fixtures": [
                            {
                                "request_fixture_path": (
                                    "data/samples/api_recommend_start_plan_request_v1.json"
                                ),
                                "response_status": "ok",
                                "next_action": "start_plan",
                                "projected_workflow_state": "recommendation_ready",
                                "issue_count": 0,
                            },
                            {
                                "request_fixture_path": (
                                    "data/samples/api_recommend_blocked_collect_more_input_request_v1.json"
                                ),
                                "response_status": "blocked",
                                "next_action": "collect_more_input",
                                "projected_workflow_state": "baseline_questionnaire_due",
                                "issue_count": 0,
                            },
                        ],
                    },
                },
                "structured_safety_evidence_linkage": {
                    "status": "connected",
                    "proof": {
                        "response_status": "blocked",
                        "safety_status": "blocked",
                        "next_action": "trigger_safety_recheck",
                        "rule_count": 2,
                        "reference_backed_rule_count": 0,
                        "issue_count": 0,
                    },
                },
            },
            "structured_safety_evidence_linkage_audit": {
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
                    "category_case_count": 1,
                    "case_ids": ["eval-003"],
                    "actual_status_counts": {"ok": 1},
                    "actual_next_action_counts": {"start_plan": 1},
                    "fixture_branches": [
                        {
                            "request_fixture_path": (
                                "data/samples/api_recommend_start_plan_request_v1.json"
                            ),
                            "response_status": "ok",
                            "next_action": "start_plan",
                            "projected_workflow_state": "recommendation_ready",
                            "issue_count": 0,
                            "matched_case_count": 1,
                            "matched_case_ids": ["eval-003"],
                        },
                        {
                            "request_fixture_path": (
                                "data/samples/api_recommend_blocked_collect_more_input_request_v1.json"
                            ),
                            "response_status": "blocked",
                            "next_action": "collect_more_input",
                            "projected_workflow_state": "baseline_questionnaire_due",
                            "issue_count": 0,
                            "matched_case_count": 0,
                            "matched_case_ids": [],
                        },
                    ],
                    "fixture_response_status_seen_in_family": False,
                    "fixture_next_action_seen_in_family": False,
                    "matched_case_count": 1,
                    "matched_case_ids": ["eval-003"],
                    "coverage_pct": 100.0,
                    "unmatched_next_action_counts": {},
                },
                "frozen_eval_category_join": {
                    "family": "safety_blocked",
                    "join_status": "connected",
                    "category_case_count": 1,
                    "case_ids": ["eval-003"],
                    "actual_status_counts": {"ok": 1},
                    "actual_next_action_counts": {"start_plan": 1},
                    "observed_rule_id_counts": {"INTAKE-SURVEY-001": 1},
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
            },
            "audit_path_summary": {
                "remaining_gaps": [
                    "parser and CGM bridge proofs are sample-fixture based.",
                    (
                        "FollowUpTransitionEventV1 still declares "
                        "sensor_genetic_normalized_event as not directly connected "
                        "inside its own contract."
                    ),
                    "Structured safety evidence linkage proof is still request-fixture scoped.",
                ]
            },
        },
        audit_path="audit.json",
        eval_report={
            "dataset_path": "data/frozen_eval/frozen_eval_v1.jsonl",
            "case_count": 256,
            "case_results": [
                {"category": "free_text_alias"},
                {"category": "free_text_alias"},
                {
                    "case_id": "eval-003",
                    "category": "safety_blocked",
                    "actual": {
                        "status": "ok",
                        "next_action": "start_plan",
                        "rule_ids": ["INTAKE-SURVEY-001"],
                    },
                },
                {"category": "bone_joint"},
            ],
            "weakest_slice_summary": {
                "weakest_category_overall": {
                    "category": "safety_blocked",
                    "metrics": ["next_action_accuracy_pct"],
                },
                "weakest_category_by_metric": {
                    "sensor_genetic_integration_rate_pct": {"category": "free_text_alias"},
                    "next_action_accuracy_pct": {"category": "safety_blocked"},
                    "efficacy_improvement_pp": {"category": "safety_warning"},
                    "recommendation_coverage_pct": {"category": "bone_joint"},
                },
            },
        },
        eval_report_path="eval_report.json",
    )

    family_map = {item["family"]: item for item in summary["case_family_summaries"]}
    assert summary["readable_summary"] == {
        "family_contract_matrix": [
            {
                "family": "bone_joint",
                "case_count": 1,
                "coverage_status": "empty",
                "contracts_filled": [],
                "contracts_missing": [],
            },
            {
                "family": "free_text_alias",
                "case_count": 2,
                "coverage_status": "connected",
                "contracts_filled": [
                    "CGMNormalizedEventV1",
                    "cgm_slice_bridge_summary_v1",
                    "file_schema_validation",
                    "parser_outputs",
                    "supported_parser_failure_types",
                ],
                "contracts_missing": [],
            },
            {
                "family": "safety_blocked",
                "case_count": 1,
                "coverage_status": "connected",
                "contracts_filled": [
                    "FollowUpTransitionEventV1",
                    "NextActionWorkflowEventV1",
                    "structured_safety_evidence_linkage",
                ],
                "contracts_missing": [],
            },
            {
                "family": "safety_warning",
                "case_count": 0,
                "coverage_status": "connected",
                "contracts_filled": [
                    "PROImprovementSummaryV1_shared_event_path"
                ],
                "contracts_missing": [],
            },
        ],
        "parser_failure_digest": {
            "family": "free_text_alias",
            "combined_failure_type_count": 2,
            "taxonomy_stage_counts": {
                "file_schema_validation": 1,
                "parser_normalization_fallback": 1,
            },
            "taxonomy_modality_counts": {"cgm": 2},
            "taxonomy_family_counts": {
                "invalid_numeric_ignored": 1,
                "missing_unit": 1,
            },
            "taxonomy_field_counts": {
                "avg_glucose": 1,
                "mean_glucose": 1,
            },
            "taxonomy_field_ambiguity_count": 0,
            "parser_supported_failure_types": [
                "cgm_mean_glucose_invalid_numeric_ignored"
            ],
            "schema_failure_type_examples": [
                "missing_unit::cgm_summary::avg_glucose"
            ],
        },
        "cgm_bridge_digest": {
            "family": "free_text_alias",
            "threshold_tags": ["cgm_available"],
            "eval_attempted": 1,
            "eval_success": 1,
            "slice_case_count": 2,
            "slice_eval_success_count": 1,
            "threshold_edge_case_ids": ["case-1"],
            "parser_failure_type_counts": {
                "cgm_mean_glucose_invalid_numeric_ignored": 1
            },
        },
        "workflow_safety_digest": {
            "family": "safety_blocked",
            "followup_not_directly_connected": [
                "sensor_genetic_normalized_event"
            ],
            "next_action_branch_fixture_count": 2,
            "next_action_category_join_coverage_pct": 100.0,
            "safety_reference_linkage_status": "deterministic_only",
            "safety_rule_overlap_count": 0,
            "safety_rule_count": 0,
        },
        "still_empty_weakest_families": ["bone_joint"],
    }
    assert family_map["free_text_alias"]["coverage_status"] == "connected"
    assert "supported_parser_failure_types" in family_map["free_text_alias"]["contracts_filled"]
    assert family_map["free_text_alias"]["parser_failure_types"]["combined_failure_type_count"] == 2
    assert family_map["free_text_alias"]["parser_failure_types"]["taxonomy_stage_counts"] == {
        "file_schema_validation": 1,
        "parser_normalization_fallback": 1,
    }
    assert family_map["free_text_alias"]["parser_failure_types"]["taxonomy_field_counts"] == {
        "avg_glucose": 1,
        "mean_glucose": 1,
    }
    assert family_map["free_text_alias"]["parser_failure_types"]["taxonomy_ambiguity_count"] == 0
    assert (
        family_map["free_text_alias"]["parser_failure_types"][
            "taxonomy_field_ambiguity_count"
        ]
        == 0
    )
    assert family_map["safety_blocked"]["workflow_safety_linkage"]["next_action_workflow"][
        "next_action"
    ] == "start_plan"
    assert len(
        family_map["safety_blocked"]["workflow_safety_linkage"]["next_action_workflow"][
            "branch_fixtures"
        ]
    ) == 2
    assert family_map["safety_blocked"]["workflow_safety_linkage"][
        "next_action_workflow_category_join"
    ] == {
        "family": "safety_blocked",
        "join_status": "connected",
        "category_case_count": 1,
        "case_ids": ["eval-003"],
        "actual_status_counts": {"ok": 1},
        "actual_next_action_counts": {"start_plan": 1},
        "fixture_branches": [
            {
                "request_fixture_path": "data/samples/api_recommend_start_plan_request_v1.json",
                "response_status": "ok",
                "next_action": "start_plan",
                "projected_workflow_state": "recommendation_ready",
                "issue_count": 0,
                "matched_case_count": 1,
                "matched_case_ids": ["eval-003"],
            },
            {
                "request_fixture_path": (
                    "data/samples/api_recommend_blocked_collect_more_input_request_v1.json"
                ),
                "response_status": "blocked",
                "next_action": "collect_more_input",
                "projected_workflow_state": "baseline_questionnaire_due",
                "issue_count": 0,
                "matched_case_count": 0,
                "matched_case_ids": [],
            },
        ],
        "fixture_response_status_seen_in_family": False,
        "fixture_next_action_seen_in_family": False,
        "matched_case_count": 1,
        "matched_case_ids": ["eval-003"],
        "coverage_pct": 100.0,
        "unmatched_next_action_counts": {},
    }
    assert family_map["safety_blocked"]["structured_safety_evidence_audit"] == {
        "path_status": "connected",
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
            "category_case_count": 1,
            "case_ids": ["eval-003"],
            "actual_status_counts": {"ok": 1},
            "actual_next_action_counts": {"start_plan": 1},
            "fixture_branches": [
                {
                    "request_fixture_path": "data/samples/api_recommend_start_plan_request_v1.json",
                    "response_status": "ok",
                    "next_action": "start_plan",
                    "projected_workflow_state": "recommendation_ready",
                    "issue_count": 0,
                    "matched_case_count": 1,
                    "matched_case_ids": ["eval-003"],
                },
                {
                    "request_fixture_path": (
                        "data/samples/api_recommend_blocked_collect_more_input_request_v1.json"
                    ),
                    "response_status": "blocked",
                    "next_action": "collect_more_input",
                    "projected_workflow_state": "baseline_questionnaire_due",
                    "issue_count": 0,
                    "matched_case_count": 0,
                    "matched_case_ids": [],
                },
            ],
            "fixture_response_status_seen_in_family": False,
            "fixture_next_action_seen_in_family": False,
            "matched_case_count": 1,
            "matched_case_ids": ["eval-003"],
            "coverage_pct": 100.0,
            "unmatched_next_action_counts": {},
        },
        "frozen_eval_category_join": {
            "family": "safety_blocked",
            "join_status": "connected",
            "category_case_count": 1,
            "case_ids": ["eval-003"],
            "actual_status_counts": {"ok": 1},
            "actual_next_action_counts": {"start_plan": 1},
            "observed_rule_id_counts": {"INTAKE-SURVEY-001": 1},
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
    assert family_map["safety_warning"]["coverage_status"] == "connected"
    assert family_map["safety_warning"]["contracts_filled"] == [
        "PROImprovementSummaryV1_shared_event_path"
    ]
    assert family_map["safety_warning"]["pro_improvement_path"] == {
        "shared_event_schema_version": "baseline_followup_pro_event_v1",
        "shared_event_adapter": "summarize_pro_improvement_from_event_v1",
        "shared_event_unifier": "coerce_baseline_followup_pro_event_v1",
        "shared_event_validator": "validate_pro_improvement_summary_from_event_v1",
        "single_path_status": {
            "event_adapter_only_public_entrypoint": True,
            "snapshot_pair_entrypoint_internal_only": True,
            "record_or_event_payloads_unified_by": "coerce_baseline_followup_pro_event_v1",
        },
        "shared_event_path_proof": {
            "valid_case_count": 480,
            "invalid_case_count": 0,
        },
        "synthetic_dataset_summary": {
            "improved_case_count": 356,
            "worsened_case_count": 93,
            "unchanged_case_count": 31,
        },
    }
    assert family_map["safety_warning"]["structured_safety_evidence_audit"] == {
        "path_status": "missing",
        "missing_reason": (
            "No structured safety evidence contract bundle is mapped to this "
            "weakest safety family in the current audit layer."
        ),
    }
    assert summary["structured_safety_evidence_completeness"] == {
        "linked_family_count": 1,
        "missing_family_count": 1,
        "linked_case_count": 1,
        "missing_case_count": 0,
        "linked_families": ["safety_blocked"],
        "missing_families": ["safety_warning"],
        "reference_linkage_status_counts": {"deterministic_only": 1},
    }
    assert family_map["bone_joint"]["coverage_status"] == "empty"
    assert "safety_warning" not in summary["still_empty_weakest_families"]
    assert "bone_joint" in summary["still_empty_weakest_families"]


def test_write_weakest_slice_frozen_eval_summary_files_creates_outputs(tmp_path: Path) -> None:
    summary = {
        "summary_name": "weakest_slice_frozen_eval_summary_v1",
        "source_artifacts": {
            "audit_path": "audit.json",
            "eval_report_path": "eval_report.json",
        },
        "frozen_eval_anchor": {
            "dataset_path": "data/frozen_eval/frozen_eval_v1.jsonl",
            "case_count": 256,
            "weakest_category_overall": {"category": "safety_blocked", "metrics": ["x"]},
            "weakest_category_by_metric": {
                "efficacy_improvement_pp": {"category": "safety_warning"}
            },
        },
        "case_family_summaries": [
            {
                "family": "free_text_alias",
                "case_count": 3,
                "weakest_metrics": ["sensor_genetic_integration_rate_pct"],
                "coverage_status": "connected",
                "contracts_filled": ["parser_outputs"],
                "contracts_expected_for_current_audit": ["parser_outputs"],
                "parser_failure_types": {},
                "cgm_bridge_summary": {},
                "pro_improvement_path": {},
                "workflow_safety_linkage": {},
                "structured_safety_evidence_audit": {},
                "remaining_gaps": [],
            }
        ],
        "structured_safety_evidence_completeness": {
            "linked_family_count": 0,
            "missing_family_count": 0,
            "linked_case_count": 0,
            "missing_case_count": 0,
            "linked_families": [],
            "missing_families": [],
            "reference_linkage_status_counts": {},
        },
        "still_empty_weakest_families": ["bone_joint"],
        "audit_layer_gaps": ["fixture scoped"],
    }

    output_json = tmp_path / "weakest_slice_summary.json"
    output_md = tmp_path / "weakest_slice_summary.md"
    write_weakest_slice_frozen_eval_summary_files(
        summary,
        output_json_path=output_json,
        output_md_path=output_md,
    )

    assert output_json.exists()
    assert output_md.exists()
    markdown = render_weakest_slice_frozen_eval_summary_markdown(summary)
    assert "readable digest" in markdown
    assert "parser and cgm digest" in markdown
    assert "workflow and safety digest" in markdown
    assert "case family coverage" in markdown
    assert "weakest_efficacy_metric_category" in markdown
    assert "structured safety evidence completeness" in markdown
    assert "still_empty_weakest_families" in markdown
