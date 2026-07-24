from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "etc/local_research_runtime/interim.sqlite3"


def main() -> int:
    if not DATABASE.is_file():
        print(json.dumps({"database": str(DATABASE), "status": "missing"}, ensure_ascii=False))
        return 1
    with sqlite3.connect(DATABASE) as connection:
        actual_profiles = connection.execute(
            "select count(distinct profile_id) from profile_snapshots "
            "where data_class = 'INTERIM_RUNTIME_EVENT'"
        ).fetchone()[0]
        pending_drafts = connection.execute(
            "select count(*) from ai_drafts where review_status = 'pending'"
        ).fetchone()[0]
    result = {
        "database": str(DATABASE),
        "distinct_actual_profiles": actual_profiles,
        "target_distinct_profiles": 5,
        "pending_pharmacist_drafts": pending_drafts,
        "automatic_receipt_generation": False,
        "next_action": "사람이 실제 프로필의 전체 경로를 실행한다",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
