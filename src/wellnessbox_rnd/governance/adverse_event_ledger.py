"""Count adverse events reported for engine-recommended supplement use.

KPI-6 is `Count_12 = Σ 1(AE_reported(i))` over the twelve months before the
measurement date, and it passes at five or fewer. Zero is a passing number, but
zero out of nothing is not a measurement — the count only means something when
there were users to report.

So this module reports two things side by side: how many adverse events were
reported, and how many engine-recommended sessions there were to report from. A
run with no exposure is reported as `INSUFFICIENT_EXPOSURE`, not as a pass.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "adverse_event_ledger_v1"
TARGET_MAX_EVENTS = 5
WINDOW_MONTHS = 12
_DAYS_PER_WINDOW = 365


def window_start(measured_at: str) -> str:
    """Return the ISO timestamp twelve months before the measurement date."""
    parsed = datetime.fromisoformat(measured_at.replace("Z", "+00:00")).astimezone(UTC)
    return (parsed - timedelta(days=_DAYS_PER_WINDOW)).isoformat().replace("+00:00", "Z")


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    row = connection.execute(
        "select 1 from sqlite_master where type='table' and name=?", (name,)
    ).fetchone()
    return row is not None


def read_operational_exposure(database: Path, *, since: str) -> dict[str, int]:
    """Count engine-recommended sessions and reported adverse events in the window."""
    if not Path(database).is_file():
        return {"recommendation_sessions": 0, "distinct_users": 0, "adverse_events": 0}
    connection = sqlite3.connect(f"file:{Path(database)}?mode=ro", uri=True)
    try:
        sessions = users = events = 0
        if _table_exists(connection, "profile_snapshots"):
            sessions = connection.execute(
                "select count(*) from profile_snapshots "
                "where data_class = 'INTERIM_RUNTIME_EVENT' and created_at >= ?",
                (since,),
            ).fetchone()[0]
            users = connection.execute(
                "select count(distinct profile_id) from profile_snapshots "
                "where data_class = 'INTERIM_RUNTIME_EVENT' and created_at >= ?",
                (since,),
            ).fetchone()[0]
        if _table_exists(connection, "adverse_events"):
            # The ledger already separates events tied to a recommendation, which is
            # exactly what KPI-6 counts. observation_month is a YYYY-MM string.
            events = connection.execute(
                "select count(*) from adverse_events "
                "where related_to_recommendation = 1 and observation_month >= ?",
                (since[:7],),
            ).fetchone()[0]
    finally:
        connection.close()
    return {
        "recommendation_sessions": int(sessions),
        "distinct_users": int(users),
        "adverse_events": int(events),
    }


def load_external_reports(path: Path | None) -> dict[str, Any]:
    """Read adverse events collected outside the research runtime, if declared.

    A separately operated site can contribute only when its records say the
    supplement use came from this engine's recommendation. Rows without that
    attribution are counted separately and excluded from the KPI.
    """
    if path is None or not Path(path).is_file():
        return {"declared": False, "attributed": 0, "unattributed": 0, "source": None}
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("reports", [])
    attributed = [row for row in rows if row.get("engine_recommended") is True]
    return {
        "declared": True,
        "source": payload.get("source_system"),
        "attributed": len(attributed),
        "unattributed": len(rows) - len(attributed),
        "attribution_note": (
            "engine_recommended=true 인 보고만 KPI-6에 포함한다. 지표 정의가 "
            "'엔진 추천 건강기능식품 복용으로 인한' 이상반응이기 때문이다."
        ),
    }


def build_adverse_event_report_v1(
    *,
    measured_at: str,
    exposure: dict[str, int],
    external: dict[str, Any],
    minimum_sessions: int = 1,
) -> dict[str, Any]:
    """Combine internal and attributed external counts into a KPI-6 verdict."""
    since = window_start(measured_at)
    total_events = int(exposure["adverse_events"]) + int(external.get("attributed", 0))
    total_sessions = int(exposure["recommendation_sessions"])
    has_exposure = total_sessions >= minimum_sessions

    if not has_exposure:
        status = "INSUFFICIENT_EXPOSURE"
    elif total_events <= TARGET_MAX_EVENTS:
        status = "READY"
    else:
        status = "ABOVE_TARGET"

    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "measured_at": measured_at,
        "window_start": since,
        "window_months": WINDOW_MONTHS,
        "target_max_events": TARGET_MAX_EVENTS,
        "adverse_event_count": total_events,
        "meets_target": status == "READY",
        "exposure": {
            "recommendation_sessions": total_sessions,
            "distinct_users": int(exposure["distinct_users"]),
            "minimum_sessions_required": minimum_sessions,
            "has_exposure": has_exposure,
        },
        "internal_adverse_events": int(exposure["adverse_events"]),
        "external_source": external,
        "measurement_environment": "research_phase_internal_measurement",
        "interpretation": (
            "노출이 없으면 0건은 통과가 아니라 측정 불가다. 12개월 창 안에 엔진 추천 세션이 "
            "있어야 0건이 의미를 가진다."
            if not has_exposure
            else "12개월 창의 엔진 추천 복용 관련 이상반응 보고 집계다."
        ),
    }
