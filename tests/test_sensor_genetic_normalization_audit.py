from pathlib import Path

from wellnessbox_rnd.evals.sensor_genetic_normalization_audit import (
    build_sensor_genetic_normalization_audit,
    render_sensor_genetic_normalization_audit_markdown,
    validate_sensor_genetic_normalization_audit,
    write_sensor_genetic_normalization_audit_files,
)


def test_build_sensor_genetic_normalization_audit_reports_consistent_path(
    tmp_path: Path,
) -> None:
    frozen_eval_dataset = tmp_path / "test_frozen_eval_sensor_genetic_join.jsonl"
    frozen_eval_dataset.write_text(
        "\n".join(
            [
                '{"case_id":"eval-019","category":"free_text_alias","integration":{"wearable":{"attempted":1,"success":1},"cgm":{"attempted":0,"success":0},"genetic":{"attempted":0,"success":0}}}',
                '{"case_id":"eval-030","category":"free_text_alias","integration":{"wearable":{"attempted":0,"success":0},"cgm":{"attempted":0,"success":0},"genetic":{"attempted":1,"success":1}}}',
                '{"case_id":"eval-034","category":"free_text_alias","integration":{"wearable":{"attempted":0,"success":0},"cgm":{"attempted":0,"success":0},"genetic":{"attempted":1,"success":0}}}',
                '{"case_id":"eval-150","category":"cgm_supported","integration":{"wearable":{"attempted":0,"success":0},"cgm":{"attempted":1,"success":1},"genetic":{"attempted":0,"success":0}}}',
                '{"case_id":"eval-151","category":"genetic_supported","integration":{"wearable":{"attempted":0,"success":0},"cgm":{"attempted":1,"success":0},"genetic":{"attempted":1,"success":1}}}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    audit = build_sensor_genetic_normalization_audit(
        parser_report={
            "case_count": 4,
            "cases_json_path": "data/samples/sensor_genetic_parser_cases_v1.json",
            "wearable_case_count": 2,
            "cgm_case_count": 2,
            "genetic_case_count": 1,
            "supported_failure_types": [
                "cgm_mean_glucose_invalid_numeric_ignored",
                "cgm_time_in_range_invalid_numeric_ignored",
            ],
            "normalized_cases": [
                {
                    "case_id": "cgm_mmol_conversion",
                    "normalized_snapshot": {
                        "cgm_available": True,
                        "mean_glucose_mg_dl": 122.4,
                        "time_in_range_pct": 78.0,
                        "post_meal_spike_concern": True,
                        "normalization_notes": [
                            "cgm_mmol_l_converted_to_mg_dl",
                            "cgm_time_in_range_string_coerced_to_float",
                        ],
                    },
                },
                {
                    "case_id": "malformed_numeric_fallback",
                    "normalized_snapshot": {
                        "cgm_available": True,
                        "mean_glucose_mg_dl": None,
                        "time_in_range_pct": None,
                        "post_meal_spike_concern": False,
                        "normalization_notes": [
                            "cgm_mean_glucose_invalid_numeric_ignored",
                            "cgm_time_in_range_invalid_numeric_ignored",
                        ],
                    },
                },
            ],
        },
        parser_report_path="parser.json",
        file_schema_report={
            "valid_fixture_results": {
                "wearable": {"passed": True},
                "cgm": {"passed": True},
                "genetic": {"passed": True},
            },
            "failure_type_examples": {
                "bad_cgm": {
                    "failure_types": ["missing_unit::cgm_summary::avg_glucose"]
                }
            },
        },
        file_schema_report_path="schema.json",
        cgm_event_report={
            "source_fixture_path": "data/samples/cgm_summary_v1.csv",
            "event": {
                "cgm_available": True,
                "mean_glucose_mg_dl": 122.4,
                "time_in_range_pct": 78.0,
                "post_meal_spike_concern": True,
                "normalization_notes": [
                    "cgm_mmol_l_converted_to_mg_dl",
                    "cgm_time_in_range_string_coerced_to_float",
                ],
            },
        },
        cgm_event_report_path="cgm_event.json",
        cgm_slice_report={
            "case_count": 2,
            "valid_case_count": 2,
            "eval_attempted_count": 2,
            "eval_success_count": 1,
            "threshold_tag_counts": {"cgm_available": 2},
            "parser_failure_type_counts": {
                "cgm_mean_glucose_invalid_numeric_ignored": 1
            },
            "threshold_edge_case_ids": ["cgm_mmol_conversion"],
            "cases": [
                {"case_id": "cgm_mmol_conversion"},
                {"case_id": "malformed_numeric_fallback"},
            ],
        },
        cgm_slice_report_path="cgm_slice.json",
        weakest_slice_audit={
                "frozen_eval_anchor": {
                    "sensor_genetic_integration_metric": {
                        "category": "free_text_alias",
                        "score": 66.666667,
                    },
                "integration_bottleneck": {
                    "modality": "cgm",
                    "rate_pct": 72.0,
                },
            },
            "required_path_components": {
                "parser_outputs": {"status": "connected"},
                "file_schema_validation": {"status": "connected"},
                "supported_parser_failure_types": {"status": "connected"},
                "CGMNormalizedEventV1": {"status": "connected"},
                "cgm_slice_bridge_summary_v1": {"status": "connected"},
            },
            "audit_path_summary": {
                "connection_edges": [
                    {"from": "file_schema_validation", "to": "parser_outputs"},
                    {"from": "parser_outputs", "to": "supported_parser_failure_types"},
                    {"from": "parser_outputs", "to": "CGMNormalizedEventV1"},
                    {"from": "CGMNormalizedEventV1", "to": "cgm_slice_bridge_summary_v1"},
                    {
                        "from": "cgm_slice_bridge_summary_v1",
                        "to": "frozen_eval.sensor_genetic_integration_rate_pct",
                    },
                ]
            },
        },
        weakest_slice_audit_path="weakest_audit.json",
        frozen_eval_dataset_path=frozen_eval_dataset,
    )

    assert audit["normalization_drift_detected"] is False
    assert audit["consistency_checks"] == {
        "cgm_parser_case_count_matches_bridge": True,
        "cgm_bridge_case_ids_match_parser_cgm_cases": True,
        "cgm_failure_types_subset_of_supported_types": True,
        "cgm_event_matches_parser_reference_case": True,
        "integration_path_connected": True,
        "integration_bottleneck_modality_is_cgm": True,
    }
    assert audit["frozen_eval_category_join"]["weakest_category"] == "free_text_alias"
    assert audit["frozen_eval_category_join"]["case_ids"] == [
        "eval-019",
        "eval-030",
        "eval-034",
    ]
    assert audit["frozen_eval_category_join"]["modality_attempted_success"]["pooled"] == {
        "attempted": 3,
        "success": 2,
        "score": 66.666667,
    }
    assert (
        audit["frozen_eval_category_join"]["cgm_bridge_applicability"]
        == "not_direct_for_this_weakest_family"
    )
    assert audit["direct_cgm_case_family_join"]["selected_family"] == "genetic_supported"
    assert audit["direct_cgm_case_family_join"]["selected_is_lowest_cgm_score_family"] is True
    assert audit["direct_cgm_case_family_join"]["modality_attempted_success"]["cgm"] == {
        "attempted": 1,
        "success": 0,
        "score": 0.0,
    }
    assert audit["direct_cgm_case_family_join"]["bridge_evidence_summary"] == {
        "bridge_case_count": 2,
        "bridge_valid_case_count": 2,
        "eval_attempted_count": 2,
        "eval_success_count": 1,
        "threshold_tag_counts": {"cgm_available": 2},
        "parser_failure_type_counts": {
            "cgm_mean_glucose_invalid_numeric_ignored": 1
        },
        "threshold_edge_case_ids": ["cgm_mmol_conversion"],
    }
    assert validate_sensor_genetic_normalization_audit(audit) == []
    assert audit["readable_summary"]["normalization_path_status"] == (
        "connected_fixture_scoped_no_drift"
    )
    assert audit["readable_summary"]["bridge_and_metric_digest"] == {
        "cgm_bridge_case_count": 2,
        "cgm_bridge_valid_case_count": 2,
        "threshold_edge_case_ids": ["cgm_mmol_conversion"],
        "weakest_metric_category": "free_text_alias",
        "weakest_metric_score": 66.666667,
        "bottleneck_modality": "cgm",
        "sensor_genetic_integration_rate_linkage_status": (
            "category_join_connected_direct_cgm_family_connected"
        ),
    }
    assert audit["readable_summary"]["component_coverage_matrix"] == [
        {
            "component": "file_schema_validation",
            "status": "connected",
            "proof": "3/3 valid fixtures",
        },
        {
            "component": "parser_outputs",
            "status": "connected",
            "proof": "4 parser smoke cases",
        },
        {
            "component": "supported_parser_failure_types",
            "status": "connected",
            "proof": "3 supported failure types",
        },
        {
            "component": "CGMNormalizedEventV1",
            "status": "connected",
            "proof": "2 parser CGM cases",
        },
        {
            "component": "cgm_slice_bridge_summary_v1",
            "status": "connected",
            "proof": "2/2 valid bridge cases",
        },
        {
            "component": "sensor_genetic_integration_rate_pct",
            "status": "connected",
            "proof": "free_text_alias @ 66.666667",
        },
    ]
    assert audit["readable_summary"]["coverage_gap_summary"] == {
        "gap_count": 5,
        "gap_classes": [
            "fixture_scope",
            "genetic_single_case",
            "single_cgm_fixture",
            "weakest_family_adjacent_only",
            "case_id_lineage_mismatch",
        ],
        "fixture_scope_only": True,
        "genetic_parser_case_count": 1,
        "cgm_event_fixture_count": 1,
        "weakest_category_case_count": 3,
        "direct_cgm_family_join_status": "connected",
        "smallest_measurable_fix": "audit_only_no_runtime_fix_required",
    }
    assert any(
        "sample-fixture scoped" in gap for gap in audit["coverage_gaps"]
    )
    assert any(
        "direct CGM family joining now exists" in gap for gap in audit["coverage_gaps"]
    )


def test_write_sensor_genetic_normalization_audit_files_creates_outputs(
    tmp_path: Path,
) -> None:
    audit = {
        "audit_name": "sensor_genetic_normalization_audit_v1",
        "normalization_coverage": {"parser_case_count": 4},
        "consistency_checks": {"integration_path_connected": True},
        "downstream_bridge_summary": {"threshold_tag_counts": {"cgm_available": 2}},
        "integration_metric_path": {
            "required_component_statuses": {"parser_outputs": "connected"}
        },
        "frozen_eval_category_join": {
            "weakest_category": "free_text_alias",
            "join_scope": "category_level",
            "case_ids": ["eval-019"],
            "modality_attempted_success": {"pooled": {"attempted": 1, "success": 1}},
            "supported_failure_taxonomy_by_modality": {},
            "related_sensor_genetic_categories": [],
        },
        "direct_cgm_case_family_join": {
            "selected_family": "genetic_supported",
            "join_scope": "case_family_level",
            "join_status": "connected",
            "case_ids": ["eval-151"],
            "modality_attempted_success": {"cgm": {"attempted": 1, "success": 0}},
            "supported_cgm_failure_taxonomy": [],
            "bridge_evidence_summary": {"bridge_case_count": 2},
        },
        "coverage_gaps": ["fixture scoped"],
        "normalization_drift_detected": False,
        "validation_issues": [],
    }

    json_path = tmp_path / "sensor_genetic_normalization_audit_v1.json"
    md_path = tmp_path / "sensor_genetic_normalization_audit_v1.md"
    write_sensor_genetic_normalization_audit_files(
        audit=audit,
        json_path=json_path,
        md_path=md_path,
    )

    assert json_path.exists()
    assert md_path.exists()
    markdown = render_sensor_genetic_normalization_audit_markdown(audit)
    assert "## readable summary" in markdown
    assert "normalization_path_status" in markdown
    assert "## consistency checks" in markdown
    assert "## integration metric path" in markdown
    assert "## direct cgm case-family join" in markdown
