import sqlite3
from shutil import copyfile

import pytest

from wellnessbox_rnd.interim.store import SCHEMA_SQL, SCHEMA_VERSION, InterimStore


def test_v9_unlinked_workflow_rows_are_quarantined_on_migration(tmp_path) -> None:
    database_path = tmp_path / "legacy-jobs.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            create table user_profiles (
              profile_id text primary key, data_class text not null,
              consent_scopes_json text not null, payload_json text not null,
              payload_sha256 text not null, created_at text not null
            );
            create table followups (
              followup_id text primary key, profile_id text not null,
              plan_id text, due_at text not null, requested_data_json text not null,
              status text not null, created_at text not null
            );
            create table workflow_jobs (
              job_id text primary key, job_type text not null, status text not null,
              idempotency_key text not null unique, profile_id text not null,
              plan_id text not null, followup_id text not null, scheduled_at text not null,
              payload_json text not null, payload_sha256 text not null,
              created_at text not null, claimed_at text, completed_at text
            );
            insert into user_profiles values (
              'legacy', 'PROXY_GOLD_SIMULATION', '[]', '{}', 'h', 'now'
            );
            insert into followups values (
              'fu_legacy', 'legacy', 'plan_legacy', 'now', '[]', 'OPEN', 'now'
            );
            insert into workflow_jobs values (
              'job_legacy', 'FOLLOWUP_REMINDER', 'READY', 'legacy', 'legacy',
              'plan_legacy', 'fu_legacy', 'now', '{}', 'h', 'now', null, null
            );
            """
        )

    store = InterimStore(database_path)
    store.migrate()

    assert store.scalar("select status from followups where followup_id='fu_legacy'") == "CLOSED"
    assert store.scalar("select status from workflow_jobs where job_id='job_legacy'") == "CANCELLED"
    assert store.scalar("select last_error from workflow_jobs where job_id='job_legacy'") == (
        "LEGACY_UNLINKED_EXECUTION"
    )


def test_interim_store_migrates_clean_and_is_idempotent(tmp_path) -> None:
    database_path = tmp_path / "interim.sqlite3"
    store = InterimStore(database_path)

    store.migrate()
    store.migrate()

    assert store.scalar("select max(version) from schema_migrations") == SCHEMA_VERSION
    assert "pharmacy_id" in {row[1] for row in store.rows("pragma table_info(review_tasks)")}
    required_tables = {
        "proxy_cases",
        "dataset_snapshots",
        "model_versions",
        "evaluation_cases",
        "pro_observations",
        "adverse_events",
        "connector_sessions",
        "device_recommendation_assessments",
        "agent_runs",
        "agent_steps",
        "kpi_results",
        "audit_events",
        "event_mutation_cleanup",
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
        "execution_replay_snapshots",
        "execution_replay_runs",
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

    assert store.scalar("select max(version) from schema_migrations") == SCHEMA_VERSION
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

    assert store.scalar("select max(version) from schema_migrations") == SCHEMA_VERSION
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

    assert store.scalar("select max(version) from schema_migrations") == SCHEMA_VERSION
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

    assert store.scalar("select max(version) from schema_migrations") == SCHEMA_VERSION
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

    assert store.scalar("select max(version) from schema_migrations") == SCHEMA_VERSION
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


def test_schema_version_6_lineage_keeps_multiple_rules_for_one_claim(tmp_path) -> None:
    database_path = tmp_path / "version-6.sqlite3"
    corrected_unique = (
        "UNIQUE(execution_id, event_id, output_type, output_key, claim_id, rule_id)"
    )
    legacy_unique = (
        "UNIQUE(execution_id, event_id, output_type, output_key, claim_id)"
    )
    legacy_schema = SCHEMA_SQL.replace(corrected_unique, legacy_unique)
    with sqlite3.connect(database_path) as connection:
        connection.executescript(legacy_schema)
        connection.execute(
            "insert into schema_migrations values (6, '2026-07-15T00:00:00+00:00')"
        )
        connection.execute(
            "insert into source_registry values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "source_1",
                "guideline",
                "Source",
                "docs/source.md",
                "APPROVED_INTERNAL",
                "2026-01-01T00:00:00Z",
                None,
                "source-hash",
                "PROXY_GOLD_SIMULATION",
                "{}",
            ),
        )
        connection.execute(
            """
            insert into evidence_passages values (
              'evidence_1', 'source_1', 'Passage', 'section', 1, 2, '{}',
              '2026-01-01T00:00:00Z', 'evidence-hash', 1,
              'PROXY_GOLD_SIMULATION'
            )
            """
        )
        connection.execute(
            """
            insert into knowledge_claims values (
              'claim_1', 'evidence_1', 'safety', 'Claim', '[]', '[]', '[]',
              'claim-hash', '2026-01-01T00:00:00Z', null,
              'PROXY_GOLD_SIMULATION'
            )
            """
        )
        for rule_id in ("rule_1", "rule_2"):
            connection.execute(
                """
                insert into knowledge_rules values (
                  ?, 'safety', 'HIGH', 'knowledge', '{}', '{}', ?,
                  '2026-01-01T00:00:00Z', null, 'ACTIVE',
                  'PROXY_GOLD_SIMULATION'
                )
                """,
                (rule_id, f"{rule_id}-hash"),
            )
            connection.execute(
                "insert into claim_rule_links values ('claim_1', ?)", (rule_id,)
            )
        connection.execute(
            """
            insert into consent_snapshots values (
              'consent_1', 'profile_1', 1, 'v1', '{}', 'consent-hash',
              '2026-07-15T00:00:00+00:00'
            )
            """
        )
        connection.execute(
            """
            insert into executions values (
              'execution_1', 'request_1', 'profile_1', null, 'consent_1',
              'request-hash', 'COMPLETE', '2026-07-15T00:00:00+00:00',
              '2026-07-15T00:00:00+00:00'
            )
            """
        )
        connection.execute(
            """
            insert into execution_events(
              event_id, execution_id, consent_snapshot_id, event_index, event_type,
              source, idempotency_key, payload_json, payload_sha256,
              effective_payload_sha256, created_at
            ) values (
              'event_1', 'execution_1', 'consent_1', 0, 'recommendation',
              'system', 'core', '{}', 'event-hash', 'event-hash',
              '2026-07-15T00:00:00+00:00'
            )
            """
        )
        connection.execute(
            """
            insert into execution_knowledge_lineage values (
              'lineage_1', 'execution_1', 'event_1', 'recommendation_decision',
              'decision_1', 'rule_1', 'claim_1', 'evidence_1', 'source_1',
              'INTERIM_RUNTIME_EVENT', '2026-07-15T00:00:00+00:00'
            )
            """
        )

    corrupt_database_path = tmp_path / "version-6-corrupt.sqlite3"
    copyfile(database_path, corrupt_database_path)
    with sqlite3.connect(corrupt_database_path) as connection:
        connection.execute(
            "update execution_knowledge_lineage set rule_id='missing_rule'"
        )

    corrupt_store = InterimStore(corrupt_database_path)
    with pytest.raises(sqlite3.IntegrityError):
        corrupt_store.migrate()
    assert corrupt_store.scalar("select max(version) from schema_migrations") == 6
    corrupt_table_sql = corrupt_store.scalar(
        "select sql from sqlite_master "
        "where type='table' and name='execution_knowledge_lineage'"
    )
    assert legacy_unique in corrupt_table_sql
    assert corrected_unique not in corrupt_table_sql

    store = InterimStore(database_path)
    store.migrate()

    assert store.scalar("select max(version) from schema_migrations") == SCHEMA_VERSION
    assert store.scalar("select count(*) from execution_knowledge_lineage") == 1
    with store.transaction() as connection:
        connection.execute(
            """
            insert into execution_knowledge_lineage values (
              'lineage_2', 'execution_1', 'event_1', 'recommendation_decision',
              'decision_1', 'rule_2', 'claim_1', 'evidence_1', 'source_1',
              'INTERIM_RUNTIME_EVENT', '2026-07-15T00:00:00+00:00'
            )
            """
        )
    store.migrate()

    assert store.scalar("select count(*) from execution_knowledge_lineage") == 2
    assert store.scalar("pragma foreign_keys") == 1


def test_schema_version_7_gains_event_mutation_history(tmp_path) -> None:
    database_path = tmp_path / "version-7.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(SCHEMA_SQL)
        connection.execute(
            """
            insert into consent_snapshots values (
              'consent_v7', 'profile_v7', 1, 'v1', '{}', 'consent-v7-hash',
              '2026-07-16T00:00:00+00:00'
            )
            """
        )
        connection.execute(
            """
            insert into executions values (
              'execution_v7', 'request_v7', 'profile_v7', null, 'consent_v7',
              'request-v7-hash', 'COMPLETE', '2026-07-16T00:00:00+00:00',
              '2026-07-16T00:00:00+00:00'
            )
            """
        )
        connection.execute(
            """
            insert into execution_events values (
              'event_v7', 'execution_v7', 'consent_v7', 0, 'conversation',
              'survey', 'event-v7-key', '{"legacy":true}', 'event-v7-hash',
              'event-v7-hash', 'ACTIVE', '2026-07-16T00:00:00+00:00'
            )
            """
        )
        connection.execute(
            """
            insert into behavior_events values (
              'behavior_v7', 'profile_v7', 'consent_v7', 'user_behavior',
              'page_view', '2026-07-16T00:00:00+00:00', 'behavior-v7-key',
              '{"path":"/legacy"}', 'behavior-v7-hash', 'behavior-v7-hash',
              'ACTIVE', 'INTERIM_RUNTIME_EVENT',
              '2026-07-16T00:00:00+00:00'
            )
            """
        )
        connection.execute("alter table execution_events drop column payload_state")
        connection.execute(
            "alter table execution_events drop column effective_payload_sha256"
        )
        connection.execute("alter table behavior_events drop column payload_state")
        connection.execute(
            "alter table behavior_events drop column effective_payload_sha256"
        )
        connection.execute(
            "insert into schema_migrations values (7, '2026-07-16T00:00:00+00:00')"
        )

    store = InterimStore(database_path)
    store.migrate()
    store.migrate()

    assert store.scalar("select max(version) from schema_migrations") == SCHEMA_VERSION
    assert "event_mutations" in store.table_names()
    for table_name in ("execution_events", "behavior_events"):
        table_info = store.rows(f"pragma table_info({table_name})")
        columns = {row[1] for row in table_info}
        assert {"payload_state", "effective_payload_sha256"}.issubset(columns)
        effective_column = next(
            row for row in table_info if row[1] == "effective_payload_sha256"
        )
        assert effective_column[3] == 1
    execution_row = store.rows(
        "select * from execution_events where event_id='event_v7'"
    )[0]
    behavior_row = store.rows(
        "select * from behavior_events where behavior_event_id='behavior_v7'"
    )[0]
    assert execution_row["payload_state"] == "ACTIVE"
    assert execution_row["effective_payload_sha256"] == "event-v7-hash"
    assert behavior_row["payload_state"] == "ACTIVE"
    assert behavior_row["effective_payload_sha256"] == "behavior-v7-hash"


def test_schema_version_7_event_mutation_migration_rolls_back_atomically(
    tmp_path,
) -> None:
    database_path = tmp_path / "version-7-failed.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(SCHEMA_SQL)
        connection.execute("alter table execution_events drop column payload_state")
        connection.execute(
            "alter table execution_events drop column effective_payload_sha256"
        )
        connection.execute("alter table behavior_events drop column payload_state")
        connection.execute(
            "alter table behavior_events drop column effective_payload_sha256"
        )
        connection.execute("create view event_mutations as select 1 as mutation_id")
        connection.execute(
            "insert into schema_migrations values (7, '2026-07-16T00:00:00+00:00')"
        )

    store = InterimStore(database_path)
    with pytest.raises(
        sqlite3.IntegrityError, match="legacy_event_mutations_require_chain_rebuild"
    ):
        store.migrate()

    assert store.scalar("select max(version) from schema_migrations") == 7
    for table_name in ("execution_events", "behavior_events"):
        columns = {row[1] for row in store.rows(f"pragma table_info({table_name})")}
        assert "payload_state" not in columns
        assert "effective_payload_sha256" not in columns


def test_schema_version_8_migration_restores_cleanup_guards(tmp_path) -> None:
    database_path = tmp_path / "version-8-guards.sqlite3"
    store = InterimStore(database_path)
    store.migrate()
    with store.transaction() as connection:
        connection.execute("drop trigger event_mutations_no_update")
        connection.execute("drop index idx_event_mutations_target_created")
        connection.execute("drop table event_mutation_cleanup")

    store.migrate()

    sqlite_objects = {
        row["name"]
        for row in store.rows(
            "select name from sqlite_master where type in ('table','index','trigger')"
        )
    }
    assert {
        "event_mutation_cleanup",
        "event_mutations_no_update",
        "idx_event_mutations_target_created",
    }.issubset(sqlite_objects)


def test_secure_cleanup_completes_only_mutations_present_before_compaction(
    tmp_path, monkeypatch
) -> None:
    database_path = tmp_path / "cleanup-snapshot.sqlite3"
    store = InterimStore(database_path)
    store.migrate()

    def insert_pending(mutation_id: str, target_event_id: str) -> None:
        with store.transaction(immediate=True) as connection:
            connection.execute(
                """
                insert into event_mutations(
                  mutation_id, profile_id, target_type, target_event_id,
                  operation, idempotency_key, request_sha256,
                  prior_payload_sha256, result_payload_sha256,
                  previous_mutation_id, previous_mutation_sha256,
                  mutation_index, mutation_sha256, created_at
                ) values (?, 'profile', 'execution_event', ?, 'deletion', ?,
                  'request-hash', 'prior-hash', 'result-hash', null, null, 0,
                  'mutation-hash', '2026-07-16T00:00:00+00:00')
                """,
                (mutation_id, target_event_id, f"key-{mutation_id}"),
            )
            connection.execute(
                """
                insert into event_mutation_cleanup values (
                  ?, 'PENDING', '2026-07-16T00:00:00+00:00', null
                )
                """,
                (mutation_id,),
            )

    insert_pending("mutation_before", "event_before")

    def compact_with_concurrent_pending_insert() -> None:
        insert_pending("mutation_during", "event_during")

    monkeypatch.setattr(store, "secure_compact", compact_with_concurrent_pending_insert)

    store.complete_pending_secure_compactions()

    cleanup_statuses = {
        row["mutation_id"]: row["status"]
        for row in store.rows("select * from event_mutation_cleanup")
    }
    assert cleanup_statuses == {
        "mutation_before": "COMPLETE",
        "mutation_during": "PENDING",
    }
