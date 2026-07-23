from __future__ import annotations

import json
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from wellnessbox_rnd.governance.operational_receipts import begin_session, finish_session

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="wb-operational-rehearsal-") as temp:
        directory = Path(temp)
        database = directory / "rehearsal.sqlite3"
        with closing(sqlite3.connect(database)) as connection:
            for table in ("user_profiles", "recommendation_runs", "followups", "review_tasks"):
                connection.execute(f"create table {table}(id text)")
            connection.commit()
        capture = begin_session(ROOT, database, {"rnd_api": "simulation://rnd", "wellnessbox": "simulation://web"})
        capture["data_class"] = "SIMULATION"
        with closing(sqlite3.connect(database)) as connection:
            for table in ("user_profiles", "recommendation_runs", "followups", "review_tasks"):
                connection.execute(f"insert into {table}(id) values ('simulation')")
            connection.commit()
        result = finish_session(
            ROOT, database, capture, directory / "receipts", key_path=None, data_class="SIMULATION"
        )
        assert result["data_class"] == "SIMULATION"
        assert len(result["covered_requirement_ids"]) == 41
        production = ROOT / "data/original_plan/final_session/operational_receipts"
        report = {
            "schema_version": "operational_receipt_collector_rehearsal_v1",
            "status": "PASS",
            "data_class": "SIMULATION",
            "covered_requirement_count": 41,
            "production_receipt_path_touched": False,
            "production_receipt_path": str(production.relative_to(ROOT)),
        }
    output = ROOT / "data/original_plan/evidence/operational_receipt_collector_rehearsal_v1.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
