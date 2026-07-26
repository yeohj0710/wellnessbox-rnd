from __future__ import annotations

import ast
from pathlib import Path

from scripts import run_final_session_preflight as preflight

ROOT = Path(__file__).resolve().parents[1]


def _passing_checks(*, preselected: int = 0, prefilled: int = 0) -> dict[str, object]:
    return {
        "rnd_health": 200,
        "console_home": 200,
        "console_state": 200,
        "wellnessbox_health": 200,
        "tips": {
            "login_status": 307,
            "page_status": 200,
            "final_url": "http://127.0.0.1:3001/tips",
        },
        "pharmacist": {
            "login_status": 307,
            "page_status": 200,
            "final_url": "http://127.0.0.1:3001/pharm/tips",
        },
        "h005": {
            "status": 200,
            "case_count": 10,
            "preselected_count": preselected,
            "comment_count": 10,
            "prefilled_comment_count": prefilled,
        },
    }


def _storage_snapshot(*, database_hash: str = "db-hash") -> dict[str, object]:
    return {
        "database": {
            "path": "interim.sqlite3",
            "sha256": database_hash,
            "size": 12,
        },
        "receipts": {
            "receipt-a.json": "receipt-a-hash",
            "receipt-b.json": "receipt-b-hash",
        },
    }


def test_preflight_source_has_no_operational_capture_entrypoints() -> None:
    source_path = ROOT / "scripts/run_final_session_preflight.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    referenced_names = {
        node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
    } | {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }

    assert "begin_session" not in referenced_names
    assert "finish_session" not in referenced_names
    assert "CAPTURE_PATH" not in referenced_names
    assert "STATE_PATH" not in referenced_names
    assert "scripts.run_local_research_session" not in source


def test_run_preflight_passes_only_temporary_database_and_state_to_probe(
    tmp_path: Path,
) -> None:
    root = tmp_path / "wellnessbox-rnd"
    database = root / "etc/local_research_runtime/interim.sqlite3"
    database.parent.mkdir(parents=True)
    database.write_bytes(b"actual-operational-database")
    receipts = root / "data/original_plan/final_session/operational_receipts"
    receipts.mkdir(parents=True)
    (receipts / "receipt-a.json").write_text("receipt-a", encoding="utf-8")

    def probe(
        probe_root: Path,
        web_root: Path,
        temporary_database: Path,
        temporary_state_root: Path,
        temporary_root: Path,
    ) -> dict[str, object]:
        assert probe_root == root
        assert web_root == tmp_path / "wellnessbox"
        assert temporary_root != root
        assert temporary_database.parent == temporary_root
        assert temporary_database.read_bytes() == b"actual-operational-database"
        assert temporary_state_root.parent == temporary_root
        temporary_database.write_bytes(b"temporary-copy-only")
        temporary_state_root.mkdir()
        (temporary_state_root / "session_state_v1.json").write_text(
            "{}", encoding="utf-8"
        )
        return _passing_checks()

    result = preflight.run_preflight(
        root=root,
        web_root=tmp_path / "wellnessbox",
        probe=probe,
    )

    assert result["status"] == "READY"
    assert result["exit_code"] == 0
    assert result["storage"]["database_unchanged"] is True
    assert result["storage"]["receipt_file_list_unchanged"] is True
    assert result["storage"]["receipt_hashes_unchanged"] is True
    assert database.read_bytes() == b"actual-operational-database"
    assert sorted(path.name for path in receipts.iterdir()) == ["receipt-a.json"]


def test_classify_result_blocks_h005_ten_of_ten_prefill() -> None:
    snapshot = _storage_snapshot()

    result = preflight.classify_result(
        _passing_checks(preselected=10, prefilled=10),
        before=snapshot,
        after=snapshot,
    )

    assert result["status"] == "BLOCKED"
    assert result["exit_code"] == 2
    assert result["checks"]["h005"]["preselected_count"] == 10
    assert result["checks"]["h005"]["prefilled_comment_count"] == 10
    assert result["blockers"] == [
        {
            "id": "H005_FORM_NOT_NEUTRAL",
            "message": "H-005 10/10 cases are preselected and 10/10 comments are prefilled.",
        }
    ]


def test_classify_result_marks_storage_change_as_error() -> None:
    before = _storage_snapshot()
    after = _storage_snapshot(database_hash="changed-db-hash")
    after["receipts"] = {"receipt-a.json": "changed-receipt-hash"}

    result = preflight.classify_result(
        _passing_checks(),
        before=before,
        after=after,
    )

    assert result["status"] == "ERROR"
    assert result["exit_code"] == 1
    assert result["storage"] == {
        "database_unchanged": False,
        "receipt_file_list_unchanged": False,
        "receipt_hashes_unchanged": False,
    }
    assert [item["id"] for item in result["blockers"]] == [
        "OPERATIONAL_DATABASE_CHANGED",
        "OPERATIONAL_RECEIPTS_CHANGED",
    ]
