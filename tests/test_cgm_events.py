import json
import subprocess
import sys

from wellnessbox_rnd.domain.sensor_parser import normalize_sensor_genetic_payloads
from wellnessbox_rnd.schemas.cgm_events import (
    build_cgm_normalized_event_v1,
    summarize_cgm_slice_bridge_v1,
    validate_cgm_normalized_event_v1,
)


def test_build_cgm_normalized_event_v1_projects_parser_output_to_eval_and_replay() -> None:
    snapshot = normalize_sensor_genetic_payloads(
        cgm_payload={
            "avg_glucose": 6.8,
            "avg_glucose_unit": "mmol/L",
            "timeInRangePct": "78",
            "postMealSpike": True,
        }
    )

    event = build_cgm_normalized_event_v1(snapshot)

    assert event.cgm_available is True
    assert event.eval_integration_projection["cgm"].attempted == 1
    assert event.eval_integration_projection["cgm"].success == 1
    assert event.replay_bridge_projection.parser_mean_glucose_mg_dl == 122.4
    assert "mean_glucose_near_126_mg_dl_pm_10" in event.threshold_tags
    assert "post_meal_spike_flagged" in event.threshold_tags


def test_validate_cgm_normalized_event_v1_flags_projection_mismatch() -> None:
    snapshot = normalize_sensor_genetic_payloads(
        cgm_payload={
            "avg_glucose": 6.8,
            "avg_glucose_unit": "mmol/L",
            "timeInRangePct": "78",
        }
    )
    event = build_cgm_normalized_event_v1(snapshot)
    event.eval_integration_projection["cgm"].success = 0

    issues = validate_cgm_normalized_event_v1(event)

    assert "eval_projection_mismatch::success::1::0" in issues


def test_build_cgm_normalized_event_bridge_writes_expected_report(tmp_path) -> None:
    report_json = tmp_path / "cgm_bridge.json"
    report_md = tmp_path / "cgm_bridge.md"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_cgm_normalized_event_bridge.py",
            "--report-json",
            str(report_json),
            "--report-md",
            str(report_md),
        ],
        capture_output=True,
        check=False,
        cwd="C:/dev/wellnessbox-rnd",
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["valid"] is True
    assert payload["event"]["eval_integration_projection"]["cgm"]["success"] == 1
    assert (
        payload["connected_flows"]["cgm_replay_analysis"][0]
        == "replay_bridge_projection.cgm_available"
    )


def test_summarize_cgm_slice_bridge_v1_marks_threshold_edge_and_parser_failures() -> None:
    threshold_edge_event = build_cgm_normalized_event_v1(
        normalize_sensor_genetic_payloads(
            cgm_payload={
                "avg_glucose": 6.8,
                "avg_glucose_unit": "mmol/L",
                "timeInRangePct": "78",
                "postMealSpike": True,
            }
        )
    )
    malformed_event = build_cgm_normalized_event_v1(
        normalize_sensor_genetic_payloads(
            cgm_payload={
                "avg_glucose": "bad",
                "avg_glucose_unit": "mg/dL",
                "timeInRangePct": "?",
            }
        )
    )

    report = summarize_cgm_slice_bridge_v1(
        [threshold_edge_event, malformed_event],
        source_cases_path="data/samples/sensor_genetic_parser_cases_v1.json",
        case_ids=["threshold_edge", "malformed_numeric_fallback"],
    )

    assert report["case_count"] == 2
    assert report["valid_case_count"] == 2
    assert report["eval_attempted_count"] == 2
    assert report["eval_success_count"] == 1
    assert report["threshold_tag_counts"]["mean_glucose_near_126_mg_dl_pm_10"] == 1
    assert report["parser_failure_type_counts"]["cgm_mean_glucose_invalid_numeric_ignored"] == 1
    assert report["threshold_edge_case_ids"] == ["threshold_edge"]
