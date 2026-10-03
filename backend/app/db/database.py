"""
SQLite Edge Cache — Road Bulletin Storage
==========================================

Provides an async SQLite cache for road-pass status data fetched via
Bright Data Web Unlocker. The cache acts as the second tier in the
circuit breaker:

    Tier 1: Live Bright Data scrape (requires connectivity)
    Tier 2: SQLite edge cache (this module — survives connectivity loss)
    Tier 3: JSON fixture files (always available, baked into the app)

Schema
------
    road_bulletins
        id          INTEGER  PK autoincrement
        region      TEXT     e.g. 'himalaya', 'andes', 'east_africa'
        source_name TEXT     e.g. 'Dochula Pass'
        country     TEXT     e.g. 'Bhutan'
        status      TEXT     'open' | 'closed' | 'restricted'
        reason      TEXT     nullable human-readable description
        severity    TEXT     'none' | 'minor' | 'major' | 'critical'
        last_updated TEXT    ISO-8601 timestamp from the source
        fetched_at  TEXT     ISO-8601 timestamp of our scrape

This module contains no HTTP calls. All I/O is local aiosqlite only.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite

from app.config.settings import settings

# ── SQL statements ────────────────────────────────────────────────────────────

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS road_bulletins (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    region       TEXT    NOT NULL DEFAULT 'himalaya',
    source_name  TEXT    NOT NULL,
    country      TEXT    NOT NULL,
    status       TEXT    NOT NULL CHECK(status IN ('open', 'closed', 'restricted')),
    reason       TEXT,
    severity     TEXT    NOT NULL DEFAULT 'none'
                         CHECK(severity IN ('none', 'minor', 'major', 'critical')),
    last_updated TEXT    NOT NULL,
    fetched_at   TEXT    NOT NULL
);
"""

_INSERT_SQL = """
INSERT INTO road_bulletins
    (region, source_name, country, status, reason, severity, last_updated, fetched_at)
VALUES
    (:region, :source_name, :country, :status, :reason, :severity, :last_updated, :fetched_at);
"""

_SELECT_RECENT_SQL = """
SELECT source_name, country, status, reason, severity, last_updated, fetched_at
FROM   road_bulletins
WHERE  region = :region
  AND  fetched_at >= :cutoff
ORDER  BY fetched_at DESC;
"""

_DELETE_STALE_SQL = """
DELETE FROM road_bulletins
WHERE fetched_at < :cutoff;
"""

_COUNT_SQL = "SELECT COUNT(*) FROM road_bulletins;"


# ── Public API ────────────────────────────────────────────────────────────────

async def init_db(db_path: Optional[str] = None) -> None:
    """
    Create the road_bulletins table if it does not exist.
    Called once at application startup via FastAPI lifespan.

    Parameters
    ----------
    db_path : str, optional
        Override the database path (used in tests to pass ':memory:' or a
        temp file). Defaults to settings.db_path.
    """
    path = db_path or settings.db_path
    # Ensure parent directory exists (creates app/db/ if needed)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(path) as db:
        await db.execute(_CREATE_TABLE_SQL)
        await db.commit()


async def upsert_bulletins(
    records: list[dict],
    region: str = "himalaya",
    db_path: Optional[str] = None,
) -> None:
    """
    Insert a fresh batch of road bulletin records into the cache.
    Does NOT upsert on primary key — inserts new rows so history is preserved.
    Stale rows are pruned by `purge_stale_bulletins()`.

    Parameters
    ----------
    records : list[dict]
        Each dict must contain: source_name, country, status, reason, severity, last_updated.
    region : str
        Region key attached to each record.
    db_path : str, optional
        Override db path for testing.
    """
    path = db_path or settings.db_path
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        {
            "region": region,
            "source_name": r["source_name"],
            "country": r["country"],
            "status": r["status"],
            "reason": r.get("reason"),
            "severity": r.get("severity", "none"),
            "last_updated": r["last_updated"],
            "fetched_at": now,
        }
        for r in records
    ]
    async with aiosqlite.connect(path) as db:
        await db.executemany(_INSERT_SQL, rows)
        await db.commit()


async def get_cached_bulletins(
    region: str = "himalaya",
    max_age_hours: float = 6.0,
    db_path: Optional[str] = None,
) -> list[dict]:
    """
    Retrieve road bulletins from the cache that are no older than max_age_hours.

    Parameters
    ----------
    region : str
        Filter by region key.
    max_age_hours : float
        Maximum acceptable cache age in hours (default 6 h).
    db_path : str, optional
        Override db path for testing.

    Returns
    -------
    list[dict]
        List of bulletin dicts, or empty list if cache is empty / stale.
    """
    from datetime import timedelta

    path = db_path or settings.db_path
    if not Path(path).exists():
        return []

    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    ).isoformat()

    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(_SELECT_RECENT_SQL, {"region": region, "cutoff": cutoff}) as cursor:
            rows = await cursor.fetchall()

    return [dict(row) for row in rows]


async def purge_stale_bulletins(
    max_age_hours: float = 48.0,
    db_path: Optional[str] = None,
) -> None:
    """
    Delete records older than max_age_hours to keep the edge cache lean.
    Intended to be called periodically (e.g., once per day at startup).
    """
    from datetime import timedelta

    path = db_path or settings.db_path
    if not Path(path).exists():
        return

    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    ).isoformat()
    async with aiosqlite.connect(path) as db:
        await db.execute(_DELETE_STALE_SQL, {"cutoff": cutoff})
        await db.commit()


async def count_records(db_path: Optional[str] = None) -> int:
    """Return total row count — used in tests to verify cache writes."""
    path = db_path or settings.db_path
    if not Path(path).exists():
        return 0
    async with aiosqlite.connect(path) as db:
        async with db.execute(_COUNT_SQL) as cursor:
            row = await cursor.fetchone()
    return row[0] if row else 0
