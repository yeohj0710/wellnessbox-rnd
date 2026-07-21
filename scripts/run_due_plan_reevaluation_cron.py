from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from wellnessbox_rnd.interim.jobs import WorkflowJobQueue
from wellnessbox_rnd.interim.store import InterimStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(os.getenv("WB_RND_INTERIM_DATABASE", "artifacts/interim.sqlite3")),
    )
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    store = InterimStore(args.database)
    store.migrate()
    result = WorkflowJobQueue(store).enqueue_due_plan_reevaluations(
        as_of=datetime.fromisoformat(args.as_of)
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
