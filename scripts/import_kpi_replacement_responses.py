"""Validate and store the returned KPI replacement inputs without adjudicating them."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import zipfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.build_kpi_replacement_handoff import (  # noqa: E402
    OUTPUT_DIR,
    REQUEST_NAMES,
    RESPONSE_NAMES,
    build_candidates,
)
from wellnessbox_rnd.evals.adaptive_answer_key_review import (  # noqa: E402
    agent_family,
    register_blind_primary_ai_draft,
    register_independent_ai_review,
)
from wellnessbox_rnd.evals.answer_key_workbench import Workbench  # noqa: E402
from wellnessbox_rnd.governance.reviewer_credentials import (  # noqa: E402
    load_registry as load_identity_registry,
)
from wellnessbox_rnd.governance.reviewer_credentials import (  # noqa: E402
    registered_reviewer_identity_references,
)

SELECTION_NAME = "reviewer_identity_selection.json"
RETURN_ZIP_NAME = "kpi_replacement_completed.zip"
STAGING_PATH = OUTPUT_DIR / "kpi_replacement_staging_v1.json"
RESPONSE_DIR = OUTPUT_DIR / "responses"
INVALID_AGENT_NAMES = {
    "anthropic",
    "claude",
    "not_recorded",
    "unknown",
    "placeholder",
}
ALLOWED_ANTHROPIC_MODEL_IDS = frozenset({"claude-opus-5"})


class SnapshotZip:
    def __init__(self, source: Path):
        self.source_bytes = source.read_bytes()
        self.sha256 = hashlib.sha256(self.source_bytes).hexdigest()
        self.archive = zipfile.ZipFile(io.BytesIO(self.source_bytes))

    def read(self, name: str) -> bytes:
        try:
            return self.archive.read(name)
        except KeyError as exc:
            raise ValueError(f"replacement_return_file_missing:{name}") from exc

    def close(self) -> None:
        self.archive.close()


def _load_json(reader: SnapshotZip, name: str) -> tuple[dict[str, Any], bytes]:
    content = reader.read(name)
    payload = json.loads(content.decode("utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"replacement_return_json_object_required:{name}")
    return payload, content


def _parse_confirmed_at(value: str) -> str:
    text = value.strip()
    try:
        stamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("identity_confirmation_time_invalid") from exc
    if stamp.tzinfo is None:
        raise ValueError("identity_confirmation_timezone_missing")
    return stamp.isoformat()


def _validate_identity_selection(payload: dict[str, Any]) -> dict[str, str]:
    if payload.get("schema_version") != "kpi_reviewer_identity_selection_v1":
        raise ValueError("identity_selection_schema_invalid")
    selected = str(payload.get("selected_reviewer_identity_ref", "")).strip()
    registry = load_identity_registry(ROOT)
    eligible_registry = {
        **registry,
        "registered_reviewers": [
            entry
            for entry in registry.get("registered_reviewers", [])
            if entry.get("may_review_h005") is True
        ],
    }
    trusted = registered_reviewer_identity_references(eligible_registry)
    if selected not in trusted:
        raise ValueError("identity_selection_not_registered")
    return {
        "reviewer_identity_ref": selected,
        "confirmed_at": _parse_confirmed_at(
            str(payload.get("confirmed_at", ""))
        ),
    }


def _actual_anthropic_agent(payload: dict[str, Any], key: str) -> str:
    agent = str(payload.get(key, "")).strip()
    if (
        agent.casefold() in INVALID_AGENT_NAMES
        or agent_family(agent) != "anthropic"
        or agent.casefold() not in ALLOWED_ANTHROPIC_MODEL_IDS
    ):
        raise ValueError(f"replacement_response_agent_invalid:{key}")
    return agent


def _required_blinded_from(request: dict[str, Any]) -> list[str]:
    return list(request["packet"]["required_blinded_from"])


def validate_return(source: Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    reader = SnapshotZip(source)
    try:
        selection_payload, selection_bytes = _load_json(reader, SELECTION_NAME)
        identity = _validate_identity_selection(selection_payload)
        candidates = build_candidates()
        records: dict[str, Any] = {}
        response_bytes: dict[str, bytes] = {
            RETURN_ZIP_NAME: reader.source_bytes,
            SELECTION_NAME: selection_bytes,
        }

        for indicator_id in ("KPI-1", "KPI-4", "KPI-5"):
            request = json.loads(
                (OUTPUT_DIR / REQUEST_NAMES[indicator_id]).read_text(
                    encoding="utf-8"
                )
            )
            response, raw = _load_json(reader, RESPONSE_NAMES[indicator_id])
            response_bytes[RESPONSE_NAMES[indicator_id]] = raw
            workbench = Workbench(
                indicator_id,
                deepcopy(candidates[indicator_id]),
            )
            if indicator_id == "KPI-4":
                workbench.primary_ai_draft = {
                    "answer_vocabulary": list(request["packet"]["answer_vocabulary"])
                }
                agent = _actual_anthropic_agent(response, "drafting_agent")
                record = register_blind_primary_ai_draft(
                    workbench,
                    drafting_agent=agent,
                    draft_source=str(response.get("draft_source", "")),
                    blinded_from=list(response.get("blinded_from", [])),
                    required_blinded_from=_required_blinded_from(request),
                    packet_sha256=str(response.get("packet_sha256", "")),
                    engine_output_consulted=bool(
                        response.get("engine_output_consulted", False)
                    ),
                    cases=list(response.get("cases", [])),
                    input_response_sha256=hashlib.sha256(raw).hexdigest(),
                )
            else:
                agent = _actual_anthropic_agent(response, "reviewing_agent")
                record = register_independent_ai_review(
                    workbench,
                    reviewing_agent=agent,
                    review_source=str(response.get("review_source", "")),
                    blinded_from=list(response.get("blinded_from", [])),
                    required_blinded_from=_required_blinded_from(request),
                    packet_sha256=str(response.get("packet_sha256", "")),
                    engine_output_consulted=bool(
                        response.get("engine_output_consulted", False)
                    ),
                    cases=list(response.get("cases", [])),
                )
            records[indicator_id] = {
                "response_sha256": hashlib.sha256(raw).hexdigest(),
                "validated_record": record,
            }
        staging = {
            "schema_version": "kpi_replacement_staging_v1",
            "source_zip_sha256": reader.sha256,
            "identity_confirmation": identity,
            "counts": {
                indicator_id: len(items)
                for indicator_id, items in candidates.items()
            },
            "responses": records,
            "status": "READY_FOR_KPI4_SECOND_OPINION_AND_FINAL_REVIEW",
        }
        return staging, response_bytes
    finally:
        reader.close()


def apply_return(source: Path) -> dict[str, Any]:
    staging, response_bytes = validate_return(source)
    RESPONSE_DIR.mkdir(parents=True, exist_ok=True)
    snapshots = {
        STAGING_PATH: STAGING_PATH.read_bytes() if STAGING_PATH.is_file() else None,
        **{
            RESPONSE_DIR / name: (
                (RESPONSE_DIR / name).read_bytes()
                if (RESPONSE_DIR / name).is_file()
                else None
            )
            for name in response_bytes
        },
    }
    try:
        STAGING_PATH.write_text(
            json.dumps(staging, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        for name, content in response_bytes.items():
            (RESPONSE_DIR / name).write_bytes(content)
    except Exception:
        for path, content in snapshots.items():
            if content is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(content)
        raise
    return {
        "status": staging["status"],
        "source_zip_sha256": staging["source_zip_sha256"],
        "counts": staging["counts"],
        "staging_path": str(STAGING_PATH),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.input.is_file():
        raise SystemExit(f"replacement_return_missing:{args.input}")
    try:
        if args.apply:
            report = apply_return(args.input)
        else:
            staging, _ = validate_return(args.input)
            report = {
                "status": "READY_TO_IMPORT",
                "source_zip_sha256": staging["source_zip_sha256"],
                "counts": staging["counts"],
            }
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
