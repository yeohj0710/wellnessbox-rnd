from scripts.compare_effect_artifact_replay import _build_slice_deltas, _distribution_delta


def test_distribution_delta_captures_added_removed_and_unchanged_actions() -> None:
    delta = _distribution_delta(
        {"continue_plan": 5, "monitor_only": 1},
        {"continue_plan": 3, "re_optimize": 2},
    )

    assert delta == {
        "continue_plan": -2,
        "monitor_only": -1,
        "re_optimize": 2,
    }


def test_build_slice_deltas_reports_overall_low_risk_and_cgm_changes() -> None:
    reference = {
        "replay_summary": {
            "learned_effect_guarded": {
                "final_policy_action_counts": {"continue_plan": 5},
                "low_risk_final_action_distribution": {"continue_plan": 4},
                "cgm_final_action_distribution": {"continue_plan": 2},
                "low_risk_disagreement_count": 8,
                "cgm_disagreement_count": 3,
                "policy_effect_override_applied_count": 0,
            },
            "learned_effect_and_policy_guarded": {
                "final_policy_action_counts": {"continue_plan": 4, "monitor_only": 1},
                "low_risk_final_action_distribution": {"continue_plan": 3, "monitor_only": 1},
                "cgm_final_action_distribution": {"continue_plan": 1, "monitor_only": 1},
                "low_risk_disagreement_count": 9,
                "cgm_disagreement_count": 4,
                "policy_effect_override_applied_count": 10,
            },
        }
    }
    candidate = {
        "replay_summary": {
            "learned_effect_guarded": {
                "final_policy_action_counts": {"continue_plan": 3, "monitor_only": 2},
                "low_risk_final_action_distribution": {"continue_plan": 2, "monitor_only": 2},
                "cgm_final_action_distribution": {"continue_plan": 1, "monitor_only": 1},
                "low_risk_disagreement_count": 7,
                "cgm_disagreement_count": 5,
                "policy_effect_override_applied_count": 0,
            },
            "learned_effect_and_policy_guarded": {
                "final_policy_action_counts": {"continue_plan": 2, "monitor_only": 3},
                "low_risk_final_action_distribution": {"continue_plan": 1, "monitor_only": 3},
                "cgm_final_action_distribution": {"monitor_only": 2},
                "low_risk_disagreement_count": 11,
                "cgm_disagreement_count": 6,
                "policy_effect_override_applied_count": 12,
            },
        }
    }

    slice_deltas = _build_slice_deltas(reference=reference, candidate=candidate)

    assert slice_deltas["learned_effect_guarded"]["overall_final_action_delta"] == {
        "continue_plan": -2,
        "monitor_only": 2,
    }
    assert slice_deltas["learned_effect_guarded"]["low_risk_disagreement_delta"] == -1
    assert slice_deltas["learned_effect_guarded"]["cgm_disagreement_delta"] == 2
    assert (
        slice_deltas["learned_effect_and_policy_guarded"][
            "policy_effect_override_applied_count_delta"
        ]
        == 2
    )
    assert slice_deltas["learned_effect_and_policy_guarded"]["cgm_final_action_delta"] == {
        "continue_plan": -1,
        "monitor_only": 1,
    }
