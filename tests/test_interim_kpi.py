import pytest

from wellnessbox_rnd.interim.contracts import DataClass
from wellnessbox_rnd.interim.importer import import_interim_package
from wellnessbox_rnd.interim.kpi import (
    device_linkage_metrics,
    evaluate_proxy_kpis,
    linkage_macro_rate,
    recommendation_reference_coverage,
)
from wellnessbox_rnd.interim.manifest import APPROVED_SOURCE_ROOT
from wellnessbox_rnd.interim.store import InterimStore

PACKAGE_ROOT = APPROVED_SOURCE_ROOT


def test_recommendation_score_uses_reference_set_denominator_from_plan_page_26() -> None:
    score = recommendation_reference_coverage(
        reference={"vitamin_d", "magnesium"},
        predicted={"vitamin_d", "omega3", "zinc"},
    )

    assert score == 50.0


def test_recommendation_score_rejects_empty_reference_set() -> None:
    with pytest.raises(ValueError, match="recommendation_reference_set_required"):
        recommendation_reference_coverage(reference=set(), predicted=set())


def test_linkage_uses_equal_weight_macro_average_across_w_c_g() -> None:
    result = linkage_macro_rate(
        [
            {"source": "W", "success": True},
            {"source": "W", "success": True},
            {"source": "C", "success": False},
            {"source": "G", "success": True},
        ]
    )

    assert result.source_rates == {"W": 100.0, "C": 0.0, "G": 100.0}
    assert result.aggregate == 200.0 / 3.0


def test_production_device_linkage_is_class_scoped_and_macro_averaged(tmp_path) -> None:
    store = InterimStore(tmp_path / "production-linkage.sqlite3")
    store.migrate()
    with store.transaction() as connection:
        for session_id, source, success, data_class, deduplicated in [
            ("w1", "W", 1, "PRODUCTION_DEVICE_SESSION", 0),
            ("w2", "W", 1, "PRODUCTION_DEVICE_SESSION", 0),
            ("c1", "C", 1, "PRODUCTION_DEVICE_SESSION", 0),
            ("c2", "C", 0, "PRODUCTION_DEVICE_SESSION", 0),
            ("g1", "G", 1, "PRODUCTION_DEVICE_SESSION", 0),
            ("simulation", "C", 0, "SIMULATED_DEVICE_SESSION", 0),
        ]:
            connection.execute(
                "insert into connector_sessions values "
                "(?, null, ?, 'test', ?, ?, 1, 1, 1, ?, 1, ?, '{}')",
                (session_id, source, data_class, success, deduplicated, session_id),
            )
            if data_class == "PRODUCTION_DEVICE_SESSION":
                connection.execute(
                    "insert into device_event_receipts values "
                    "(?, ?, 'profile', ?, ?, ?, ?, 1, 1, 1, 1, ?, 'now')",
                    (
                        f"event-{session_id}",
                        session_id,
                        source,
                        session_id,
                        data_class,
                        success,
                        session_id,
                    ),
                )

    result = device_linkage_metrics(
        store, data_class=DataClass.PRODUCTION_DEVICE_SESSION
    )

    assert result.source_counts == {"W": 2, "C": 2, "G": 1}
    assert result.source_rates == {"W": 100.0, "C": 50.0, "G": 100.0}
    assert result.aggregate == 250.0 / 3.0


def test_bundled_proxy_evaluation_passes_all_seven_without_real_claims(tmp_path) -> None:
    if not PACKAGE_ROOT.exists():
        pytest.skip("approved_interim_source_package_not_available")
    store = InterimStore(tmp_path / "interim.sqlite3")
    store.migrate()
    import_interim_package(store, PACKAGE_ROOT, max_records_per_split=1)

    report = evaluate_proxy_kpis(store)

    assert report.proxy_kpis_passed == 7
    assert report.proxy_kpis_total == 7
    assert report.proxy_research_completion is True
    assert report.real_research_completion is False
    assert {item.replacement_status for item in report.kpis} == {
        "PENDING_PHARMACIST_GOLD",
        "PENDING_REAL_WORLD_OUTCOME",
        "PENDING_EXTERNAL_TEST",
        "PENDING_12_MONTH_REAL_OPERATION",
        "PENDING_PRODUCTION_DEVICE_SESSIONS",
    }
    assert report.by_id("KPI-1").proxy_value == 100.0
    assert report.by_id("KPI-1").sample_count == 3_544
    assert report.by_id("KPI-1").details == {
        "invalid_reference_count": 1_456,
        "total_input_count": 5_000,
        "valid_reference_count": 3_544,
    }
    assert report.by_id("KPI-5").hard_failures == 0

    with store.transaction() as connection:
        connection.execute(
            """
            insert into pro_observations values (
              'runtime-pro', null, 'INTERIM_RUNTIME_EVENT', 4, 0, -9, -90, 1, 'hash', '{}'
            )
            """
        )
        connection.execute(
            """
            insert into adverse_events values (
              'runtime-ae', null, 'INTERIM_RUNTIME_EVENT', 1, 1, 'OPEN', 1, 'hash', '{}'
            )
            """
        )
        connection.execute(
            """
            insert into connector_sessions values (
              'runtime-device', null, 'W', 'runtime', 'INTERIM_RUNTIME_EVENT',
              0, 0, 0, 0, 0, 0, 'hash', '{}'
            )
            """
        )
    replay = evaluate_proxy_kpis(store)
    assert replay.by_id("KPI-2").proxy_value == report.by_id("KPI-2").proxy_value
    assert replay.by_id("KPI-6").proxy_value == report.by_id("KPI-6").proxy_value
    assert replay.by_id("KPI-7").proxy_value == report.by_id("KPI-7").proxy_value
