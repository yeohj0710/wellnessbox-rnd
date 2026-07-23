from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wellnessbox_rnd.governance.final_session_console import run_rehearsal  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="wellnessbox-final-session-smoke-") as temp:
        result = run_rehearsal(ROOT, Path(temp))
        evidence = {
            "schema_version": result["schema_version"],
            "data_class": "SIMULATION",
            "step_statuses": {key: value["status"] for key, value in result["steps"].items()},
            "audit": result["audit"],
            "production_paths_touched": result["production_paths_touched"],
        }
    output = ROOT / "data/original_plan/evidence/final_session_console_rehearsal_v1.json"
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
