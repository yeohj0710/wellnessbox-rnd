from wellnessbox_rnd.interim.store import InterimStore


def test_interim_store_migrates_clean_and_is_idempotent(tmp_path) -> None:
    database_path = tmp_path / "interim.sqlite3"
    store = InterimStore(database_path)

    store.migrate()
    store.migrate()

    assert store.scalar("select max(version) from schema_migrations") == 2
    assert "pharmacy_id" in {row[1] for row in store.rows("pragma table_info(review_tasks)")}
    required_tables = {
        "proxy_cases",
        "dataset_snapshots",
        "model_versions",
        "evaluation_cases",
        "pro_observations",
        "adverse_events",
        "connector_sessions",
        "agent_runs",
        "agent_steps",
        "kpi_results",
        "audit_events",
    }
    assert required_tables.issubset(store.table_names())


def test_interim_store_rejects_unmigrated_access(tmp_path) -> None:
    store = InterimStore(tmp_path / "missing.sqlite3")

    assert store.is_migrated() is False
