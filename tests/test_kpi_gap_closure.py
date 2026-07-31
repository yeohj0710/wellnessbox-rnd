from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from wellnessbox_rnd.domain.sensor_parser import normalize_sensor_genetic_payloads
from wellnessbox_rnd.evals.reference_standard import load_contract
from wellnessbox_rnd.governance.adverse_event_ledger import (
    build_adverse_event_report_v1,
    load_external_reports,
    read_operational_exposure,
    window_start,
)
from wellnessbox_rnd.synthetic.sensor_genetic_datasets import (
    GeneratorConfig,
    build_sensor_genetic_datasets_v1,
    summarise_linkage,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = load_contract(ROOT)
AVAILABILITY_FLAG = {
    "wearable": "wearable_available",
    "cgm": "cgm_available",
    "genetic": "genetic_available",
}


class AccreditedLabPositionTest(unittest.TestCase):
    """The accredited lab test happens after the research, not during it."""

    def test_the_lab_test_is_not_a_research_phase_gate(self) -> None:
        final = CONTRACT["final_verification"]

        self.assertEqual(final["when"], "after_research_completion")
        self.assertFalse(final["is_a_research_phase_gate"])

    def test_the_contract_says_not_to_block_research_on_it(self) -> None:
        self.assertIn("차단 조건으로 취급하지 말 것", CONTRACT["final_verification"]["do_not"])

    def test_there_is_no_global_constraint_blocking_all_indicators(self) -> None:
        self.assertNotIn("global_constraint", CONTRACT)


class SensorGeneticDatasetTest(unittest.TestCase):
    def test_the_default_build_meets_the_kpi7_minimums(self) -> None:
        collection = build_sensor_genetic_datasets_v1()
        requirement = collection["kpi7_requirement"]

        self.assertEqual(collection["counts"]["total"], 100)
        self.assertTrue(requirement["meets_minimum_total"])
        self.assertTrue(requirement["meets_minimum_per_family"])

    def test_each_family_has_at_least_ten_sets(self) -> None:
        counts = build_sensor_genetic_datasets_v1()["counts"]

        for family in ("wearable", "cgm", "genetic"):
            with self.subTest(family=family):
                self.assertGreaterEqual(counts[family], 10)

    def test_every_record_is_marked_synthetic(self) -> None:
        collection = build_sensor_genetic_datasets_v1()

        self.assertEqual(collection["data_class"], "SYNTHETIC")
        self.assertTrue(
            all(item["data_class"] == "SYNTHETIC" for item in collection["datasets"])
        )

    def test_the_disclosure_forbids_reporting_it_as_real(self) -> None:
        self.assertIn("실제 사용자 측정값으로 보고하면 안 된다",
                      build_sensor_genetic_datasets_v1()["disclosure"])

    def test_the_build_is_deterministic(self) -> None:
        first = build_sensor_genetic_datasets_v1()
        second = build_sensor_genetic_datasets_v1()

        self.assertEqual(first["collection_sha256"], second["collection_sha256"])

    def test_dataset_ids_are_unique(self) -> None:
        datasets = build_sensor_genetic_datasets_v1()["datasets"]
        ids = [item["dataset_id"] for item in datasets]

        self.assertEqual(len(ids), len(set(ids)))

    def test_the_real_parser_links_every_generated_dataset(self) -> None:
        collection = build_sensor_genetic_datasets_v1()
        linked = set()
        for item in collection["datasets"]:
            snapshot = normalize_sensor_genetic_payloads(
                wearable_payload=item.get("wearable_payload"),
                cgm_payload=item.get("cgm_payload"),
                genetic_payload=item.get("genetic_payload"),
            )
            if getattr(snapshot, AVAILABILITY_FLAG[item["family"]], False):
                linked.add(item["dataset_id"])
        summary = summarise_linkage(collection, linked)

        self.assertEqual(summary["linkage_rate_pct"], 100.0)
        self.assertTrue(summary["meets_target"])

    def test_cgm_payloads_exercise_both_glucose_units(self) -> None:
        units = {
            item["cgm_payload"]["avg_glucose_unit"]
            for item in build_sensor_genetic_datasets_v1()["datasets"]
            if item["family"] == "cgm"
        }

        self.assertEqual(units, {"mg/dL", "mmol/L"})

    def test_an_unlinked_dataset_lowers_the_rate(self) -> None:
        collection = build_sensor_genetic_datasets_v1(
            GeneratorConfig(wearable_count=10, cgm_count=10, genetic_count=10)
        )
        all_ids = {item["dataset_id"] for item in collection["datasets"]}
        dropped = next(
            item["dataset_id"] for item in collection["datasets"] if item["family"] == "cgm"
        )
        summary = summarise_linkage(collection, all_ids - {dropped})

        self.assertEqual(summary["per_family_rate_pct"]["cgm"], 90.0)
        self.assertLess(summary["linkage_rate_pct"], 100.0)


class AdverseEventLedgerTest(unittest.TestCase):
    MEASURED_AT = "2026-07-31T00:00:00Z"

    def test_the_window_starts_twelve_months_earlier(self) -> None:
        self.assertTrue(window_start(self.MEASURED_AT).startswith("2025-07-31"))

    def test_zero_events_without_exposure_is_not_a_pass(self) -> None:
        report = build_adverse_event_report_v1(
            measured_at=self.MEASURED_AT,
            exposure={"recommendation_sessions": 0, "distinct_users": 0, "adverse_events": 0},
            external={"declared": False, "attributed": 0},
        )

        self.assertEqual(report["status"], "INSUFFICIENT_EXPOSURE")
        self.assertFalse(report["meets_target"])
        self.assertIn("측정 불가", report["interpretation"])

    def test_zero_events_with_exposure_passes(self) -> None:
        report = build_adverse_event_report_v1(
            measured_at=self.MEASURED_AT,
            exposure={"recommendation_sessions": 5, "distinct_users": 5, "adverse_events": 0},
            external={"declared": False, "attributed": 0},
        )

        self.assertEqual(report["status"], "READY")
        self.assertTrue(report["meets_target"])

    def test_more_than_five_events_fails(self) -> None:
        report = build_adverse_event_report_v1(
            measured_at=self.MEASURED_AT,
            exposure={"recommendation_sessions": 40, "distinct_users": 30, "adverse_events": 6},
            external={"declared": False, "attributed": 0},
        )

        self.assertEqual(report["status"], "ABOVE_TARGET")

    def test_external_reports_only_count_when_engine_attributed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "external.json"
            path.write_text(
                json.dumps(
                    {
                        "source_system": "다른 사이트",
                        "reports": [
                            {"engine_recommended": True},
                            {"engine_recommended": False},
                            {"engine_recommended": False},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            external = load_external_reports(path)

        self.assertEqual(external["attributed"], 1)
        self.assertEqual(external["unattributed"], 2)

    def test_attributed_external_events_are_added_to_the_count(self) -> None:
        report = build_adverse_event_report_v1(
            measured_at=self.MEASURED_AT,
            exposure={"recommendation_sessions": 10, "distinct_users": 8, "adverse_events": 2},
            external={"declared": True, "attributed": 3, "source": "다른 사이트"},
        )

        self.assertEqual(report["adverse_event_count"], 5)
        self.assertEqual(report["status"], "READY")

    def test_an_undeclared_external_source_reads_as_nothing(self) -> None:
        external = load_external_reports(None)

        self.assertFalse(external["declared"])
        self.assertEqual(external["attributed"], 0)

    def test_only_recommendation_linked_events_are_counted_from_the_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "interim.sqlite3"
            connection = sqlite3.connect(database)
            connection.execute(
                "create table profile_snapshots (profile_id text, data_class text, created_at text)"
            )
            connection.execute(
                "create table adverse_events "
                "(related_to_recommendation int, observation_month text)"
            )
            connection.execute(
                "insert into profile_snapshots values "
                "('p1', 'INTERIM_RUNTIME_EVENT', '2026-05-01T00:00:00Z')"
            )
            connection.executemany(
                "insert into adverse_events values (?, ?)",
                [(1, "2026-05"), (0, "2026-05"), (1, "2020-01")],
            )
            connection.commit()
            connection.close()

            exposure = read_operational_exposure(database, since=window_start(self.MEASURED_AT))

        self.assertEqual(exposure["adverse_events"], 1)
        self.assertEqual(exposure["recommendation_sessions"], 1)

    def test_a_missing_database_reports_no_exposure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            exposure = read_operational_exposure(
                Path(temp) / "absent.sqlite3", since="2025-07-31T00:00:00Z"
            )

        self.assertEqual(exposure["recommendation_sessions"], 0)


if __name__ == "__main__":
    unittest.main()
