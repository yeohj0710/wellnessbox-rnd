from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_module():
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "diagnose_current_cgm_continue_plan_cases.py"
    )
    spec = spec_from_file_location(
        "diagnose_current_cgm_continue_plan_cases",
        script_path,
    )
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_classify_final_blocker_family_threshold_edge_case():
    module = _load_module()
    step_diagnostic = {
        "gating_reason": {"current_prior_band": "monitor_only_band"},
        "deterministic_fallback": {
            "effect_fallback_active": False,
            "policy_fallback_active": False,
        },
        "safety_ceiling": {"active": False},
        "margin_snapshot": {
            "distance_to_monitor_flip": 0.12,
            "reoptimize_minus_continue_after_priors": -0.4,
        },
    }

    blocker_family = module._classify_final_blocker_family(
        step_diagnostic=step_diagnostic
    )

    assert blocker_family == "threshold_edge_monitor_band_continue"


def test_classify_final_blocker_family_large_monitor_gap_case():
    module = _load_module()
    step_diagnostic = {
        "gating_reason": {"current_prior_band": "continue_plan_band"},
        "deterministic_fallback": {
            "effect_fallback_active": False,
            "policy_fallback_active": False,
        },
        "safety_ceiling": {"active": False},
        "margin_snapshot": {
            "distance_to_monitor_flip": 0.46,
            "reoptimize_minus_continue_after_priors": -0.23,
        },
    }

    blocker_family = module._classify_final_blocker_family(
        step_diagnostic=step_diagnostic
    )

    assert blocker_family == "outside_monitor_band_large_monitor_gap"


def test_build_blocker_family_summary_counts_are_sorted():
    module = _load_module()
    cases = [
        {"final_blocker_family": "outside_monitor_band_large_monitor_gap"},
        {"final_blocker_family": "threshold_edge_monitor_band_continue"},
        {"final_blocker_family": "outside_monitor_band_large_monitor_gap"},
    ]

    summary = module._build_blocker_family_summary(cases)

    assert list(summary) == [
        "outside_monitor_band_large_monitor_gap",
        "threshold_edge_monitor_band_continue",
    ]
    assert summary["outside_monitor_band_large_monitor_gap"] == 2
    assert summary["threshold_edge_monitor_band_continue"] == 1
