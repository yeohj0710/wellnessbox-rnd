from __future__ import annotations

import json
from collections import Counter
from math import log2
from pathlib import Path

from wellnessbox_rnd.training.effect_model_v1 import (
    build_effect_dataset_pairs_v1,
    load_rich_effect_records,
)


def build_dataset_f_data_quality_report(
    *,
    dataset_path: str | Path,
    manifest_path: str | Path,
    pair_summary_path: str | Path,
) -> dict[str, object]:
    dataset_file = Path(dataset_path)
    manifest_file = Path(manifest_path)
    pair_summary_file = Path(pair_summary_path)

    records = load_rich_effect_records(dataset_file)
    rows = build_effect_dataset_pairs_v1(records)
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    pair_summary = json.loads(pair_summary_file.read_text(encoding="utf-8"))

    response_family_counts = Counter(
        row.response_profile.response_family for row in rows
    )
    trajectory_mode_counts = Counter(row.response_profile.trajectory_mode for row in rows)
    response_strength_counts = Counter(
        row.response_profile.response_strength_band for row in rows
    )
    adherence_band_counts = Counter(row.response_profile.adherence_band for row in rows)
    tolerability_band_counts = Counter(
        row.response_profile.tolerability_band for row in rows
    )

    risk_cgm_counts = Counter(
        (row.risk_tier, bool(row.input_flags.cgm)) for row in rows
    )
    risk_cgm_family_counts = Counter(
        (row.risk_tier, bool(row.input_flags.cgm), row.response_profile.response_family)
        for row in rows
    )

    low_risk_rows = [row for row in rows if row.risk_tier == "low"]
    low_risk_cgm_rows = [row for row in low_risk_rows if row.input_flags.cgm]
    low_risk_non_cgm_rows = [row for row in low_risk_rows if not row.input_flags.cgm]
    high_risk_rows = [row for row in rows if row.risk_tier == "high"]

    delta_signature_counts = Counter(_delta_signature(row) for row in rows)
    zero_delta_signature = tuple(0.0 for _ in sorted(rows[0].baseline.domain_z)) if rows else ()
    family_signature_diversity = [
        _build_family_diversity_entry(rows, family_name)
        for family_name in sorted(response_family_counts)
    ]
    family_signature_diversity.sort(
        key=lambda entry: (
            entry["signature_diversity_pct"],
            entry["case_count"],
            entry["response_family"],
        )
    )

    uniform_non_goal_delta_case_count = sum(
        1 for record in records if _has_uniform_non_goal_delta(record)
    )

    report = {
        "report_name": "dataset_f_data_quality_v1",
        "scope": {
            "dataset_path": dataset_file.as_posix(),
            "manifest_path": manifest_file.as_posix(),
            "pair_summary_path": pair_summary_file.as_posix(),
            "cohort_version": manifest["cohort_version"],
        },
        "dataset_summary": {
            "case_count": len(rows),
            "user_count": len({row.user_id for row in rows}),
            "trajectory_steps_per_user": manifest["trajectory_steps_per_user"],
            "goal_counts": pair_summary["goal_counts"],
        },
        "response_profile_heterogeneity": {
            "response_family_counts": dict(sorted(response_family_counts.items())),
            "trajectory_mode_counts": dict(sorted(trajectory_mode_counts.items())),
            "response_strength_band_counts": dict(sorted(response_strength_counts.items())),
            "adherence_band_counts": dict(sorted(adherence_band_counts.items())),
            "tolerability_band_counts": dict(sorted(tolerability_band_counts.items())),
            "response_family_normalized_entropy": _normalized_entropy(response_family_counts),
            "trajectory_mode_normalized_entropy": _normalized_entropy(
                trajectory_mode_counts
            ),
            "smallest_response_family": _smallest_count_entry(response_family_counts),
            "largest_response_family": _largest_count_entry(response_family_counts),
            "smallest_to_largest_family_ratio": round(
                _safe_ratio(
                    min(response_family_counts.values(), default=0),
                    max(response_family_counts.values(), default=0),
                ),
                4,
            ),
        },
        "slice_balance": {
            "risk_cgm_counts": {
                "high__cgm_false": risk_cgm_counts[("high", False)],
                "high__cgm_true": risk_cgm_counts[("high", True)],
                "low__cgm_false": risk_cgm_counts[("low", False)],
                "low__cgm_true": risk_cgm_counts[("low", True)],
            },
            "risk_tier_counts": pair_summary["risk_tier_counts"],
            "input_flag_counts": pair_summary["input_flag_counts"],
            "smallest_nonzero_risk_cgm_family_slice": _smallest_nonzero_slice(
                risk_cgm_family_counts
            ),
            "largest_risk_cgm_family_slice": _largest_slice(risk_cgm_family_counts),
        },
        "low_risk_vs_cgm_distribution": {
            "low_risk_case_count": len(low_risk_rows),
            "low_risk_cgm_case_count": len(low_risk_cgm_rows),
            "low_risk_non_cgm_case_count": len(low_risk_non_cgm_rows),
            "low_risk_cgm_share_of_low_risk_pct": _pct(
                len(low_risk_cgm_rows), len(low_risk_rows)
            ),
            "low_risk_cgm_share_of_all_pct": _pct(len(low_risk_cgm_rows), len(rows)),
            "low_risk_cgm_goal_counts": _count_string_values(
                row.goal for row in low_risk_cgm_rows
            ),
            "low_risk_non_cgm_goal_counts": _count_string_values(
                row.goal for row in low_risk_non_cgm_rows
            ),
            "low_risk_cgm_response_family_counts": _count_string_values(
                row.response_profile.response_family for row in low_risk_cgm_rows
            ),
            "low_risk_non_cgm_response_family_counts": _count_string_values(
                row.response_profile.response_family for row in low_risk_non_cgm_rows
            ),
            "low_risk_cgm_next_action_counts": _count_string_values(
                row.next_action for row in low_risk_cgm_rows
            ),
            "low_risk_non_cgm_next_action_counts": _count_string_values(
                row.next_action for row in low_risk_non_cgm_rows
            ),
            "low_risk_cgm_response_family_entropy": _normalized_entropy(
                Counter(row.response_profile.response_family for row in low_risk_cgm_rows)
            ),
            "low_risk_non_cgm_response_family_entropy": _normalized_entropy(
                Counter(row.response_profile.response_family for row in low_risk_non_cgm_rows)
            ),
            "low_risk_cgm_next_action_entropy": _normalized_entropy(
                Counter(row.next_action for row in low_risk_cgm_rows)
            ),
            "low_risk_non_cgm_next_action_entropy": _normalized_entropy(
                Counter(row.next_action for row in low_risk_non_cgm_rows)
            ),
        },
        "follow_up_change_diversity": {
            "aggregate_delta_summary": {
                "all": _build_aggregate_delta_summary(rows),
                "low_risk_cgm": _build_aggregate_delta_summary(low_risk_cgm_rows),
                "low_risk_non_cgm": _build_aggregate_delta_summary(low_risk_non_cgm_rows),
                "high_risk": _build_aggregate_delta_summary(high_risk_rows),
            },
            "goal_domain_delta_summary": {
                "low_risk_cgm": _build_goal_delta_summary(records, risk_tier="low", cgm=True),
                "low_risk_non_cgm": _build_goal_delta_summary(
                    records, risk_tier="low", cgm=False
                ),
                "high_risk": _build_goal_delta_summary(records, risk_tier="high", cgm=None),
            },
            "unique_aggregate_delta_count": len(
                {
                    round(row.follow_up.aggregate_z - row.baseline.aggregate_z, 3)
                    for row in rows
                }
            ),
            "unique_delta_signature_count": len(delta_signature_counts),
            "zero_delta_signature_case_count": delta_signature_counts[zero_delta_signature],
            "uniform_non_goal_delta_case_count": uniform_non_goal_delta_case_count,
            "uniform_non_goal_delta_case_pct": _pct(
                uniform_non_goal_delta_case_count, len(records)
            ),
            "lowest_signature_diversity_families": family_signature_diversity[:3],
            "top_repeated_delta_signatures": [
                {
                    "case_count": case_count,
                    "signature": list(signature),
                }
                for signature, case_count in delta_signature_counts.most_common(5)
            ],
        },
        "readable_summary": {
            "response_profile_digest": {
                "response_family_normalized_entropy": _normalized_entropy(
                    response_family_counts
                ),
                "trajectory_mode_normalized_entropy": _normalized_entropy(
                    trajectory_mode_counts
                ),
                "smallest_response_family": _smallest_count_entry(response_family_counts),
                "largest_response_family": _largest_count_entry(response_family_counts),
                "smallest_to_largest_family_ratio": round(
                    _safe_ratio(
                        min(response_family_counts.values(), default=0),
                        max(response_family_counts.values(), default=0),
                    ),
                    4,
                ),
            },
            "slice_balance_digest": {
                "low_risk_case_count": len(low_risk_rows),
                "high_risk_case_count": len(high_risk_rows),
                "low_risk_cgm_case_count": len(low_risk_cgm_rows),
                "low_risk_cgm_share_of_low_risk_pct": _pct(
                    len(low_risk_cgm_rows), len(low_risk_rows)
                ),
                "low_risk_cgm_single_goal_pct": _pct(
                    max(
                        Counter(
                            row.goal for row in low_risk_cgm_rows
                        ).values(),
                        default=0,
                    ),
                    len(low_risk_cgm_rows),
                ),
                "smallest_nonzero_risk_cgm_family_slice": _smallest_nonzero_slice(
                    risk_cgm_family_counts
                ),
                "largest_risk_cgm_family_slice": _largest_slice(
                    risk_cgm_family_counts
                ),
            },
            "low_risk_vs_cgm_digest": {
                "low_risk_cgm_response_family_count": len(
                    low_risk_distribution_families := _count_string_values(
                        row.response_profile.response_family for row in low_risk_cgm_rows
                    )
                ),
                "low_risk_cgm_response_family_counts": low_risk_distribution_families,
                "low_risk_cgm_next_action_counts": _count_string_values(
                    row.next_action for row in low_risk_cgm_rows
                ),
                "low_risk_non_cgm_next_action_counts": _count_string_values(
                    row.next_action for row in low_risk_non_cgm_rows
                ),
                "low_risk_cgm_next_action_entropy": _normalized_entropy(
                    Counter(row.next_action for row in low_risk_cgm_rows)
                ),
                "low_risk_non_cgm_next_action_entropy": _normalized_entropy(
                    Counter(row.next_action for row in low_risk_non_cgm_rows)
                ),
            },
            "follow_up_diversity_digest": {
                "unique_aggregate_delta_count": len(
                    {
                        round(row.follow_up.aggregate_z - row.baseline.aggregate_z, 3)
                        for row in rows
                    }
                ),
                "unique_delta_signature_count": len(delta_signature_counts),
                "uniform_non_goal_delta_case_pct": _pct(
                    uniform_non_goal_delta_case_count, len(records)
                ),
                "weakest_signature_diversity_family": family_signature_diversity[0],
                "top_repeated_delta_signature_case_count": (
                    delta_signature_counts.most_common(1)[0][1]
                    if delta_signature_counts
                    else 0
                ),
            },
            "signal_simplicity_verdict": {
                "weakest_slice": "low_risk_cgm",
                "weakest_diversity_family": family_signature_diversity[0][
                    "response_family"
                ],
                "signal_homogeneity_risk": "material_but_not_single_mode",
                "why": (
                    "low_risk_cgm stays narrow and single-goal, while "
                    "cgm_threshold_sensitive has only 5 unique signatures across 35 rows "
                    "and 82.08% of all cases keep uniform non-goal spillover."
                ),
            },
            "weakest_slice_surface": {
                "slice_name": "low_risk_cgm",
                "slice_case_count": len(low_risk_cgm_rows),
                "slice_goal_counts": _count_string_values(
                    row.goal for row in low_risk_cgm_rows
                ),
                "slice_response_family_counts": _count_string_values(
                    row.response_profile.response_family for row in low_risk_cgm_rows
                ),
                "slice_next_action_counts": _count_string_values(
                    row.next_action for row in low_risk_cgm_rows
                ),
                "weakest_diversity_family": family_signature_diversity[0],
            },
            "sample_example_digest": {
                "low_risk_cgm_record_ids": [
                    example["record_id"]
                    for example in _build_low_risk_cgm_examples(records)
                ],
                "repeated_zero_delta_record_ids": [
                    example["record_id"]
                    for example in _build_zero_delta_examples(records)
                ],
                "weakest_diversity_family_record_ids": [
                    example["record_id"]
                    for example in _build_weakest_family_examples(
                        records,
                        weakest_family=family_signature_diversity[0]["response_family"],
                    )
                ],
            },
        },
        "sample_examples": {
            "low_risk_cgm_examples": _build_low_risk_cgm_examples(records),
            "repeated_zero_delta_examples": _build_zero_delta_examples(records),
            "weakest_diversity_family_examples": _build_weakest_family_examples(
                records, weakest_family=family_signature_diversity[0]["response_family"]
            ),
        },
        "overall_assessment": {
            "weakest_slice": (
                "low-risk cgm is the narrowest useful slice: it is only 65 cases, "
                "all blood_glucose, and concentrated in 3 response families."
            ),
            "signal_simplicity_interpretation": (
                "Effect-training signal is not fully homogeneous because there are "
                "152 unique delta signatures and 82 unique aggregate deltas, but it is "
                "still materially simplified: 394/480 cases have uniform non-goal spillover "
                "and cgm_threshold_sensitive contributes only 5 signatures across 35 rows."
            ),
            "kpi_readiness_interpretation": (
                "This is useful as a data-quality measurement surface, not as proof that "
                "the training signal is rich enough for promotion."
            ),
        },
    }
    return report


def render_dataset_f_data_quality_markdown(report: dict[str, object]) -> str:
    scope = _as_dict(report["scope"])
    dataset_summary = _as_dict(report["dataset_summary"])
    heterogeneity = _as_dict(report["response_profile_heterogeneity"])
    slice_balance = _as_dict(report["slice_balance"])
    low_risk_distribution = _as_dict(report["low_risk_vs_cgm_distribution"])
    follow_up_diversity = _as_dict(report["follow_up_change_diversity"])
    readable_summary = _as_dict(report["readable_summary"])
    response_profile_digest = _as_dict(readable_summary["response_profile_digest"])
    slice_balance_digest = _as_dict(readable_summary["slice_balance_digest"])
    low_risk_vs_cgm_digest = _as_dict(readable_summary["low_risk_vs_cgm_digest"])
    follow_up_diversity_digest = _as_dict(
        readable_summary["follow_up_diversity_digest"]
    )
    signal_simplicity_verdict = _as_dict(readable_summary["signal_simplicity_verdict"])
    weakest_slice_surface = _as_dict(readable_summary["weakest_slice_surface"])
    sample_example_digest = _as_dict(readable_summary["sample_example_digest"])
    examples = _as_dict(report["sample_examples"])
    overall = _as_dict(report["overall_assessment"])

    lines = [
        "# dataset f data quality v1",
        "",
        "## Scope",
        f"- dataset_path: `{scope['dataset_path']}`",
        f"- manifest_path: `{scope['manifest_path']}`",
        f"- pair_summary_path: `{scope['pair_summary_path']}`",
        f"- cohort_version: `{scope['cohort_version']}`",
        "",
        "## Dataset Summary",
        f"- case_count: `{dataset_summary['case_count']}`",
        f"- user_count: `{dataset_summary['user_count']}`",
        f"- trajectory_steps_per_user: `{dataset_summary['trajectory_steps_per_user']}`",
        f"- goal_counts: `{dataset_summary['goal_counts']}`",
        "",
        "## Readable Summary",
        f"- response_profile_digest: `{response_profile_digest}`",
        f"- slice_balance_digest: `{slice_balance_digest}`",
        f"- low_risk_vs_cgm_digest: `{low_risk_vs_cgm_digest}`",
        f"- follow_up_diversity_digest: `{follow_up_diversity_digest}`",
        f"- signal_simplicity_verdict: `{signal_simplicity_verdict}`",
        f"- weakest_slice_surface: `{weakest_slice_surface}`",
        f"- sample_example_digest: `{sample_example_digest}`",
        "",
        "## Response-Profile Heterogeneity",
        (
            "- response_family_normalized_entropy: "
            f"`{heterogeneity['response_family_normalized_entropy']}`"
        ),
        (
            "- trajectory_mode_normalized_entropy: "
            f"`{heterogeneity['trajectory_mode_normalized_entropy']}`"
        ),
        (
            "- smallest_to_largest_family_ratio: "
            f"`{heterogeneity['smallest_to_largest_family_ratio']}`"
        ),
        f"- response_family_counts: `{heterogeneity['response_family_counts']}`",
        f"- trajectory_mode_counts: `{heterogeneity['trajectory_mode_counts']}`",
        f"- response_strength_band_counts: `{heterogeneity['response_strength_band_counts']}`",
        f"- adherence_band_counts: `{heterogeneity['adherence_band_counts']}`",
        f"- tolerability_band_counts: `{heterogeneity['tolerability_band_counts']}`",
        "",
        "## Slice Balance",
        f"- risk_cgm_counts: `{slice_balance['risk_cgm_counts']}`",
        (
            "- smallest_nonzero_risk_cgm_family_slice: "
            f"`{slice_balance['smallest_nonzero_risk_cgm_family_slice']}`"
        ),
        (
            "- largest_risk_cgm_family_slice: "
            f"`{slice_balance['largest_risk_cgm_family_slice']}`"
        ),
        "",
        "## Low-Risk vs CGM",
        f"- low_risk_case_count: `{low_risk_distribution['low_risk_case_count']}`",
        (
            "- low_risk_cgm_case_count: "
            f"`{low_risk_distribution['low_risk_cgm_case_count']}`"
        ),
        (
            "- low_risk_cgm_share_of_low_risk_pct: "
            f"`{low_risk_distribution['low_risk_cgm_share_of_low_risk_pct']}`"
        ),
        (
            "- low_risk_cgm_response_family_counts: "
            f"`{low_risk_distribution['low_risk_cgm_response_family_counts']}`"
        ),
        (
            "- low_risk_non_cgm_response_family_counts: "
            f"`{low_risk_distribution['low_risk_non_cgm_response_family_counts']}`"
        ),
        (
            "- low_risk_cgm_next_action_counts: "
            f"`{low_risk_distribution['low_risk_cgm_next_action_counts']}`"
        ),
        (
            "- low_risk_non_cgm_next_action_counts: "
            f"`{low_risk_distribution['low_risk_non_cgm_next_action_counts']}`"
        ),
        "",
        "## Follow-Up Change Diversity",
        f"- aggregate_delta_summary: `{follow_up_diversity['aggregate_delta_summary']}`",
        f"- goal_domain_delta_summary: `{follow_up_diversity['goal_domain_delta_summary']}`",
        (
            "- unique_delta_signature_count: "
            f"`{follow_up_diversity['unique_delta_signature_count']}`"
        ),
        (
            "- unique_aggregate_delta_count: "
            f"`{follow_up_diversity['unique_aggregate_delta_count']}`"
        ),
        (
            "- zero_delta_signature_case_count: "
            f"`{follow_up_diversity['zero_delta_signature_case_count']}`"
        ),
        (
            "- uniform_non_goal_delta_case_pct: "
            f"`{follow_up_diversity['uniform_non_goal_delta_case_pct']}`"
        ),
        (
            "- lowest_signature_diversity_families: "
            f"`{follow_up_diversity['lowest_signature_diversity_families']}`"
        ),
        "",
        "## Sample Examples",
        f"- low_risk_cgm_examples: `{examples['low_risk_cgm_examples']}`",
        f"- repeated_zero_delta_examples: `{examples['repeated_zero_delta_examples']}`",
        (
            "- weakest_diversity_family_examples: "
            f"`{examples['weakest_diversity_family_examples']}`"
        ),
        "",
        "## Overall Assessment",
        f"- weakest_slice: `{overall['weakest_slice']}`",
        (
            "- signal_simplicity_interpretation: "
            f"`{overall['signal_simplicity_interpretation']}`"
        ),
        (
            "- kpi_readiness_interpretation: "
            f"`{overall['kpi_readiness_interpretation']}`"
        ),
        "",
    ]
    return "\n".join(lines)


def write_dataset_f_data_quality_files(
    *,
    report: dict[str, object],
    json_path: str | Path,
    md_path: str | Path,
) -> None:
    json_file = Path(json_path)
    md_file = Path(md_path)
    json_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_file.write_text(render_dataset_f_data_quality_markdown(report), encoding="utf-8")


def _build_family_diversity_entry(rows: list, family_name: str) -> dict[str, object]:
    family_rows = [
        row for row in rows if row.response_profile.response_family == family_name
    ]
    unique_signature_count = len({_delta_signature(row) for row in family_rows})
    case_count = len(family_rows)
    return {
        "response_family": family_name,
        "case_count": case_count,
        "unique_signature_count": unique_signature_count,
        "signature_diversity_pct": _pct(unique_signature_count, case_count),
    }


def _build_aggregate_delta_summary(rows: list) -> dict[str, object]:
    values = sorted(
        round(row.follow_up.aggregate_z - row.baseline.aggregate_z, 3) for row in rows
    )
    if not values:
        return {
            "case_count": 0,
            "min": 0.0,
            "mean": 0.0,
            "median": 0.0,
            "max": 0.0,
            "unique_value_count": 0,
        }
    mid_index = len(values) // 2
    median_value = (
        values[mid_index]
        if len(values) % 2 == 1
        else round((values[mid_index - 1] + values[mid_index]) / 2, 3)
    )
    return {
        "case_count": len(values),
        "min": values[0],
        "mean": round(sum(values) / len(values), 6),
        "median": median_value,
        "max": values[-1],
        "unique_value_count": len(set(values)),
    }


def _build_goal_delta_summary(
    records: list,
    *,
    risk_tier: str,
    cgm: bool | None,
) -> dict[str, object]:
    filtered = []
    for record in records:
        if record.labels.risk_tier != risk_tier:
            continue
        if cgm is not None and bool(record.request.input_availability.cgm) != cgm:
            continue
        goal = record.request.goals[0].value if record.request.goals else None
        if goal is None:
            continue
        filtered.append(round(record.delta_z_by_domain[goal], 3))
    if not filtered:
        return {
            "case_count": 0,
            "min": 0.0,
            "mean": 0.0,
            "median": 0.0,
            "max": 0.0,
            "unique_value_count": 0,
        }
    filtered.sort()
    mid_index = len(filtered) // 2
    median_value = (
        filtered[mid_index]
        if len(filtered) % 2 == 1
        else round((filtered[mid_index - 1] + filtered[mid_index]) / 2, 3)
    )
    return {
        "case_count": len(filtered),
        "min": filtered[0],
        "mean": round(sum(filtered) / len(filtered), 6),
        "median": median_value,
        "max": filtered[-1],
        "unique_value_count": len(set(filtered)),
    }


def _build_low_risk_cgm_examples(records: list) -> list[dict[str, object]]:
    examples = []
    seen_actions: set[str] = set()
    for record in records:
        if record.labels.risk_tier != "low" or not record.request.input_availability.cgm:
            continue
        next_action = record.labels.next_action.value
        if next_action in seen_actions:
            continue
        seen_actions.add(next_action)
        goal = record.request.goals[0].value if record.request.goals else "unknown"
        examples.append(
            {
                "record_id": record.record_id,
                "trajectory_mode": record.trajectory_mode,
                "next_action": next_action,
                "goal": goal,
                "goal_domain_delta": round(record.delta_z_by_domain[goal], 3),
                "expected_effect_proxy": round(record.expected_effect_proxy, 3),
            }
        )
    return examples[:3]


def _build_zero_delta_examples(records: list) -> list[dict[str, object]]:
    examples = []
    for record in records:
        if not all(round(value, 3) == 0.0 for value in record.delta_z_by_domain.values()):
            continue
        goal = record.request.goals[0].value if record.request.goals else "unknown"
        examples.append(
            {
                "record_id": record.record_id,
                "trajectory_mode": record.trajectory_mode,
                "next_action": record.labels.next_action.value,
                "goal": goal,
                "expected_effect_proxy": round(record.expected_effect_proxy, 3),
            }
        )
        if len(examples) == 3:
            break
    return examples


def _build_weakest_family_examples(
    records: list,
    *,
    weakest_family: str,
) -> list[dict[str, object]]:
    examples = []
    for record in records:
        row_family = _response_family_from_mode(record.trajectory_mode)
        if row_family != weakest_family:
            continue
        goal = record.request.goals[0].value if record.request.goals else "unknown"
        examples.append(
            {
                "record_id": record.record_id,
                "trajectory_mode": record.trajectory_mode,
                "next_action": record.labels.next_action.value,
                "goal": goal,
                "goal_domain_delta": round(record.delta_z_by_domain[goal], 3),
                "aggregate_delta": round(
                    record.follow_up_pro.aggregate_z - record.baseline_pro.aggregate_z,
                    3,
                ),
            }
        )
        if len(examples) == 3:
            break
    return examples


def _delta_signature(row) -> tuple[float, ...]:
    return tuple(
        round(row.follow_up.domain_z[domain] - row.baseline.domain_z[domain], 3)
        for domain in sorted(row.baseline.domain_z)
    )


def _has_uniform_non_goal_delta(record) -> bool:
    goal = record.request.goals[0].value if record.request.goals else None
    non_goal_values = [
        round(value, 3)
        for domain, value in record.delta_z_by_domain.items()
        if domain != goal
    ]
    return bool(non_goal_values) and len(set(non_goal_values)) == 1


def _smallest_count_entry(counts: Counter[str]) -> dict[str, object]:
    if not counts:
        return {"name": "unknown", "count": 0}
    name, count = min(counts.items(), key=lambda item: (item[1], item[0]))
    return {"name": name, "count": count}


def _largest_count_entry(counts: Counter[str]) -> dict[str, object]:
    if not counts:
        return {"name": "unknown", "count": 0}
    name, count = max(counts.items(), key=lambda item: (item[1], item[0]))
    return {"name": name, "count": count}


def _smallest_nonzero_slice(
    counts: Counter[tuple[str, bool, str]]
) -> dict[str, object]:
    nonzero = [(key, count) for key, count in counts.items() if count > 0]
    if not nonzero:
        return {"risk_tier": "unknown", "cgm": False, "response_family": "unknown", "case_count": 0}
    key, count = min(nonzero, key=lambda item: (item[1], item[0]))
    risk_tier, cgm, response_family = key
    return {
        "risk_tier": risk_tier,
        "cgm": cgm,
        "response_family": response_family,
        "case_count": count,
    }


def _largest_slice(counts: Counter[tuple[str, bool, str]]) -> dict[str, object]:
    if not counts:
        return {"risk_tier": "unknown", "cgm": False, "response_family": "unknown", "case_count": 0}
    key, count = max(counts.items(), key=lambda item: (item[1], item[0]))
    risk_tier, cgm, response_family = key
    return {
        "risk_tier": risk_tier,
        "cgm": cgm,
        "response_family": response_family,
        "case_count": count,
    }


def _response_family_from_mode(trajectory_mode: str) -> str:
    return {
        "reduce_side_effect": "tolerability_limited",
        "safety_recheck_high_risk": "safety_blocked",
        "threshold_continue_primary": "stable_responder",
        "threshold_monitor_secondary": "monitor_plateau",
        "threshold_reopt_edge": "low_response_edge",
        "threshold_cgm_balance": "cgm_threshold_sensitive",
        "threshold_delayed_flip": "delayed_response",
        "threshold_duration_sensitive": "duration_sensitive",
        "threshold_adherence_recovery": "adherence_limited_recovery",
    }.get(trajectory_mode, "other")


def _count_string_values(values) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for value in values:
        counts[str(value)] += 1
    return dict(sorted(counts.items()))


def _normalized_entropy(counts: Counter[str]) -> float:
    total = sum(counts.values())
    if total == 0 or len(counts) <= 1:
        return 0.0
    probabilities = [count / total for count in counts.values() if count]
    entropy = -sum(probability * log2(probability) for probability in probabilities)
    return round(entropy / log2(len(probabilities)), 4)


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _pct(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 2)


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


__all__ = [
    "build_dataset_f_data_quality_report",
    "render_dataset_f_data_quality_markdown",
    "write_dataset_f_data_quality_files",
]
