import sqlite3

from wellnessbox_rnd.interim.store import InterimStore


def test_interim_store_migrates_clean_and_is_idempotent(tmp_path) -> None:
    database_path = tmp_path / "interim.sqlite3"
    store = InterimStore(database_path)

    store.migrate()
    store.migrate()

    assert store.scalar("select max(version) from schema_migrations") == 6
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
        "profile_snapshots",
        "consent_snapshots",
        "active_profile_consents",
        "executions",
        "execution_events",
        "knowledge_claims",
        "knowledge_rules",
        "claim_rule_links",
        "execution_knowledge_lineage",
        "execution_identities",
        "behavior_events",
    }
    assert required_tables.issubset(store.table_names())


def test_interim_store_rejects_unmigrated_access(tmp_path) -> None:
    store = InterimStore(tmp_path / "missing.sqlite3")

    assert store.is_migrated() is False


def test_schema_version_2_profile_data_survives_lineage_migration(tmp_path) -> None:
    database_path = tmp_path / "version-2.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            create table schema_migrations (
              version integer primary key,
              applied_at text not null
            );
            insert into schema_migrations values (2, '2026-07-15T00:00:00+00:00');
            create table user_profiles (
              profile_id text primary key,
              data_class text not null,
              consent_scopes_json text not null,
              payload_json text not null,
              payload_sha256 text not null,
              created_at text not null
            );
            insert into user_profiles values (
              'usr_1234567890abcdef',
              'INTERIM_RUNTIME_EVENT',
              '[]',
              '{"age":41}',
              'legacy-hash',
              '2026-07-15T00:00:00+00:00'
            );
            """
        )

    store = InterimStore(database_path)
    store.migrate()

    assert store.scalar("select max(version) from schema_migrations") == 6
    assert store.scalar("select count(*) from user_profiles") == 1
    assert store.scalar(
        "select payload_json from user_profiles where profile_id='usr_1234567890abcdef'"
    ) == '{"age":41}'
    assert {
        "profile_snapshots",
        "consent_snapshots",
        "active_profile_consents",
        "executions",
        "execution_events",
    }.issubset(store.table_names())


def test_interim_store_read_helpers_close_database_connections(tmp_path) -> None:
    database_path = tmp_path / "closable.sqlite3"
    store = InterimStore(database_path)
    store.migrate()

    assert store.scalar("select max(version) from schema_migrations") == 6
    assert store.rows("select version from schema_migrations")

    database_path.unlink()
    assert database_path.exists() is False


def test_schema_version_3_events_gain_consent_lineage(tmp_path) -> None:
    database_path = tmp_path / "version-3.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            create table schema_migrations (
              version integer primary key,
              applied_at text not null
            );
            insert into schema_migrations values (3, '2026-07-15T00:00:00+00:00');
            create table consent_snapshots (
              consent_snapshot_id text primary key,
              profile_id text not null,
              version integer not null,
              schema_version text not null,
              payload_json text not null,
              payload_sha256 text not null,
              created_at text not null,
              unique(profile_id, version),
              unique(profile_id, payload_sha256)
            );
            create table executions (
              execution_id text primary key,
              request_id text not null,
              profile_id text not null,
              profile_snapshot_id text,
              consent_snapshot_id text not null references consent_snapshots,
              request_sha256 text not null,
              status text not null,
              created_at text not null,
              updated_at text not null
            );
            create table execution_events (
              event_id text primary key,
              execution_id text not null references executions,
              event_index integer not null,
              event_type text not null,
              source text not null,
              idempotency_key text not null,
              payload_json text not null,
              payload_sha256 text not null,
              created_at text not null,
              unique(execution_id, event_index),
              unique(execution_id, event_type, idempotency_key)
            );
            insert into consent_snapshots values (
              'consent_1', 'usr_1', 1, 'v1', '{}', 'consent-hash',
              '2026-07-15T00:00:00+00:00'
            );
            insert into consent_snapshots values (
              'consent_2', 'usr_1', 2, 'v1', '{"denied":true}', 'denied-hash',
              '2026-07-15T02:00:00+00:00'
            );
            insert into executions values (
              'exec_1', 'request_1', 'usr_1', null, 'consent_1', 'request-hash',
              'COMPLETE', '2026-07-15T00:00:00+00:00', '2026-07-15T03:00:00+00:00'
            );
            insert into executions values (
              'exec_2', 'request_2', 'usr_1', null, 'consent_2', 'request-hash-2',
              'COMPLETE', '2026-07-15T02:00:00+00:00', '2026-07-15T02:00:00+00:00'
            );
            insert into execution_events values (
              'event_1', 'exec_1', 0, 'recommendation', 'system', 'core', '{}',
              'event-hash', '2026-07-15T00:00:00+00:00'
            );
            """
        )

    store = InterimStore(database_path)
    store.migrate()

    assert store.scalar("select max(version) from schema_migrations") == 6
    assert store.scalar(
        "select consent_snapshot_id from execution_events where event_id='event_1'"
    ) == "consent_1"
    assert store.scalar(
        "select consent_snapshot_id from active_profile_consents where profile_id='usr_1'"
    ) == "consent_2"


def test_schema_version_4_evidence_gains_parsed_span_lineage(tmp_path) -> None:
    database_path = tmp_path / "version-4.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            create table schema_migrations (
              version integer primary key,
              applied_at text not null
            );
            insert into schema_migrations values (4, '2026-07-15T00:00:00+00:00');
            create table source_registry (
              source_id text primary key,
              source_tier text not null,
              title text not null,
              canonical_uri text not null,
              license_status text not null,
              effective_at text,
              retired_at text,
              checksum text not null,
              data_class text not null,
              metadata_json text not null
            );
            create table evidence_passages (
              evidence_id text primary key,
              source_id text not null references source_registry,
              passage_text text not null,
              effective_at text,
              checksum text not null,
              approved_for_safety integer not null default 0,
              data_class text not null
            );
            insert into source_registry values (
              'REF-OLD', 'guideline', 'Old source', 'docs/old.md',
              'APPROVED_INTERNAL', '2026-01-01', null, 'source-hash',
              'PROXY_GOLD_SIMULATION', '{}'
            );
            insert into evidence_passages values (
              'ev_old', 'REF-OLD', 'old passage', '2026-01-01',
              'passage-hash', 1, 'PROXY_GOLD_SIMULATION'
            );
            """
        )

    store = InterimStore(database_path)
    store.migrate()

    assert store.scalar("select max(version) from schema_migrations") == 6
    columns = {row[1] for row in store.rows("pragma table_info(evidence_passages)")}
    assert {"page_or_section", "line_start", "line_end", "metadata_json"}.issubset(
        columns
    )
    assert store.scalar(
        "select passage_text from evidence_passages where evidence_id='ev_old'"
    ) == "old passage"
    assert store.scalar(
        "select metadata_json from evidence_passages where evidence_id='ev_old'"
    ) == "{}"
    assert {
        "knowledge_claims",
        "knowledge_rules",
        "claim_rule_links",
        "execution_knowledge_lineage",
    }.issubset(store.table_names())


def test_schema_version_5_gains_disjoint_log_and_identity_tables(tmp_path) -> None:
    database_path = tmp_path / "version-5.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            create table schema_migrations (
              version integer primary key,
              applied_at text not null
            );
            insert into schema_migrations values (5, '2026-07-15T00:00:00+00:00');
            create table consent_snapshots (
              consent_snapshot_id text primary key,
              profile_id text not null,
              version integer not null,
              schema_version text not null,
              payload_json text not null,
              payload_sha256 text not null,
              created_at text not null,
              unique(profile_id, version),
              unique(profile_id, payload_sha256)
            );
            create table executions (
              execution_id text primary key,
              request_id text not null,
              profile_id text not null,
              profile_snapshot_id text,
              consent_snapshot_id text not null references consent_snapshots,
              request_sha256 text not null,
              status text not null,
              created_at text not null,
              updated_at text not null
            );
            insert into consent_snapshots values (
              'consent_v5', 'usr_v5', 1, 'v1', '{}', 'consent-hash-v5',
              '2026-07-15T00:00:00+00:00'
            );
            insert into executions values (
              'exec_v5', 'request_v5', 'usr_v5', null, 'consent_v5', 'request-hash-v5',
              'COMPLETE', '2026-07-15T00:00:00+00:00', '2026-07-15T00:00:00+00:00'
            );
            """
        )

    store = InterimStore(database_path)
    store.migrate()

    assert store.scalar("select max(version) from schema_migrations") == 6
    assert store.scalar("select count(*) from executions") == 1
    assert {"execution_identities", "behavior_events"}.issubset(store.table_names())
    behavior_sql = store.scalar(
        "select sql from sqlite_master where type='table' and name='behavior_events'"
    )
    assert "'user_behavior'" in behavior_sql
    for research_type in (
        "'conversation'",
        "'recommendation'",
        "'safety'",
        "'optimization'",
        "'followup_evaluation'",
    ):
        assert research_type not in behavior_sql
    events_sql = store.scalar(
        "select sql from sqlite_master where type='table' and name='execution_events'"
    )
    for behavior_name in ("'page_view'", "'product_exposure'", "'session_start'"):
        assert behavior_name not in events_sql
