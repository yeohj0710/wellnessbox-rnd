from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

TARGET_FEATURE_FAMILY = "regimen_status_summary"


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_regimen_status_summary_diagnostic(
    *,
    slice_diagnostic: dict[str, object],
    slice_diagnostic_path: str | Path,
    family_decision: dict[str, object],
    family_decision_path: str | Path,
) -> dict[str, object]:
    slice_target = _as_dict(slice_diagnostic.get("slice_target"))
    decision_gate = _as_dict(family_decision.get("decision_gate"))
    example_cases = _as_list(slice_diagnostic.get("example_cases"))
    matching_cases = [case for case in example_cases if _case_has_target_family(case)]
    feature_totals = _aggregate_target_family_feature_deltas(matching_cases)
    ordered_features = _order_feature_items(feature_totals)
    family_value = _lookup_target_family_value(slice_diagnostic)

    diagnostic = {
        "audit_name": (
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_status_summary_diagnostic_v1"
        ),
        "source_artifacts": {
            "slice_diagnostic_path": str(slice_diagnostic_path),
            "family_decision_path": str(family_decision_path),
        },
        "family_target": {
            "parent_family": slice_target.get("parent_family"),
            "trajectory_mode": slice_target.get("trajectory_mode"),
            "margin_bucket": slice_target.get("margin_bucket"),
            "proxy_drop_bucket": slice_target.get("proxy_drop_bucket"),
            "chosen_feature_family": decision_gate.get("chosen_first_feature_family"),
            "expected_slice_case_count": slice_target.get("observed_case_count"),
            "observed_matching_case_count": len(matching_cases),
            "family_absolute_value": family_value,
        },
        "family_feature_summary": {
            "ordered_features": ordered_features,
            "top_absolute_feature": ordered_features[0] if ordered_features else {},
            "top_positive_features": [
                item for item in ordered_features if float(item.get("value", 0.0)) > 0.0
            ][:5],
            "top_negative_features": [
                item for item in ordered_features if float(item.get("value", 0.0)) < 0.0
            ][:5],
            "feature_case_coverage": _feature_case_coverage(matching_cases),
        },
        "readable_summary": {
            "case_digest": {
                "observed_matching_case_count": len(matching_cases),
                "expected_slice_case_count": slice_target.get("observed_case_count"),
                "family_absolute_value": family_value,
            },
            "feature_digest": {
                "chosen_feature_family": decision_gate.get("chosen_first_feature_family"),
                "top_absolute_feature": ordered_features[0] if ordered_features else {},
                "top_positive_features": [
                    item for item in ordered_features if float(item.get("value", 0.0)) > 0.0
                ][:3],
            },
        },
        "summary_findings": _build_summary_findings(
            matching_case_count=len(matching_cases),
            slice_case_count=int(slice_target.get("observed_case_count", 0)),
            family_value=family_value,
            ordered_features=ordered_features,
        ),
    }
    diagnostic["validation_issues"] = (
        validate_regimen_status_summary_diagnostic(
            diagnostic
        )
    )
    return diagnostic


def validate_regimen_status_summary_diagnostic(
    diagnostic: dict[str, object]
) -> list[str]:
    issues: list[str] = []
    family_target = _as_dict(diagnostic.get("family_target"))
    family_feature_summary = _as_dict(diagnostic.get("family_feature_summary"))
    readable_summary = _as_dict(diagnostic.get("readable_summary"))

    if family_target.get("trajectory_mode") != "threshold_duration_sensitive":
        issues.append("unexpected_trajectory_mode")
    if family_target.get("margin_bucket") != "mid_margin":
        issues.append("unexpected_margin_bucket")
    if family_target.get("proxy_drop_bucket") != "small_drop":
        issues.append("unexpected_proxy_drop_bucket")
    if family_target.get("chosen_feature_family") != TARGET_FEATURE_FAMILY:
        issues.append("unexpected_feature_family")
    if int(family_target.get("expected_slice_case_count", 0)) != int(
        family_target.get("observed_matching_case_count", 0)
    ):
        issues.append("slice_case_count_mismatch")
    if not _as_list(family_feature_summary.get("ordered_features")):
        issues.append("missing_family_feature_breakdown")
    if (
        _as_dict(_as_dict(readable_summary.get("feature_digest")).get("top_absolute_feature")).get(
            "feature"
        )
        != _as_dict(family_feature_summary.get("top_absolute_feature")).get("feature")
    ):
        issues.append("readable_summary_top_feature_mismatch")
    if not _as_list(diagnostic.get("summary_findings")):
        issues.append("summary_findings_missing")
    return issues


def render_regimen_status_summary_diagnostic_markdown(
    diagnostic: dict[str, object]
) -> str:
    lines = [
        (
            "# non-cgm threshold-duration-sensitive mid-margin "
            "small-drop regimen-status-summary diagnostic v1"
        ),
        "",
        "## readable summary",
        "",
        f"- readable_summary: `{diagnostic.get('readable_summary', {})}`",
        "",
        "## family target",
        "",
        f"- family_target: `{diagnostic.get('family_target', {})}`",
        "",
        "## family feature summary",
        "",
        f"- family_feature_summary: `{diagnostic.get('family_feature_summary', {})}`",
        "",
        "## summary findings",
        "",
    ]
    for item in _as_list(diagnostic.get("summary_findings")):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## validation",
            "",
            f"- validation_issues: `{diagnostic.get('validation_issues', [])}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_regimen_status_summary_diagnostic_files(
    *,
    diagnostic: dict[str, object],
    json_path: str | Path,
    md_path: str | Path,
) -> None:
    json_file = Path(json_path)
    md_file = Path(md_path)
    json_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(json.dumps(diagnostic, ensure_ascii=False, indent=2), encoding="utf-8")
    md_file.write_text(
        render_regimen_status_summary_diagnostic_markdown(diagnostic),
        encoding="utf-8",
    )


def _case_has_target_family(case: object) -> bool:
    feature_family_delta = _as_dict(_as_dict(case).get("feature_family_delta"))
    return TARGET_FEATURE_FAMILY in feature_family_delta


def _aggregate_target_family_feature_deltas(
    cases: list[object],
) -> dict[str, dict[str, object]]:
    signed_totals: dict[str, float] = defaultdict(float)
    abs_totals: dict[str, float] = defaultdict(float)
    for case in cases:
        for feature_name, value in _as_dict(_as_dict(case).get("feature_delta")).items():
            if _feature_belongs_to_target_family(str(feature_name)):
                signed_totals[str(feature_name)] += float(value)
                abs_totals[str(feature_name)] += abs(float(value))
    return {
        feature_name: {
            "feature": feature_name,
            "value": round(signed_totals[feature_name], 6),
            "abs_value": round(abs_totals[feature_name], 6),
        }
        for feature_name in signed_totals
    }


def _order_feature_items(
    feature_totals: dict[str, dict[str, object]]
) -> list[dict[str, object]]:
    return sorted(
        feature_totals.values(),
        key=lambda item: float(_as_dict(item).get("abs_value", 0.0)),
        reverse=True,
    )


def _feature_case_coverage(cases: list[object]) -> list[dict[str, object]]:
    coverage: dict[str, int] = defaultdict(int)
    for case in cases:
        present = {
            feature_name
            for feature_name in _as_dict(_as_dict(case).get("feature_delta"))
            if _feature_belongs_to_target_family(str(feature_name))
        }
        for feature_name in present:
            coverage[feature_name] += 1
    return sorted(
        (
            {"feature": feature_name, "case_count": count}
            for feature_name, count in coverage.items()
        ),
        key=lambda item: (int(item["case_count"]), str(item["feature"])),
        reverse=True,
    )


def _lookup_target_family_value(slice_diagnostic: dict[str, object]) -> float:
    families = _as_list(
        _as_dict(slice_diagnostic.get("feature_summary")).get("top_absolute_families")
    )
    for item in families:
        item_dict = _as_dict(item)
        if item_dict.get("family") == TARGET_FEATURE_FAMILY:
            return float(item_dict.get("value", 0.0))
    return 0.0


def _feature_belongs_to_target_family(feature_name: str) -> bool:
    return feature_name in {
        "regimen_count",
        "active_regimen_count",
        "planned_regimen_count",
        "reduced_regimen_count",
        "stopped_regimen_count",
    } or feature_name.startswith("regimen_status::")


def _build_summary_findings(
    *,
    matching_case_count: int,
    slice_case_count: int,
    family_value: float,
    ordered_features: list[dict[str, object]],
) -> list[str]:
    top_feature = _as_dict(ordered_features[0]) if ordered_features else {}
    second_feature = _as_dict(ordered_features[1]) if len(ordered_features) > 1 else {}
    return [
        (
            "The chosen family `regimen_status_summary` currently appears in "
            f"{matching_case_count}/{slice_case_count} cases inside the `small_drop` slice."
        ),
        (
            "Its current absolute family value is "
            f"{round(family_value, 6)}, led by `{top_feature.get('feature')}`."
        ),
        (
            f"`{second_feature.get('feature')}` remains the next family-internal feature "
            "to watch if the top feature does not move enough."
        ),
    ]


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_regimen_status_summary_diagnostic",
    "load_json_artifact",
    "render_regimen_status_summary_diagnostic_markdown",
    "validate_regimen_status_summary_diagnostic",
    "write_regimen_status_summary_diagnostic_files",
]
