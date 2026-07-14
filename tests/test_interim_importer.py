from wellnessbox_rnd.interim.importer import import_interim_package
from wellnessbox_rnd.interim.manifest import APPROVED_SOURCE_ROOT
from wellnessbox_rnd.interim.store import InterimStore

PACKAGE_ROOT = APPROVED_SOURCE_ROOT


def test_importer_streams_rows_and_is_idempotent(tmp_path) -> None:
    store = InterimStore(tmp_path / "interim.sqlite3")
    store.migrate()

    first = import_interim_package(store, PACKAGE_ROOT, max_records_per_split=2)
    second = import_interim_package(store, PACKAGE_ROOT, max_records_per_split=2)

    assert first.proxy_cases == 8
    assert first.pro_observations == 240
    assert first.adverse_events == 3
    assert first.connector_sessions == 180
    assert first.evaluation_cases == 10_000
    assert second == first
    assert store.scalar("select count(*) from proxy_cases") == 8
    assert store.scalar("select count(*) from pro_observations") == 240
    assert store.scalar("select count(*) from adverse_events") == 3
    assert store.scalar("select count(*) from connector_sessions") == 180
    assert store.scalar("select count(*) from evaluation_cases") == 10_000
    assert store.scalar("select count(*) from model_versions") == 1
