from __future__ import annotations

import ast
import json
import sqlite3
import urllib.parse
from pathlib import Path

import pytest

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


def _file_snapshot(name: str, file_hash: str) -> dict[str, object]:
    return {
        "path": name,
        "exists": True,
        "sha256": file_hash,
        "size": 12,
    }


def _storage_snapshot() -> dict[str, object]:
    return {
        "database_family": {
            "interim.sqlite3": _file_snapshot("interim.sqlite3", "db-hash"),
            "interim.sqlite3-wal": {
                "path": "interim.sqlite3-wal",
                "exists": False,
            },
            "interim.sqlite3-shm": {
                "path": "interim.sqlite3-shm",
                "exists": False,
            },
        },
        "runtime_controls": {
            "operational_capture.json": {
                "path": "operational_capture.json",
                "exists": False,
            },
        },
        "final_state": {
            "session_state_v1.json": _file_snapshot("session_state_v1.json", "state-hash")
        },
        "receipts": {
            "receipt-a.json": _file_snapshot("receipt-a.json", "receipt-a-hash"),
            "receipt-b.json": _file_snapshot("receipt-b.json", "receipt-b-hash"),
        },
    }


def test_preflight_source_has_no_operational_capture_entrypoints() -> None:
    source_path = ROOT / "scripts/run_final_session_preflight.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    referenced_names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
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
    connection = sqlite3.connect(database)
    try:
        connection.execute("CREATE TABLE evidence (value TEXT NOT NULL)")
        connection.execute("INSERT INTO evidence VALUES ('actual-operational-database')")
        connection.commit()
    finally:
        connection.close()
    database_before = database.read_bytes()
    receipts = root / "data/original_plan/final_session/operational_receipts"
    receipts.mkdir(parents=True)
    (receipts / "receipt-a.json").write_text("receipt-a", encoding="utf-8")
    state_root = receipts.parent
    (state_root / "session_state_v1.json").write_text("{}", encoding="utf-8")

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
        connection = sqlite3.connect(temporary_database)
        try:
            assert connection.execute("SELECT value FROM evidence").fetchone() == (
                "actual-operational-database",
            )
        finally:
            connection.close()
        assert temporary_state_root.parent == temporary_root
        temporary_database.write_bytes(b"temporary-copy-only")
        temporary_state_root.mkdir()
        (temporary_state_root / "session_state_v1.json").write_text("{}", encoding="utf-8")
        return _passing_checks()

    result = preflight.run_preflight(
        root=root,
        web_root=tmp_path / "wellnessbox",
        probe=probe,
    )

    assert result["status"] == "READY"
    assert result["exit_code"] == 0
    assert result["storage"]["database_unchanged"] is True
    assert result["storage"]["runtime_controls_unchanged"] is True
    assert result["storage"]["final_state_unchanged"] is True
    assert result["storage"]["receipt_file_list_unchanged"] is True
    assert result["storage"]["receipt_hashes_unchanged"] is True
    assert database.read_bytes() == database_before
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


@pytest.mark.parametrize(
    ("boundary", "key", "blocker_id"),
    [
        ("database_family", "interim.sqlite3-wal", "OPERATIONAL_DATABASE_CHANGED"),
        ("runtime_controls", "operational_capture.json", "RUNTIME_CONTROL_FILES_CHANGED"),
        ("final_state", "session_state_v1.json", "FINAL_SESSION_STATE_CHANGED"),
        ("receipts", "receipt-a.json", "OPERATIONAL_RECEIPTS_CHANGED"),
    ],
)
def test_classify_result_marks_each_storage_boundary_change_as_error(
    boundary: str,
    key: str,
    blocker_id: str,
) -> None:
    before = _storage_snapshot()
    after = json.loads(json.dumps(before))
    after[boundary][key] = _file_snapshot(key, "changed-hash")

    result = preflight.classify_result(
        _passing_checks(),
        before=before,
        after=after,
    )

    assert result["status"] == "ERROR"
    assert result["exit_code"] == 1
    assert result["status"] == "ERROR"
    assert result["exit_code"] == 1
    assert [item["id"] for item in result["blockers"]] == [blocker_id]


def test_run_preflight_copies_committed_wal_frames_consistently(tmp_path: Path) -> None:
    database = tmp_path / "interim.sqlite3"
    copied_database = tmp_path / "copied.sqlite3"
    writer = sqlite3.connect(database)
    try:
        assert writer.execute("PRAGMA journal_mode=WAL").fetchone() == ("wal",)
        writer.execute("CREATE TABLE evidence (value TEXT NOT NULL)")
        writer.execute("INSERT INTO evidence VALUES ('committed-in-wal')")
        writer.commit()
        assert database.with_name("interim.sqlite3-wal").stat().st_size > 0
        source_before = preflight._database_family_snapshot(database)

        preflight.copy_sqlite_database(database, copied_database)
        assert preflight._database_family_snapshot(database) == source_before
        copied = sqlite3.connect(copied_database)
        try:
            assert copied.execute("SELECT value FROM evidence").fetchone() == ("committed-in-wal",)
            assert copied.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        finally:
            copied.close()
    finally:
        writer.close()


@pytest.mark.parametrize(
    ("script", "expected"),
    [
        (
            "",
            {"preselected_count": 1, "prefilled_comment_count": 1},
        ),
        (
            "<script>document.querySelector('input').checked=true;"
            "document.querySelector('textarea').value='dynamic';</script>",
            {"preselected_count": 1, "prefilled_comment_count": 1},
        ),
    ],
)
def test_inspect_rendered_h005_detects_static_and_dynamic_defaults(
    script: str,
    expected: dict[str, int],
) -> None:
    static_values = " checked" if not script else ""
    static_comment = "static" if not script else ""
    html = (
        "<section><h2>Case</h2>"
        f"<input type='radio'{static_values}>"
        f"<textarea>{static_comment}</textarea>{script}</section>"
    )
    url = "data:text/html," + urllib.parse.quote(html)

    result = preflight.inspect_rendered_h005(url, web_root=ROOT.parent / "wellnessbox")

    assert result["status"] == 0
    assert result["case_count"] == 1
    assert result["comment_count"] == 1
    assert result["preselected_count"] == expected["preselected_count"]
    assert result["prefilled_comment_count"] == expected["prefilled_comment_count"]
