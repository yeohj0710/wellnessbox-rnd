from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 6

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
  UNIQUE(execution_id, event_id, output_type, output_key, claim_id)
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
  completed_at TEXT
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
  PRIMARY KEY(run_id, step_index)
);

CREATE TABLE IF NOT EXISTS followups (
  followup_id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL REFERENCES user_profiles(profile_id),
  due_at TEXT NOT NULL,
  requested_data_json TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL
);

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
  pharmacy_id INTEGER
);

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
            columns = {str(row[1]) for row in connection.execute("pragma table_info(review_tasks)")}
            if "pharmacy_id" not in columns:
                connection.execute("alter table review_tasks add column pharmacy_id integer")
            event_columns = {
                str(row[1])
                for row in connection.execute("pragma table_info(execution_events)")
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
            passage_columns = {
                str(row[1])
                for row in connection.execute("pragma table_info(evidence_passages)")
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
