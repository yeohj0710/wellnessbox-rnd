from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 12

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
  version INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS import_jobs (
  import_key TEXT PRIMARY KEY,
  package_root TEXT NOT NULL,
  manifest_sha256 TEXT NOT NULL,
  status TEXT NOT NULL,
  counts_json TEXT NOT NULL,
  completed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_registry (
  source_id TEXT PRIMARY KEY,
  source_tier TEXT NOT NULL,
  title TEXT NOT NULL,
  canonical_uri TEXT NOT NULL,
  license_status TEXT NOT NULL,
  effective_at TEXT,
  retired_at TEXT,
  checksum TEXT NOT NULL,
  data_class TEXT NOT NULL,
  metadata_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_passages (
  evidence_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES source_registry(source_id),
  passage_text TEXT NOT NULL,
  page_or_section TEXT,
  line_start INTEGER,
  line_end INTEGER,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  effective_at TEXT,
  checksum TEXT NOT NULL,
  approved_for_safety INTEGER NOT NULL DEFAULT 0,
  data_class TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_claims (
  claim_id TEXT PRIMARY KEY,
  evidence_id TEXT NOT NULL REFERENCES evidence_passages(evidence_id),
  normalized_claim_type TEXT NOT NULL,
  claim_text TEXT NOT NULL,
  ingredient_keys_json TEXT NOT NULL,
  medication_keys_json TEXT NOT NULL,
  domain_keys_json TEXT NOT NULL,
  checksum TEXT NOT NULL,
  effective_at TEXT,
  retired_at TEXT,
  data_class TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_rules (
  rule_id TEXT PRIMARY KEY,
  rule_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  predicate_json TEXT NOT NULL,
  action_json TEXT NOT NULL,
  checksum TEXT NOT NULL,
  valid_from TEXT,
  valid_to TEXT,
  status TEXT NOT NULL,
  data_class TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claim_rule_links (
  claim_id TEXT NOT NULL REFERENCES knowledge_claims(claim_id),
  rule_id TEXT NOT NULL REFERENCES knowledge_rules(rule_id),
  PRIMARY KEY(claim_id, rule_id)
);

CREATE TABLE IF NOT EXISTS safety_rules (
  rule_version_id TEXT PRIMARY KEY,
  rule_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  severity TEXT NOT NULL,
  action TEXT NOT NULL,
  predicate_json TEXT NOT NULL,
  evidence_ids_json TEXT NOT NULL,
  valid_from TEXT NOT NULL,
  valid_to TEXT,
  review_status TEXT NOT NULL,
  rule_sha256 TEXT NOT NULL,
  data_class TEXT NOT NULL,
  UNIQUE(rule_id, version)
);

CREATE TABLE IF NOT EXISTS dataset_snapshots (
  dataset_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  version TEXT NOT NULL,
  data_class TEXT NOT NULL,
  manifest_uri TEXT NOT NULL,
  manifest_sha256 TEXT NOT NULL,
  record_count INTEGER NOT NULL,
  split_counts_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS proxy_cases (
  case_id TEXT PRIMARY KEY,
  dataset_id TEXT NOT NULL REFERENCES dataset_snapshots(dataset_id),
  split TEXT NOT NULL,
  data_class TEXT NOT NULL,
  teacher_session TEXT NOT NULL,
  archetype_id TEXT NOT NULL,
  source_file TEXT NOT NULL,
  source_line INTEGER NOT NULL,
  row_sha256 TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS model_versions (
  model_id TEXT PRIMARY KEY,
  model_name TEXT NOT NULL,
  version TEXT NOT NULL,
  data_class TEXT NOT NULL,
  artifact_uri TEXT NOT NULL,
  artifact_sha256 TEXT NOT NULL,
  dataset_id TEXT NOT NULL REFERENCES dataset_snapshots(dataset_id),
  metrics_json TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evaluation_cases (
  evaluation_kind TEXT NOT NULL,
  case_id TEXT NOT NULL,
  data_class TEXT NOT NULL,
  source_file TEXT NOT NULL,
  source_line INTEGER NOT NULL,
  row_sha256 TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  PRIMARY KEY(evaluation_kind, case_id)
);

CREATE TABLE IF NOT EXISTS user_profiles (
  profile_id TEXT PRIMARY KEY,
  data_class TEXT NOT NULL,
  consent_scopes_json TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS profile_snapshots (
  profile_snapshot_id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  schema_version TEXT NOT NULL,
  data_class TEXT NOT NULL,
  persisted_sources_json TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(profile_id, version),
  UNIQUE(profile_id, payload_sha256)
);

CREATE TABLE IF NOT EXISTS consent_snapshots (
  consent_snapshot_id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  schema_version TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(profile_id, version),
  UNIQUE(profile_id, payload_sha256)
);

CREATE TABLE IF NOT EXISTS active_profile_consents (
  profile_id TEXT PRIMARY KEY,
  consent_snapshot_id TEXT NOT NULL REFERENCES consent_snapshots(consent_snapshot_id),
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS executions (
  execution_id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL,
  profile_id TEXT NOT NULL,
  profile_snapshot_id TEXT REFERENCES profile_snapshots(profile_snapshot_id),
  consent_snapshot_id TEXT NOT NULL REFERENCES consent_snapshots(consent_snapshot_id),
  request_sha256 TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS execution_events (
  event_id TEXT PRIMARY KEY,
  execution_id TEXT NOT NULL REFERENCES executions(execution_id),
  consent_snapshot_id TEXT NOT NULL REFERENCES consent_snapshots(consent_snapshot_id),
  event_index INTEGER NOT NULL,
  event_type TEXT NOT NULL CHECK(event_type IN (
    'conversation',
    'recommendation',
    'safety',
    'optimization',
    'followup_evaluation'
  )),
  source TEXT NOT NULL CHECK(source IN (
    'system',
    'survey',
    'nhis',
    'wearable',
    'cgm',
    'genetic'
  )),
  idempotency_key TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  effective_payload_sha256 TEXT NOT NULL,
  payload_state TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(payload_state IN (
    'ACTIVE', 'CORRECTED', 'DELETED'
  )),
  created_at TEXT NOT NULL,
  UNIQUE(execution_id, event_index),
  UNIQUE(execution_id, event_type, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_profile_snapshots_profile_version
ON profile_snapshots(profile_id, version);

CREATE INDEX IF NOT EXISTS idx_consent_snapshots_profile_version
ON consent_snapshots(profile_id, version);

CREATE INDEX IF NOT EXISTS idx_executions_profile_created
ON executions(profile_id, created_at);

CREATE INDEX IF NOT EXISTS idx_execution_events_execution_index
ON execution_events(execution_id, event_index);

CREATE TABLE IF NOT EXISTS execution_knowledge_lineage (
  lineage_id TEXT PRIMARY KEY,
  execution_id TEXT NOT NULL REFERENCES executions(execution_id),
  event_id TEXT NOT NULL REFERENCES execution_events(event_id),
  output_type TEXT NOT NULL CHECK(output_type IN (
    'recommendation_item',
    'safety_rule',
    'recommendation_decision'
  )),
  output_key TEXT NOT NULL,
  rule_id TEXT NOT NULL REFERENCES knowledge_rules(rule_id),
  claim_id TEXT NOT NULL REFERENCES knowledge_claims(claim_id),
  evidence_id TEXT NOT NULL REFERENCES evidence_passages(evidence_id),
  source_id TEXT NOT NULL REFERENCES source_registry(source_id),
  data_class TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(execution_id, event_id, output_type, output_key, claim_id, rule_id)
);

CREATE TABLE IF NOT EXISTS execution_identities (
  execution_id TEXT PRIMARY KEY REFERENCES executions(execution_id),
  model_id TEXT NOT NULL,
  engine_version TEXT NOT NULL,
  code_commit TEXT NOT NULL,
  code_commit_source TEXT NOT NULL CHECK(code_commit_source IN (
    'environment',
    'git',
    'unresolved'
  )),
  dataset_ids_json TEXT NOT NULL,
  config_json TEXT NOT NULL,
  config_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS execution_replay_snapshots (
  execution_id TEXT PRIMARY KEY REFERENCES executions(execution_id),
  request_json TEXT NOT NULL,
  request_sha256 TEXT NOT NULL,
  expected_output_json TEXT NOT NULL,
  expected_output_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS execution_replay_runs (
  replay_id TEXT PRIMARY KEY,
  execution_id TEXT NOT NULL REFERENCES executions(execution_id),
  status TEXT NOT NULL CHECK(status IN ('MATCH', 'MISMATCH', 'VERSION_MISMATCH')),
  input_match INTEGER NOT NULL CHECK(input_match IN (0, 1)),
  version_match INTEGER NOT NULL CHECK(version_match IN (0, 1)),
  output_match INTEGER CHECK(output_match IN (0, 1)),
  expected_output_sha256 TEXT NOT NULL,
  actual_output_sha256 TEXT,
  mismatch_fields_json TEXT NOT NULL,
  stored_identity_sha256 TEXT NOT NULL,
  active_identity_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_execution_replay_runs_execution_created
ON execution_replay_runs(execution_id, created_at);

CREATE TRIGGER IF NOT EXISTS execution_replay_snapshots_no_update
BEFORE UPDATE ON execution_replay_snapshots
BEGIN
  SELECT RAISE(ABORT, 'execution_replay_snapshots_append_only');
END;

CREATE TRIGGER IF NOT EXISTS execution_replay_snapshots_no_delete
BEFORE DELETE ON execution_replay_snapshots
BEGIN
  SELECT RAISE(ABORT, 'execution_replay_snapshots_append_only');
END;

CREATE TRIGGER IF NOT EXISTS execution_replay_runs_no_update
BEFORE UPDATE ON execution_replay_runs
BEGIN
  SELECT RAISE(ABORT, 'execution_replay_runs_append_only');
END;

CREATE TRIGGER IF NOT EXISTS execution_replay_runs_no_delete
BEFORE DELETE ON execution_replay_runs
BEGIN
  SELECT RAISE(ABORT, 'execution_replay_runs_append_only');
END;

CREATE TABLE IF NOT EXISTS behavior_events (
  behavior_event_id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL,
  consent_snapshot_id TEXT NOT NULL REFERENCES consent_snapshots(consent_snapshot_id),
  log_class TEXT NOT NULL DEFAULT 'user_behavior' CHECK(log_class = 'user_behavior'),
  event_name TEXT NOT NULL CHECK(event_name IN (
    'page_view',
    'product_exposure',
    'product_click',
    'cart_add',
    'order_view',
    'notification_open',
    'session_start',
    'session_end'
  )),
  occurred_at TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  effective_payload_sha256 TEXT NOT NULL,
  payload_state TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(payload_state IN (
    'ACTIVE', 'CORRECTED', 'DELETED'
  )),
  data_class TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(profile_id, event_name, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_behavior_events_profile_created
ON behavior_events(profile_id, created_at);

CREATE INDEX IF NOT EXISTS idx_knowledge_claims_evidence
ON knowledge_claims(evidence_id);

CREATE INDEX IF NOT EXISTS idx_claim_rule_links_rule
ON claim_rule_links(rule_id);

CREATE INDEX IF NOT EXISTS idx_execution_knowledge_lineage_execution
ON execution_knowledge_lineage(execution_id, created_at);

CREATE TABLE IF NOT EXISTS recommendation_runs (
  run_id TEXT PRIMARY KEY,
  profile_id TEXT REFERENCES user_profiles(profile_id),
  model_id TEXT REFERENCES model_versions(model_id),
  status TEXT NOT NULL,
  request_sha256 TEXT NOT NULL,
  response_json TEXT,
  created_at TEXT NOT NULL,
  completed_at TEXT,
  idempotency_identity TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS recommendation_items (
  run_id TEXT NOT NULL REFERENCES recommendation_runs(run_id),
  ingredient_id TEXT NOT NULL,
  rank INTEGER NOT NULL,
  score REAL NOT NULL,
  decision TEXT NOT NULL,
  evidence_ids_json TEXT NOT NULL,
  PRIMARY KEY(run_id, ingredient_id)
);

CREATE TABLE IF NOT EXISTS agent_runs (
  run_id TEXT PRIMARY KEY,
  profile_id TEXT REFERENCES user_profiles(profile_id),
  idempotency_key TEXT NOT NULL UNIQUE,
  state_before TEXT NOT NULL,
  state_after TEXT,
  risk_tier INTEGER NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  completed_at TEXT
);

CREATE TABLE IF NOT EXISTS agent_steps (
  run_id TEXT NOT NULL REFERENCES agent_runs(run_id),
  step_index INTEGER NOT NULL,
  tool_name TEXT NOT NULL,
  arguments_sha256 TEXT NOT NULL,
  result_sha256 TEXT NOT NULL,
  postcondition_success INTEGER NOT NULL,
  reason_codes_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  binding_json TEXT,
  binding_sha256 TEXT,
  PRIMARY KEY(run_id, step_index)
);

CREATE TABLE IF NOT EXISTS followups (
  followup_id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL REFERENCES user_profiles(profile_id),
  plan_id TEXT,
  execution_id TEXT REFERENCES executions(execution_id),
  due_at TEXT NOT NULL,
  requested_data_json TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow_jobs (
  job_id TEXT PRIMARY KEY,
  job_type TEXT NOT NULL CHECK(job_type IN ('FOLLOWUP_REMINDER', 'PLAN_REEVALUATION')),
  status TEXT NOT NULL CHECK(status IN ('READY', 'CLAIMED', 'COMPLETED', 'CANCELLED')),
  idempotency_key TEXT NOT NULL UNIQUE,
  profile_id TEXT NOT NULL REFERENCES user_profiles(profile_id),
  plan_id TEXT NOT NULL,
  followup_id TEXT NOT NULL REFERENCES followups(followup_id),
  execution_id TEXT NOT NULL REFERENCES executions(execution_id),
  scheduled_at TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL,
  claimed_at TEXT,
  completed_at TEXT,
  lease_until TEXT,
  claim_token TEXT,
  attempt_count INTEGER NOT NULL DEFAULT 0,
  last_error TEXT
);

CREATE INDEX IF NOT EXISTS idx_workflow_jobs_ready_schedule
ON workflow_jobs(status, scheduled_at, job_type);

CREATE INDEX IF NOT EXISTS idx_workflow_jobs_followup
ON workflow_jobs(followup_id, job_type);

CREATE TABLE IF NOT EXISTS pro_observations (
  observation_id TEXT PRIMARY KEY,
  profile_id TEXT,
  data_class TEXT NOT NULL,
  timepoint_weeks INTEGER NOT NULL,
  z_pre REAL NOT NULL,
  z_post REAL NOT NULL,
  percentile_point_change REAL NOT NULL,
  adherence REAL,
  row_sha256 TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS adverse_events (
  case_id TEXT PRIMARY KEY,
  profile_id TEXT,
  data_class TEXT NOT NULL,
  related_to_recommendation INTEGER NOT NULL,
  serious INTEGER NOT NULL,
  status TEXT NOT NULL,
  observation_month INTEGER,
  row_sha256 TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS connector_sessions (
  session_id TEXT PRIMARY KEY,
  profile_id TEXT,
  source TEXT NOT NULL CHECK(source IN ('W','C','G')),
  environment TEXT NOT NULL,
  data_class TEXT NOT NULL,
  success INTEGER NOT NULL,
  schema_valid INTEGER NOT NULL,
  unit_valid INTEGER NOT NULL,
  timezone_valid INTEGER NOT NULL,
  deduplicated INTEGER NOT NULL,
  provenance_saved INTEGER NOT NULL,
  row_sha256 TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sensor_file_ingestions (
  ingestion_id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL,
  file_id TEXT NOT NULL,
  source TEXT NOT NULL CHECK(source IN ('wearable', 'cgm', 'genetic')),
  normalization_version TEXT NOT NULL,
  raw_file_sha256 TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('SUCCESS', 'FAILED')),
  schema_validation_json TEXT NOT NULL,
  failure_types_json TEXT NOT NULL,
  normalized_record_count INTEGER NOT NULL CHECK(normalized_record_count >= 0),
  normalized_payload_json TEXT,
  normalized_payload_sha256 TEXT,
  created_at TEXT NOT NULL,
  UNIQUE(profile_id, file_id, raw_file_sha256, normalization_version),
  CHECK(
    (status='SUCCESS' AND normalized_payload_json IS NOT NULL
      AND normalized_payload_sha256 IS NOT NULL AND normalized_record_count > 0)
    OR
    (status='FAILED' AND normalized_payload_json IS NULL
      AND normalized_payload_sha256 IS NULL AND normalized_record_count = 0)
  )
);

CREATE INDEX IF NOT EXISTS idx_sensor_file_ingestions_profile_created
ON sensor_file_ingestions(profile_id, created_at, ingestion_id);

CREATE TRIGGER IF NOT EXISTS sensor_file_ingestions_no_update
BEFORE UPDATE ON sensor_file_ingestions
BEGIN
  SELECT RAISE(ABORT, 'sensor_file_ingestions_append_only');
END;

CREATE TRIGGER IF NOT EXISTS sensor_file_ingestions_no_delete
BEFORE DELETE ON sensor_file_ingestions
BEGIN
  SELECT RAISE(ABORT, 'sensor_file_ingestions_append_only');
END;

CREATE TABLE IF NOT EXISTS review_tasks (
  review_id TEXT PRIMARY KEY,
  run_id TEXT REFERENCES agent_runs(run_id),
  profile_id TEXT,
  data_class TEXT NOT NULL,
  simulation_badge INTEGER NOT NULL,
  urgency TEXT NOT NULL,
  reason_codes_json TEXT NOT NULL,
  status TEXT NOT NULL,
  decision_json TEXT,
  created_at TEXT NOT NULL,
  completed_at TEXT,
  pharmacy_id INTEGER,
  source_job_id TEXT REFERENCES workflow_jobs(job_id),
  completion_postcondition_json TEXT,
  completion_postcondition_sha256 TEXT
);

CREATE TRIGGER IF NOT EXISTS trg_completed_review_immutable_update
BEFORE UPDATE ON review_tasks
WHEN OLD.status = 'COMPLETED'
BEGIN
  SELECT RAISE(ABORT, 'completed_review_immutable');
END;

CREATE TRIGGER IF NOT EXISTS trg_completed_review_immutable_delete
BEFORE DELETE ON review_tasks
WHEN OLD.status = 'COMPLETED'
BEGIN
  SELECT RAISE(ABORT, 'completed_review_immutable');
END;

CREATE TABLE IF NOT EXISTS kpi_results (
  kpi_id TEXT PRIMARY KEY,
  proxy_value REAL NOT NULL,
  sample_count INTEGER NOT NULL,
  ci95_lower REAL,
  ci95_upper REAL,
  proxy_pass INTEGER NOT NULL,
  replacement_status TEXT NOT NULL,
  hard_failures INTEGER NOT NULL,
  details_json TEXT NOT NULL,
  evaluated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
  event_id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  subject_id TEXT NOT NULL,
  data_class TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  metadata_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS research_notes (
  note_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  command TEXT NOT NULL,
  inputs_json TEXT NOT NULL,
  outputs_json TEXT NOT NULL,
  note_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE VIEW IF NOT EXISTS v_proxy_dataset_counts AS
SELECT split, COUNT(*) AS record_count
FROM proxy_cases
GROUP BY split;

CREATE VIEW IF NOT EXISTS v_connector_kpi AS
SELECT source, COUNT(*) AS attempted, SUM(success) AS succeeded,
       100.0 * SUM(success) / COUNT(*) AS success_rate
FROM connector_sessions
GROUP BY source;
"""


class InterimStore:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)

    def connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA secure_delete = ON")
        return connection

    @contextmanager
    def transaction(self, *, immediate: bool = False) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def migrate(self) -> None:
        connection = self.connect()
        try:
            connection.executescript(SCHEMA_SQL)
            self._migrate_execution_knowledge_lineage_unique_key(connection)
            columns = {str(row[1]) for row in connection.execute("pragma table_info(review_tasks)")}
            if "pharmacy_id" not in columns:
                connection.execute("alter table review_tasks add column pharmacy_id integer")
            review_column_migrations = {
                "source_job_id": "text references workflow_jobs(job_id)",
                "completion_postcondition_json": "text",
                "completion_postcondition_sha256": "text",
            }
            for column_name, column_type in review_column_migrations.items():
                if column_name not in columns:
                    connection.execute(
                        f"alter table review_tasks add column {column_name} {column_type}"
                    )
            followup_columns = {
                str(row[1]) for row in connection.execute("pragma table_info(followups)")
            }
            if "plan_id" not in followup_columns:
                connection.execute("alter table followups add column plan_id text")
            if "execution_id" not in followup_columns:
                connection.execute(
                    "alter table followups add column execution_id text "
                    "references executions(execution_id)"
                )
            job_columns = {
                str(row[1]) for row in connection.execute("pragma table_info(workflow_jobs)")
            }
            job_column_migrations = {
                "execution_id": "text references executions(execution_id)",
                "lease_until": "text",
                "claim_token": "text",
                "attempt_count": "integer not null default 0",
                "last_error": "text",
            }
            for column_name, column_type in job_column_migrations.items():
                if column_name not in job_columns:
                    connection.execute(
                        f"alter table workflow_jobs add column {column_name} {column_type}"
                    )
            connection.execute(
                """
                update workflow_jobs
                set status='CANCELLED', last_error='LEGACY_UNLINKED_EXECUTION'
                where execution_id is null and status in ('READY', 'CLAIMED')
                """
            )
            connection.execute(
                """
                update followups set status='CLOSED'
                where execution_id is null and status in ('OPEN', 'REEVALUATION_QUEUED')
                """
            )
            event_columns = {
                str(row[1]) for row in connection.execute("pragma table_info(execution_events)")
            }
            if "consent_snapshot_id" not in event_columns:
                connection.execute(
                    "alter table execution_events add column consent_snapshot_id "
                    "references consent_snapshots(consent_snapshot_id)"
                )
                connection.execute(
                    """
                    update execution_events
                    set consent_snapshot_id=(
                      select executions.consent_snapshot_id
                      from executions
                      where executions.execution_id=execution_events.execution_id
                    )
                    where consent_snapshot_id is null
                    """
                )
            connection.commit()
            self._migrate_event_mutation_schema_v8(connection)
            passage_columns = {
                str(row[1]) for row in connection.execute("pragma table_info(evidence_passages)")
            }
            passage_column_migrations = {
                "page_or_section": "text",
                "line_start": "integer",
                "line_end": "integer",
                "metadata_json": "text not null default '{}'",
            }
            for column_name, column_type in passage_column_migrations.items():
                if column_name not in passage_columns:
                    connection.execute(
                        f"alter table evidence_passages add column {column_name} {column_type}"
                    )
            connection.execute(
                "update evidence_passages set metadata_json='{}' where metadata_json is null"
            )
            agent_step_columns = {
                str(row[1]) for row in connection.execute("pragma table_info(agent_steps)")
            }
            for column_name in ("binding_json", "binding_sha256"):
                if column_name not in agent_step_columns:
                    connection.execute(
                        f"alter table agent_steps add column {column_name} text"
                    )
            recommendation_columns = {
                str(row[1])
                for row in connection.execute("pragma table_info(recommendation_runs)")
            }
            if "idempotency_identity" not in recommendation_columns:
                connection.execute(
                    "alter table recommendation_runs add column idempotency_identity text"
                )
            connection.execute(
                "create unique index if not exists "
                "idx_recommendation_runs_idempotency_identity_unique "
                "on recommendation_runs(idempotency_identity) "
                "where idempotency_identity is not null"
            )
            connection.execute(
                """
                insert or ignore into active_profile_consents(
                  profile_id, consent_snapshot_id, updated_at
                )
                select e.profile_id, e.consent_snapshot_id, e.updated_at
                from executions e
                where e.rowid=(
                  select latest.rowid
                  from executions latest
                  where latest.profile_id=e.profile_id
                  order by latest.created_at desc, latest.rowid desc
                  limit 1
                )
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, datetime.now(UTC).isoformat()),
            )
            connection.commit()
        finally:
            connection.close()
        self.complete_pending_secure_compactions()

    @staticmethod
    def _migrate_event_mutation_schema_v8(
        connection: sqlite3.Connection,
    ) -> None:
        event_columns = {
            str(row[1]) for row in connection.execute("pragma table_info(execution_events)")
        }
        behavior_columns = {
            str(row[1]) for row in connection.execute("pragma table_info(behavior_events)")
        }
        mutation_columns = {
            str(row[1]) for row in connection.execute("pragma table_info(event_mutations)")
        }
        required_mutation_columns = {
            "previous_mutation_id",
            "previous_mutation_sha256",
            "mutation_index",
            "mutation_sha256",
        }
        trigger_names = {
            str(row[0])
            for row in connection.execute("select name from sqlite_master where type='trigger'")
        }
        required_trigger_names = {
            "event_mutations_no_update",
            "event_mutations_no_delete",
            "data_mutation_audits_no_update",
            "data_mutation_audits_no_delete",
            "plan_lifecycle_events_no_update",
            "plan_lifecycle_events_no_delete",
            "plan_lifecycle_dependencies_no_update_v2",
            "plan_lifecycle_dependencies_no_delete_v2",
        }
        index_names = {
            str(row[0])
            for row in connection.execute("select name from sqlite_master where type='index'")
        }
        required_index_names = {
            "idx_event_mutations_target_created",
            "idx_event_mutations_target_index",
        }
        table_names = {
            str(row[0])
            for row in connection.execute("select name from sqlite_master where type='table'")
        }
        if (
            {"payload_state", "effective_payload_sha256"}.issubset(event_columns)
            and {"payload_state", "effective_payload_sha256"}.issubset(behavior_columns)
            and required_mutation_columns.issubset(mutation_columns)
            and required_trigger_names.issubset(trigger_names)
            and required_index_names.issubset(index_names)
            and "event_mutation_cleanup" in table_names
        ):
            return

        connection.execute("BEGIN IMMEDIATE")
        try:
            if "payload_state" not in event_columns:
                connection.execute(
                    "alter table execution_events add column payload_state "
                    "text not null default 'ACTIVE' check(payload_state in "
                    "('ACTIVE', 'CORRECTED', 'DELETED'))"
                )
            if "effective_payload_sha256" not in event_columns:
                connection.execute(
                    "alter table execution_events add column "
                    "effective_payload_sha256 text not null default "
                    "'0000000000000000000000000000000000000000000000000000000000000000'"
                )
                connection.execute(
                    "update execution_events set effective_payload_sha256=payload_sha256"
                )
            if "payload_state" not in behavior_columns:
                connection.execute(
                    "alter table behavior_events add column payload_state "
                    "text not null default 'ACTIVE' check(payload_state in "
                    "('ACTIVE', 'CORRECTED', 'DELETED'))"
                )
            if "effective_payload_sha256" not in behavior_columns:
                connection.execute(
                    "alter table behavior_events add column "
                    "effective_payload_sha256 text not null default "
                    "'0000000000000000000000000000000000000000000000000000000000000000'"
                )
                connection.execute(
                    "update behavior_events set effective_payload_sha256=payload_sha256"
                )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS event_mutations (
                  mutation_id TEXT PRIMARY KEY,
                  profile_id TEXT NOT NULL,
                  target_type TEXT NOT NULL CHECK(target_type IN (
                    'execution_event', 'behavior_event'
                  )),
                  target_event_id TEXT NOT NULL,
                  operation TEXT NOT NULL CHECK(operation IN ('correction', 'deletion')),
                  idempotency_key TEXT NOT NULL,
                  request_sha256 TEXT NOT NULL,
                  prior_payload_sha256 TEXT NOT NULL,
                  result_payload_sha256 TEXT NOT NULL,
                  previous_mutation_id TEXT,
                  previous_mutation_sha256 TEXT,
                  mutation_index INTEGER NOT NULL,
                  mutation_sha256 TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  UNIQUE(profile_id, target_type, target_event_id, idempotency_key),
                  UNIQUE(target_type, target_event_id, mutation_index)
                )
                """
            )
            mutation_columns = {
                str(row[1]) for row in connection.execute("pragma table_info(event_mutations)")
            }
            if not required_mutation_columns.issubset(mutation_columns):
                if connection.execute("select count(*) from event_mutations").fetchone()[0]:
                    raise sqlite3.IntegrityError("legacy_event_mutations_require_chain_rebuild")
                for column_name, column_type in {
                    "previous_mutation_id": "text",
                    "previous_mutation_sha256": "text",
                    "mutation_index": "integer",
                    "mutation_sha256": "text",
                }.items():
                    if column_name not in mutation_columns:
                        connection.execute(
                            f"alter table event_mutations add column {column_name} {column_type}"
                        )
            connection.execute(
                "create index if not exists idx_event_mutations_target_created "
                "on event_mutations(target_type, target_event_id, created_at)"
            )
            connection.execute(
                "create unique index if not exists "
                "idx_event_mutations_target_index on "
                "event_mutations(target_type, target_event_id, mutation_index)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS event_mutation_cleanup (
                  mutation_id TEXT PRIMARY KEY REFERENCES event_mutations(mutation_id),
                  status TEXT NOT NULL CHECK(status IN ('PENDING', 'COMPLETE')),
                  requested_at TEXT NOT NULL,
                  completed_at TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS event_mutations_no_update
                BEFORE UPDATE ON event_mutations
                BEGIN
                  SELECT RAISE(ABORT, 'event_mutations_append_only');
                END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS event_mutations_no_delete
                BEFORE DELETE ON event_mutations
                BEGIN
                  SELECT RAISE(ABORT, 'event_mutations_append_only');
                END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS data_mutation_audits_no_update
                BEFORE UPDATE ON audit_events
                WHEN OLD.event_type IN ('data_correction', 'data_deletion')
                BEGIN
                  SELECT RAISE(ABORT, 'data_mutation_audits_append_only');
                END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS data_mutation_audits_no_delete
                BEFORE DELETE ON audit_events
                WHEN OLD.event_type IN ('data_correction', 'data_deletion')
                BEGIN
                  SELECT RAISE(ABORT, 'data_mutation_audits_append_only');
                END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS plan_lifecycle_events_no_update
                BEFORE UPDATE ON execution_events
                WHEN json_extract(OLD.payload_json, '$.schema_version') =
                  'plan_lifecycle_transition_v1'
                  OR EXISTS (
                    SELECT 1 FROM execution_events AS lifecycle
                    WHERE lifecycle.payload_state='ACTIVE'
                      AND json_extract(lifecycle.payload_json, '$.schema_version')=
                        'plan_lifecycle_transition_v1'
                      AND json_extract(
                        lifecycle.payload_json, '$.replacement_candidate_event_id'
                      )=OLD.event_id
                  )
                BEGIN
                  SELECT RAISE(ABORT, 'plan_lifecycle_event_immutable');
                END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS plan_lifecycle_events_no_delete
                BEFORE DELETE ON execution_events
                WHEN json_extract(OLD.payload_json, '$.schema_version') =
                  'plan_lifecycle_transition_v1'
                  OR EXISTS (
                    SELECT 1 FROM execution_events AS lifecycle
                    WHERE lifecycle.payload_state='ACTIVE'
                      AND json_extract(lifecycle.payload_json, '$.schema_version')=
                        'plan_lifecycle_transition_v1'
                      AND json_extract(
                        lifecycle.payload_json, '$.replacement_candidate_event_id'
                      )=OLD.event_id
                  )
                BEGIN
                  SELECT RAISE(ABORT, 'plan_lifecycle_event_immutable');
                END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS plan_lifecycle_dependencies_no_update_v2
                BEFORE UPDATE ON execution_events
                WHEN EXISTS (
                  SELECT 1 FROM execution_events AS lifecycle
                  WHERE lifecycle.payload_state='ACTIVE'
                    AND json_extract(lifecycle.payload_json, '$.schema_version')=
                      'plan_lifecycle_transition_v1'
                    AND json_extract(
                      lifecycle.payload_json, '$.replacement_candidate_event_id'
                    )=OLD.event_id
                )
                BEGIN
                  SELECT RAISE(ABORT, 'plan_lifecycle_event_immutable');
                END
                """
            )
            connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS plan_lifecycle_dependencies_no_delete_v2
                BEFORE DELETE ON execution_events
                WHEN EXISTS (
                  SELECT 1 FROM execution_events AS lifecycle
                  WHERE lifecycle.payload_state='ACTIVE'
                    AND json_extract(lifecycle.payload_json, '$.schema_version')=
                      'plan_lifecycle_transition_v1'
                    AND json_extract(
                      lifecycle.payload_json, '$.replacement_candidate_event_id'
                    )=OLD.event_id
                )
                BEGIN
                  SELECT RAISE(ABORT, 'plan_lifecycle_event_immutable');
                END
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, datetime.now(UTC).isoformat()),
            )
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()

    def secure_compact(self) -> None:
        """Overwrite deleted payload pages and truncate the SQLite WAL."""
        connection = self.connect()
        try:
            checkpoint = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            if checkpoint is not None and int(checkpoint[0]) != 0:
                raise sqlite3.OperationalError("secure_checkpoint_busy")
            connection.execute("VACUUM")
            checkpoint = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            if checkpoint is not None and int(checkpoint[0]) != 0:
                raise sqlite3.OperationalError("secure_checkpoint_busy")
        finally:
            connection.close()

    def complete_pending_secure_compactions(self) -> None:
        if "event_mutation_cleanup" not in self.table_names():
            return
        pending_mutation_ids = [
            str(row["mutation_id"])
            for row in self.rows(
                "select mutation_id from event_mutation_cleanup "
                "where status='PENDING' order by mutation_id"
            )
        ]
        if not pending_mutation_ids:
            return
        self.secure_compact()
        placeholders = ",".join("?" for _ in pending_mutation_ids)
        with self.transaction(immediate=True) as connection:
            connection.execute(
                f"""
                update event_mutation_cleanup
                set status='COMPLETE', completed_at=?
                where status='PENDING' and mutation_id in ({placeholders})
                """,
                (datetime.now(UTC).isoformat(), *pending_mutation_ids),
            )

    @staticmethod
    def _migrate_execution_knowledge_lineage_unique_key(
        connection: sqlite3.Connection,
    ) -> None:
        table_row = connection.execute(
            "select sql from sqlite_master "
            "where type='table' and name='execution_knowledge_lineage'"
        ).fetchone()
        if table_row is None:
            return
        normalized_sql = "".join(str(table_row[0]).lower().split())
        corrected_unique = "unique(execution_id,event_id,output_type,output_key,claim_id,rule_id)"
        if corrected_unique in normalized_sql:
            return

        connection.execute("PRAGMA foreign_keys = OFF")
        try:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    "ALTER TABLE execution_knowledge_lineage "
                    "RENAME TO execution_knowledge_lineage_v6"
                )
                connection.execute("DROP INDEX IF EXISTS idx_execution_knowledge_lineage_execution")
                connection.execute(
                    """
                    CREATE TABLE execution_knowledge_lineage (
                      lineage_id TEXT PRIMARY KEY,
                      execution_id TEXT NOT NULL REFERENCES executions(execution_id),
                      event_id TEXT NOT NULL REFERENCES execution_events(event_id),
                      output_type TEXT NOT NULL CHECK(output_type IN (
                        'recommendation_item',
                        'safety_rule',
                        'recommendation_decision'
                      )),
                      output_key TEXT NOT NULL,
                      rule_id TEXT NOT NULL REFERENCES knowledge_rules(rule_id),
                      claim_id TEXT NOT NULL REFERENCES knowledge_claims(claim_id),
                      evidence_id TEXT NOT NULL REFERENCES evidence_passages(evidence_id),
                      source_id TEXT NOT NULL REFERENCES source_registry(source_id),
                      data_class TEXT NOT NULL,
                      created_at TEXT NOT NULL,
                      UNIQUE(
                        execution_id, event_id, output_type, output_key,
                        claim_id, rule_id
                      )
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO execution_knowledge_lineage(
                      lineage_id, execution_id, event_id, output_type, output_key,
                      rule_id, claim_id, evidence_id, source_id, data_class, created_at
                    )
                    SELECT
                      lineage_id, execution_id, event_id, output_type, output_key,
                      rule_id, claim_id, evidence_id, source_id, data_class, created_at
                    FROM execution_knowledge_lineage_v6
                    """
                )
                connection.execute("DROP TABLE execution_knowledge_lineage_v6")
                connection.execute(
                    "CREATE INDEX idx_execution_knowledge_lineage_execution "
                    "ON execution_knowledge_lineage(execution_id, created_at)"
                )
                foreign_key_violation = connection.execute("PRAGMA foreign_key_check").fetchone()
                if foreign_key_violation is not None:
                    raise sqlite3.IntegrityError(
                        "execution_knowledge_lineage migration violated a foreign key"
                    )
            except Exception:
                connection.rollback()
                raise
            else:
                connection.commit()
        finally:
            connection.execute("PRAGMA foreign_keys = ON")

    def is_migrated(self) -> bool:
        if not self.database_path.exists():
            return False
        try:
            return self.scalar("select max(version) from schema_migrations") == SCHEMA_VERSION
        except sqlite3.OperationalError:
            return False

    def scalar(self, sql: str, parameters: tuple[Any, ...] = ()) -> Any:
        connection = self.connect()
        try:
            row = connection.execute(sql, parameters).fetchone()
        finally:
            connection.close()
        return None if row is None else row[0]

    def rows(
        self,
        sql: str,
        parameters: tuple[Any, ...] = (),
    ) -> list[sqlite3.Row]:
        connection = self.connect()
        try:
            return list(connection.execute(sql, parameters).fetchall())
        finally:
            connection.close()

    def table_names(self) -> set[str]:
        rows = self.rows("select name from sqlite_master where type = 'table'")
        return {str(row[0]) for row in rows}
