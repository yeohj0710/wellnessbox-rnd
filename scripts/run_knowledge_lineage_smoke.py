from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.inference_api.main import app  # noqa: E402
from wellnessbox_rnd.interim.store import SCHEMA_VERSION, InterimStore  # noqa: E402

INTERNAL_TOKEN = "op023-op024-knowledge-lineage-smoke-token"


def _request() -> dict[str, Any]:
    return {
        "request_id": "op023-op024-knowledge-lineage-smoke",
        "source_profile": {
            "schema_version": "wellnessbox.chat.UserProfile.v1",
            "subject_id": "usr_cccccccccccccccccccccccccccccccc",
            "profile": {
                "age": 58,
                "sex": "male",
                "goals": ["heart_health"],
            },
        },
        "user_profile": {
            "age": 58,
            "biological_sex": "male",
            "pregnant": False,
        },
        "goals": ["heart_health"],
        "symptoms": ["low_activity_tolerance"],
        "conditions": [],
        "medications": [{"name": "warfarin", "dose": "5mg"}],
        "current_supplements": [{"name": "glucosamine"}],
        "lifestyle": {
            "sleep_hours": 7.0,
            "stress_level": 2,
            "activity_level": "lightly_active",
        },
        "input_availability": {
            "survey": True,
            "nhis": False,
            "wearable": False,
            "cgm": False,
            "genetic": False,
        },
        "data_source_consents": {
            source: {
                "use_for_recommendation": source == "survey",
                "allow_persistent_storage": source == "survey",
            }
            for source in ("survey", "nhis", "wearable", "cgm", "genetic")
        },
    }


def _require_status(response, expected: int, label: str) -> dict[str, Any]:
    if response.status_code != expected:
        raise RuntimeError(
            f"{label}_failed:{response.status_code}:{response.text[:500]}"
        )
    return response.json()


def run_smoke() -> dict[str, Any]:
    previous_database = os.environ.get("WB_RND_INTERIM_DATABASE")
    previous_token = os.environ.get("WB_RND_INTERIM_INTERNAL_TOKEN")
    try:
        with tempfile.TemporaryDirectory(prefix="wb-rnd-knowledge-lineage-") as temp_dir:
            database_path = Path(temp_dir) / "knowledge-lineage.sqlite3"
            os.environ["WB_RND_INTERIM_DATABASE"] = str(database_path)
            os.environ["WB_RND_INTERIM_INTERNAL_TOKEN"] = INTERNAL_TOKEN
            client = TestClient(app)
            response = _require_status(
                client.post("/v1/recommend", json=_request()),
                200,
                "recommendation",
            )
            execution_id = str(response["execution_id"])
            trace = _require_status(
                client.get(
                    f"/v1/interim/executions/{execution_id}",
                    headers={"x-wb-rnd-token": INTERNAL_TOKEN},
                ),
                200,
                "execution_trace",
            )

            store = InterimStore(database_path)
            store.migrate()
            source_count = int(store.scalar("select count(*) from source_registry"))
            passage_count = int(store.scalar("select count(*) from evidence_passages"))
            claim_count = int(store.scalar("select count(*) from knowledge_claims"))
            rule_count = int(store.scalar("select count(*) from knowledge_rules"))
            link_count = int(store.scalar("select count(*) from claim_rule_links"))
            lineage = list(trace["knowledge_lineage"])
            output_types = sorted({str(item["output_type"]) for item in lineage})
            checks = {
                "database_schema_version_matches_current": (
                    store.scalar("select max(version) from schema_migrations")
                    == SCHEMA_VERSION
                ),
                "canonical_artifact_counts_match": (
                    (source_count, passage_count, claim_count, rule_count, link_count)
                    == (3, 5, 5, 5, 5)
                ),
                "actual_response_is_blocked": response["status"] == "blocked",
                "rule_and_decision_outputs_connected": output_types
                == ["recommendation_decision", "safety_rule"],
                "all_lineage_uses_response_execution_id": {
                    str(item["execution_id"]) for item in lineage
                }
                == {execution_id},
                "canonical_rule_claim_source_connected": (
                    {str(item["rule_id"]) for item in lineage}
                    == {"KB-SAFETY-ANTICOAG-001"}
                    and {str(item["claim_id"]) for item in lineage}
                    == {"CLM-KNOWLEDGE-ANTICOAG-001"}
                    and {str(item["source_id"]) for item in lineage}
                    == {"REF-KNOWLEDGE-ANTICOAG-001"}
                ),
                "source_lifecycle_and_span_match": all(
                    item["license_status"] == "APPROVED_INTERNAL"
                    and item["source_uri"]
                    == "data/raw_references/supplement_warfarin_interaction.md"
                    and item["upstream_reference_uri"]
                    == (
                        "data/knowledge/supplements/"
                        "supplement_overdose_and_drug_interactions_expert.md"
                    )
                    and item["source_effective_at"] == "2026-03-10T00:00:00Z"
                    and item["source_retired_at"] is None
                    and (item["line_start"], item["line_end"]) == (13, 33)
                    and len(str(item["source_content_checksum"])) == 64
                    for item in lineage
                ),
            }
            if not all(checks.values()):
                raise RuntimeError(f"knowledge_lineage_smoke_checks_failed:{checks}")

            return {
                "schema_version": "op023_op024_knowledge_lineage_smoke_v1",
                "status": "passed",
                "data_class": "INTERIM_RUNTIME_EVENT",
                "case_count": 1,
                "database_schema_version": SCHEMA_VERSION,
                "source_count": source_count,
                "passage_count": passage_count,
                "claim_count": claim_count,
                "rule_count": rule_count,
                "claim_rule_link_count": link_count,
                "execution_lineage_count": len(lineage),
                "linked_output_types": output_types,
                "parsed_source_uri": (
                    "data/raw_references/supplement_warfarin_interaction.md"
                ),
                "upstream_reference_uri": (
                    "data/knowledge/supplements/"
                    "supplement_overdose_and_drug_interactions_expert.md"
                ),
                "checks": checks,
            }
    finally:
        if previous_database is None:
            os.environ.pop("WB_RND_INTERIM_DATABASE", None)
        else:
            os.environ["WB_RND_INTERIM_DATABASE"] = previous_database
        if previous_token is None:
            os.environ.pop("WB_RND_INTERIM_INTERNAL_TOKEN", None)
        else:
            os.environ["WB_RND_INTERIM_INTERNAL_TOKEN"] = previous_token


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_smoke()
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if arguments.output is None:
        print(rendered, end="")
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
