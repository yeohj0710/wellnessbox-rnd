import json
from pathlib import Path


def _load_json(path: str) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_synthetic_prepost_path_audit_hold_state_stays_current() -> None:
    audit = _load_json("artifacts/reports/synthetic_prepost_path_audit_v1.json")

    risk_posture = audit["risk_posture"]
    evidence = audit["evidence_snapshot"]
    overall = audit["overall_assessment"]
    pinpointed_paths = audit["pinpointed_risk_paths"]

    assert overall["verdict"] == "guarded_but_not_safe_for_strong_independent_efficacy_claim"
    assert (
        evidence["principal_blocker"]
        == "synthetic_data_circularity_and_generator_contamination"
    )

    assert risk_posture == {
        "leakage_status": "guarded_but_not_zero",
        "circularity_status": "high_risk",
        "baseline_identical_label_status": "low_risk",
        "generator_contamination_status": "high_risk",
        "frozen_eval_contamination_status": "low_risk",
        "calibration_dependence_status": "material",
        "calibration_dependence_concentration": "supported_effect_enriched_slice",
        "partition_verdict": "do_not_pool_supported_and_base_clone_validity",
    }
    assert evidence["forbidden_training_feature_count"] == 0
    assert evidence["exact_reconstruction_rate_pct"] == 100.0
    assert evidence["supported_mode_top2_match_rate_pct"] == 100.0
    assert evidence["shares_path_with_frozen_eval"] is False
    assert evidence["exact_line_overlap_count"] == 0

    assert len(pinpointed_paths) == 8
    assert {
        (item["risk_family"], item["path"])
        for item in pinpointed_paths
    } == {
        ("leakage_guard", "src/wellnessbox_rnd/training/effect_model_v1.py:169"),
        ("leakage_guard", "src/wellnessbox_rnd/training/effect_model_v1.py:1939"),
        (
            "calibration_target_coupling",
            "src/wellnessbox_rnd/training/effect_model_v1.py:1862",
        ),
        ("generator_contamination", "src/wellnessbox_rnd/synthetic/rich_longitudinal_v4.py:207"),
        ("circularity", "src/wellnessbox_rnd/synthetic/rich_longitudinal_v4.py:625"),
        ("generator_contamination", "src/wellnessbox_rnd/synthetic/rich_longitudinal_v4.py:765"),
        ("pair_contract_mixing", "src/wellnessbox_rnd/training/effect_model_v1.py:90"),
        ("frozen_eval_guard", "src/wellnessbox_rnd/training/effect_model_v1.py:1044"),
    }
