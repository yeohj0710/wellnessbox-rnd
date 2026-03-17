import json
from pathlib import Path

from wellnessbox_rnd.models.effect_model_v1 import (
    EffectFeatureVectorizerV1,
    build_effect_feature_dict_v1,
    predict_aggregate_delta_v1,
    predict_domain_deltas_v1,
    predict_policy_effect_proxy_v1,
)
from wellnessbox_rnd.synthetic.rich_longitudinal_v2 import generate_rich_synthetic_cohort
from wellnessbox_rnd.synthetic.rich_longitudinal_v4 import generate_rich_synthetic_cohort_v4
from wellnessbox_rnd.training.effect_model_v1 import (
    _effect_validation_selection_score_v1,
    _is_better_effect_validation_candidate_v1,
    build_effect_dataset_manifest_v1,
    build_effect_dataset_pair_split_manifest_v1,
    build_effect_dataset_pairs_v1,
    build_effect_dataset_split_manifest_v1,
    build_effect_dataset_training_view_contract_v1,
    build_effect_feature_schema_v1,
    build_effect_validation_selection_summary_v1,
    evaluate_effect_model_v1,
    fit_effect_model_v1,
    split_effect_records_by_user_v1,
    summarize_effect_dataset_pairs_v1,
    summarize_effect_training_feature_family_boundary_v1,
    validate_effect_dataset_pair_split_manifest_v1,
    validate_effect_dataset_pairs_v1,
    validate_effect_dataset_training_view_contract_v1,
    validate_effect_feature_schema_v1,
    validate_effect_training_feature_family_boundary_v1,
)


def test_effect_feature_vectorizer_v1_is_deterministic() -> None:
    records = generate_rich_synthetic_cohort(seed=3101, user_count=16)
    rows = [build_effect_feature_dict_v1(record) for record in records[:8]]

    vectorizer = EffectFeatureVectorizerV1.fit(rows)

    assert vectorizer.feature_names == sorted(vectorizer.feature_names)
    assert vectorizer.transform(rows) == vectorizer.transform(rows)


def test_split_effect_records_by_user_v1_keeps_user_ids_disjoint() -> None:
    records = generate_rich_synthetic_cohort(seed=3102, user_count=24)

    split = split_effect_records_by_user_v1(records, seed=3102)

    train_users = {record.user_id for record in split.train}
    val_users = {record.user_id for record in split.val}
    test_users = {record.user_id for record in split.test}
    assert train_users.isdisjoint(val_users)
    assert train_users.isdisjoint(test_users)
    assert val_users.isdisjoint(test_users)


def test_effect_model_v1_beats_zero_baseline_on_rich_synthetic_test_split() -> None:
    records = generate_rich_synthetic_cohort(seed=3103, user_count=96)
    split = split_effect_records_by_user_v1(records, seed=3103)

    artifact, _ = fit_effect_model_v1(split.train, split.val, seed=3103)
    metrics = evaluate_effect_model_v1(artifact, split.test)
    domain_prediction = predict_domain_deltas_v1(artifact, split.test[0])
    aggregate_prediction = predict_aggregate_delta_v1(artifact, split.test[0])
    feature_schema = build_effect_feature_schema_v1(artifact)

    assert artifact.feature_names
    assert set(domain_prediction) == set(artifact.output_names)
    assert isinstance(aggregate_prediction, float)
    assert metrics.aggregate_mae < metrics.zero_baseline_aggregate_mae
    assert metrics.mean_domain_mae < metrics.zero_baseline_mean_domain_mae
    assert feature_schema["feature_count"] == len(artifact.feature_names)


def test_effect_model_v1_enforces_dataset_f_training_view_in_training_features() -> None:
    records = generate_rich_synthetic_cohort_v4(seed=603, user_count=72)
    split = split_effect_records_by_user_v1(records, seed=20260311)

    artifact, _ = fit_effect_model_v1(split.train, split.val, seed=20260311)
    feature_schema = build_effect_feature_schema_v1(artifact)
    enforcement = feature_schema["training_view_enforcement"]

    assert enforcement["contract_version"] == "dataset_f_effect_training_view_v1"
    assert enforcement["forbidden_feature_count"] == 0
    assert enforcement["forbidden_feature_names_present"] == []
    assert "adherence_proxy" not in artifact.feature_names
    assert "side_effect_proxy" not in artifact.feature_names
    assert "risk_tier_low" not in artifact.feature_names
    assert "risk_tier_moderate" not in artifact.feature_names
    assert "risk_tier_high" not in artifact.feature_names
    assert "baseline_aggregate_z" in artifact.feature_names
    assert "trajectory_step" in artifact.feature_names
    assert "day_index" in artifact.feature_names


def test_effect_model_v1_feature_family_boundary_audit_matches_allowed_training_view() -> None:
    records = generate_rich_synthetic_cohort_v4(seed=605, user_count=72)
    split = split_effect_records_by_user_v1(records, seed=20260311)

    artifact, _ = fit_effect_model_v1(split.train, split.val, seed=20260311)
    audit = summarize_effect_training_feature_family_boundary_v1(artifact)
    schema = build_effect_feature_schema_v1(artifact)

    assert validate_effect_training_feature_family_boundary_v1(artifact) == []
    assert audit["classified_feature_count"] == len(artifact.feature_names)
    assert audit["unknown_feature_count"] == 0
    assert audit["allowed_source_family_counts"]["goal"] == 10
    assert audit["allowed_source_family_counts"]["baseline"] == 10
    assert audit["allowed_source_family_counts"]["input_flags"] == 4
    assert audit["allowed_source_family_counts"]["period"] == 2
    assert audit["allowed_source_family_counts"]["recommended_set"] >= 30
    assert audit["forbidden_leakage_feature_count"] == 0
    assert audit["forbidden_leakage_features_present"] == {}
    assert schema["training_feature_family_audit"]["allowed_source_family_counts"] == (
        audit["allowed_source_family_counts"]
    )
    assert schema["training_feature_family_audit"]["unknown_features"] == []


def test_effect_model_v1_feature_family_boundary_validator_rejects_leakage_prone_features() -> None:
    artifact = type(
        "Artifact",
        (),
        {
            "feature_names": [
                "goal::blood_glucose",
                "baseline::blood_glucose",
                "wearable_available",
                "trajectory_step",
                "regimen::berberine",
                "dose::berberine",
                "adherence_proxy",
                "risk_tier_low",
                "follow_up::blood_glucose",
                "response_family::cgm_threshold_sensitive",
            ]
        },
    )()

    audit = summarize_effect_training_feature_family_boundary_v1(artifact)
    issues = validate_effect_training_feature_family_boundary_v1(artifact)

    assert audit["forbidden_leakage_family_counts"]["adherence_proxy"] == 1
    assert audit["forbidden_leakage_family_counts"]["risk_tier"] == 1
    assert audit["forbidden_leakage_family_counts"]["follow_up"] == 1
    assert audit["forbidden_leakage_family_counts"]["response_profile"] == 1
    assert any(
        "forbidden leakage-prone feature families present" in issue for issue in issues
    )


def test_effect_feature_schema_validator_accepts_current_training_view_boundary() -> None:
    feature_schema = json.loads(
        Path(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_heterogeneity_candidate_feature_schema.json"
        ).read_text(encoding="utf-8")
    )

    issues = validate_effect_feature_schema_v1(feature_schema)

    assert issues == []
    assert feature_schema["training_view_enforcement"]["contract_version"] == (
        "dataset_f_effect_training_view_v1"
    )
    assert feature_schema["training_view_enforcement"]["forbidden_feature_count"] == 0
    assert feature_schema["training_feature_family_audit"]["forbidden_leakage_feature_count"] == 0


def test_effect_feature_schema_validator_rejects_boundary_drift_and_forbidden_regression() -> None:
    schema = {
        "feature_count": 4,
        "feature_names": [
            "goal::blood_glucose",
            "baseline::blood_glucose",
            "follow_up::blood_glucose",
            "risk_tier_low",
        ],
        "training_view_enforcement": {
            "contract_version": "dataset_f_effect_training_view_v1",
            "training_input_allowed_fields": [
                "goal",
                "baseline",
                "recommended_set",
            ],
            "forbidden_feature_names_present": [],
            "forbidden_feature_count": 0,
        },
        "training_feature_family_audit": {
            "allowed_source_fields": [
                "goal",
                "baseline",
                "input_flags",
                "recommended_set",
                "period",
            ],
            "allowed_source_family_counts": {
                "goal": 1,
                "baseline": 1,
                "input_flags": 0,
                "recommended_set": 0,
                "period": 0,
            },
            "classified_feature_count": 2,
            "unknown_features": [],
            "unknown_feature_count": 0,
            "forbidden_leakage_family_counts": {
                "follow_up": 1,
                "adverse_event": 0,
                "expected_effect_proxy": 0,
                "adherence_proxy": 0,
                "side_effect_proxy": 0,
                "next_action": 0,
                "risk_tier": 1,
                "response_profile": 0,
            },
            "forbidden_leakage_feature_count": 1,
        },
    }

    issues = validate_effect_feature_schema_v1(schema)

    assert "training_input_allowed_fields_drifted_from_contract" in issues
    assert "training_view_and_feature_family_allowed_fields_mismatch" in issues
    assert "forbidden_leakage_feature_count_mismatch" in issues
    assert "feature_family_audit_does_not_cover_feature_names" in issues


def test_effect_model_v1_calibrates_policy_proxy_better_than_raw_aggregate() -> None:
    records = generate_rich_synthetic_cohort(seed=3104, user_count=96)
    split = split_effect_records_by_user_v1(records, seed=3104)

    artifact, _ = fit_effect_model_v1(split.train, split.val, seed=3104)
    calibrated_errors = [
        abs(predict_policy_effect_proxy_v1(artifact, record) - record.expected_effect_proxy)
        for record in split.test
    ]
    raw_errors = [
        abs(predict_aggregate_delta_v1(artifact, record) - record.expected_effect_proxy)
        for record in split.test
    ]

    assert artifact.policy_proxy_slope >= 0.0
    assert sum(calibrated_errors) / len(calibrated_errors) < sum(raw_errors) / len(raw_errors)


def test_effect_validation_selection_profile_tracks_allowed_slice_summary() -> None:
    records = generate_rich_synthetic_cohort_v4(seed=604, user_count=72)
    split = split_effect_records_by_user_v1(records, seed=20260311)

    artifact, _ = fit_effect_model_v1(
        split.train,
        split.val,
        seed=20260311,
        alpha_grid=(0.01, 0.1, 1.0, 5.0, 10.0, 15.0, 20.0),
        validation_selection_profile="allowed_slice_balance_v1",
        validation_selection_tolerance=0.0001,
    )
    val_metrics = evaluate_effect_model_v1(artifact, split.val)
    selection_summary = build_effect_validation_selection_summary_v1(
        artifact,
        val_records=split.val,
        val_metrics=val_metrics,
        profile="allowed_slice_balance_v1",
    )

    assert artifact.validation_selection_profile == "allowed_slice_balance_v1"
    assert artifact.validation_selection_tolerance == 0.0001
    assert artifact.validation_selection_score > 0.0
    assert artifact.validation_selection_summary["selected_alpha"] == artifact.alpha
    assert len(artifact.validation_selection_summary["alpha_search"]) == 7
    assert selection_summary["slice_summary"]["case_count"] == len(split.val)
    assert selection_summary["slice_summary"]["cgm_case_count"] > 0
    assert selection_summary["slice_summary"]["non_cgm_case_count"] > 0
    assert selection_summary["slice_summary"]["mean_goal_slice_aggregate_mae"] > 0.0
    assert "blood_glucose" in selection_summary["slice_summary"]["goal_slice_aggregate_mae"]
    assert build_effect_feature_schema_v1(artifact)["validation_selection"]["profile"] == (
        "allowed_slice_balance_v1"
    )


def test_effect_validation_selection_profile_tracks_allowed_slice_heterogeneity() -> None:
    records = generate_rich_synthetic_cohort_v4(seed=606, user_count=72)
    split = split_effect_records_by_user_v1(records, seed=20260311)

    artifact, _ = fit_effect_model_v1(
        split.train,
        split.val,
        seed=20260311,
        alpha_grid=(0.01, 0.1, 1.0, 5.0, 10.0, 15.0, 20.0, 30.0),
        validation_selection_profile="allowed_slice_heterogeneity_v1",
        validation_selection_tolerance=0.0,
    )
    val_metrics = evaluate_effect_model_v1(artifact, split.val)
    selection_summary = build_effect_validation_selection_summary_v1(
        artifact,
        val_records=split.val,
        val_metrics=val_metrics,
        profile="allowed_slice_heterogeneity_v1",
    )

    assert artifact.validation_selection_profile == "allowed_slice_heterogeneity_v1"
    assert artifact.validation_selection_tolerance == 0.0
    assert artifact.validation_selection_summary["selected_alpha"] == artifact.alpha
    assert len(artifact.validation_selection_summary["alpha_search"]) == 8
    assert selection_summary["slice_summary"]["low_risk_case_count"] > 0
    assert selection_summary["slice_summary"]["low_risk_cgm_case_count"] > 0
    assert (
        selection_summary["slice_summary"]["mean_low_risk_response_family_aggregate_mae"]
        > 0.0
    )
    assert (
        selection_summary["slice_summary"][
            "worst_low_risk_cgm_response_family_aggregate_mae"
        ]
        > 0.0
    )
    assert "cgm_threshold_sensitive" in selection_summary["slice_summary"][
        "low_risk_cgm_response_family_aggregate_mae"
    ]


def test_effect_validation_selection_tolerance_prefers_higher_alpha_on_near_ties() -> None:
    assert _is_better_effect_validation_candidate_v1(
        candidate_score=0.01029,
        candidate_alpha=20.0,
        best_score=0.010225,
        best_alpha=15.0,
        tolerance=0.0001,
    )
    assert not _is_better_effect_validation_candidate_v1(
        candidate_score=0.0104,
        candidate_alpha=20.0,
        best_score=0.010225,
        best_alpha=15.0,
        tolerance=0.0001,
    )
    assert _effect_validation_selection_score_v1(
        val_metrics=type(
            "Metrics",
            (),
            {
                "aggregate_mae": 0.008208,
            },
        )(),
        slice_summary={
            "mean_goal_slice_aggregate_mae": 0.008069,
            "cgm_aggregate_mae": 0.00874,
            "non_cgm_aggregate_mae": 0.008107,
        },
        profile="allowed_slice_balance_v1",
    ) > 0.008208
    assert _effect_validation_selection_score_v1(
        val_metrics=type(
            "Metrics",
            (),
            {
                "aggregate_mae": 0.008208,
            },
        )(),
        slice_summary={
            "mean_goal_slice_aggregate_mae": 0.008069,
            "cgm_aggregate_mae": 0.00874,
            "non_cgm_aggregate_mae": 0.008107,
            "mean_low_risk_response_family_aggregate_mae": 0.0088,
            "worst_low_risk_response_family_aggregate_mae": 0.0104,
            "mean_low_risk_cgm_response_family_aggregate_mae": 0.0092,
            "worst_low_risk_cgm_response_family_aggregate_mae": 0.0111,
        },
        profile="allowed_slice_heterogeneity_v1",
    ) > _effect_validation_selection_score_v1(
        val_metrics=type(
            "Metrics",
            (),
            {
                "aggregate_mae": 0.008208,
            },
        )(),
        slice_summary={
            "mean_goal_slice_aggregate_mae": 0.008069,
            "cgm_aggregate_mae": 0.00874,
            "non_cgm_aggregate_mae": 0.008107,
        },
        profile="allowed_slice_balance_v1",
    )


def test_build_effect_dataset_manifest_v1_reports_split_ready_dataset_f() -> None:
    records = generate_rich_synthetic_cohort_v4(seed=602, user_count=72)

    split = split_effect_records_by_user_v1(records, seed=20260311)
    split_manifest = build_effect_dataset_split_manifest_v1(split, seed=20260311)
    manifest = build_effect_dataset_manifest_v1(
        records,
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        seed=20260311,
        split_manifest_path="artifacts/reports/dataset_f_effect_prepost_split_manifest_v1.json",
    )

    assert manifest["dataset_id"] == "dataset_f_effect_prepost_v1"
    assert manifest["case_count"] == len(records)
    assert manifest["user_count"] == len({record.user_id for record in records})
    assert manifest["generator_audit"]["present"] is True
    assert manifest["generator_audit"]["validation_issues"] == []
    assert manifest["split_summary"]["train"]["record_count"] == len(split.train)
    assert manifest["split_summary"]["val"]["record_count"] == len(split.val)
    assert manifest["split_summary"]["test"]["record_count"] == len(split.test)
    assert (
        manifest["distribution_summary"]["threshold_edge_counts"][
            "low_risk_cgm_effect_proxy_0_14_to_0_24"
        ]
        > 0
    )
    assert (
        manifest["distribution_summary"]["threshold_edge_counts"]["low_risk_reoptimize"]
        > 0
    )
    assert split_manifest["splits"]["train"]["record_count"] + split_manifest["splits"]["val"][
        "record_count"
    ] + split_manifest["splits"]["test"]["record_count"] == len(records)


def test_build_effect_dataset_pairs_v1_exports_required_prepost_fields() -> None:
    records = generate_rich_synthetic_cohort_v4(seed=602, user_count=72)

    rows = build_effect_dataset_pairs_v1(records)
    issues = validate_effect_dataset_pairs_v1(rows)
    training_view_contract = build_effect_dataset_training_view_contract_v1()
    training_view_issues = validate_effect_dataset_training_view_contract_v1(rows)
    summary = summarize_effect_dataset_pairs_v1(
        rows,
        dataset_path="artifacts/datasets/dataset_f_effect_prepost_pairs_v1.jsonl",
        source_dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        split_manifest_path="artifacts/reports/dataset_f_effect_prepost_pairs_split_manifest_v1.json",
        seed=20260311,
    )
    split_manifest = build_effect_dataset_pair_split_manifest_v1(rows, seed=20260311)

    assert len(rows) == len(records)
    assert issues == []
    assert training_view_issues == []
    assert rows[0].baseline.domain_z
    assert rows[0].follow_up.domain_z
    assert rows[0].recommended_set
    assert rows[0].period.days_from_baseline >= 0
    assert isinstance(rows[0].adverse_event, bool)
    assert rows[0].input_flags.survey is True
    assert isinstance(rows[0].input_flags.cgm, bool)
    assert rows[0].provenance.source_request_id
    assert rows[0].provenance.trajectory_mode
    assert rows[0].response_profile.trajectory_mode == rows[0].provenance.trajectory_mode
    assert rows[0].response_profile.response_family
    assert summary["case_count"] == len(records)
    assert summary["adverse_event_count"] > 0
    assert summary["schema_key_coverage_pct"]["top_level"]["recommended_set"] == 100.0
    assert summary["schema_key_coverage_pct"]["top_level"]["input_flags"] == 100.0
    assert summary["schema_key_coverage_pct"]["top_level"]["provenance"] == 100.0
    assert summary["schema_key_coverage_pct"]["top_level"]["response_profile"] == 100.0
    assert summary["schema_key_coverage_pct"]["nested"]["period"]["days_from_baseline"] == 100.0
    assert summary["schema_key_coverage_pct"]["nested"]["input_flags"]["survey"] == 100.0
    assert summary["schema_key_coverage_pct"]["nested"]["provenance"]["trajectory_mode"] == 100.0
    assert (
        summary["schema_key_coverage_pct"]["nested"]["response_profile"][
            "response_family"
        ]
        == 100.0
    )
    assert summary["dataset_provenance"]["shares_path_with_frozen_eval"] is False
    assert training_view_contract["contract_version"] == "dataset_f_effect_training_view_v1"
    assert summary["training_view_contract"]["issues"] == []
    assert summary["training_view_contract"]["training_input_allowed_fields"] == [
        "goal",
        "baseline",
        "input_flags",
        "recommended_set",
        "period",
    ]
    assert summary["training_view_contract"]["training_input_forbidden_fields"] == [
        "follow_up",
        "adverse_event",
        "expected_effect_proxy",
        "adherence_proxy",
        "side_effect_proxy",
        "next_action",
        "risk_tier",
        "response_profile",
    ]
    assert summary["response_profile_summary"]["response_family_counts"][
        "cgm_threshold_sensitive"
    ] > 0
    assert summary["response_profile_summary"]["response_family_counts"][
        "adherence_limited_recovery"
    ] > 0
    assert summary["response_profile_summary"]["response_family_counts"][
        "tolerability_limited"
    ] > 0
    assert summary["response_profile_summary"]["response_family_counts"][
        "safety_blocked"
    ] > 0
    assert summary["response_profile_summary"]["tolerability_band_counts"]["elevated"] > 0
    assert split_manifest["splits"]["train"]["pair_count"] + split_manifest["splits"]["val"][
        "pair_count"
    ] + split_manifest["splits"]["test"]["pair_count"] == len(rows)
    split_validation = validate_effect_dataset_pair_split_manifest_v1(
        rows,
        split_manifest,
        source_dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
    )
    assert split_validation["issues"] == []
    assert split_validation["pair_coverage"]["dataset_pair_count"] == len(rows)
    assert split_validation["pair_coverage"]["manifest_pair_count"] == len(rows)
    assert split_validation["user_coverage"]["dataset_user_count"] == len(
        {row.user_id for row in rows}
    )
    assert split_validation["split_disjointness"]["pair_overlap_counts"] == {
        "test__train": 0,
        "test__val": 0,
        "train__val": 0,
    }
    assert split_validation["split_disjointness"]["user_overlap_counts"] == {
        "test__train": 0,
        "test__val": 0,
        "train__val": 0,
    }
    assert split_validation["contamination_safeguards"]["shares_path_with_frozen_eval"] is False
    assert summary["split_validation"]["issues"] == []
