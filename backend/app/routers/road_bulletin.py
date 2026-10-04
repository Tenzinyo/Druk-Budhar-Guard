"""
GET /road-bulletin — Road Pass Status Bulletin
===============================================

Provides real-time road-pass closure status for mountain communities.
Data directly informs farmers whether access trails to market and
healthcare are safe — a critical complement to the slope audit.

Circuit breaker (three-tier fallback)
--------------------------------------
    Tier 1  Live scrape via Bright Data Web Unlocker proxy
              → parses raw HTML for closure keywords
              → writes results to SQLite edge cache
    Tier 2  SQLite edge cache (max age 6 h)
              → served when Bright Data times out or credentials absent
    Tier 3  Bundled JSON fixture files (always available, zero network)
              → served when cache is empty or stale
              → explicitly labelled data_source='fixture' in response

Bright Data Web Unlocker proxy
-------------------------------
Credentials are configured via environment variables (see .env.example):
    BRIGHTDATA_PROXY_USERNAME
    BRIGHTDATA_PROXY_PASSWORD
    BRIGHTDATA_PROXY_HOST    (default: brd.superproxy.io)
    BRIGHTDATA_PROXY_PORT    (default: 22225)

Target URLs are derived from the region config `road_sources` list.
Each source generates a Google News search query so that Bright Data
fetches the most current closure news without requiring a specific
government portal URL.

When credentials are absent or all requests fail, the circuit breaker
falls through silently to the cache then fixture tier. The response
always includes a `data_source` field so the client can display an
appropriate freshness indicator.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.config.settings import settings
from app.db.database import get_cached_bulletins, upsert_bulletins

router = APIRouter()

# ── Response models ───────────────────────────────────────────────────────────

class RoadStatusItem(BaseModel):
    source_name: str
    country: str
    status: Literal["open", "closed", "restricted"]
    reason: Optional[str] = None
    severity: Literal["none", "minor", "major", "critical"]
    last_updated: str


class RoadBulletinResponse(BaseModel):
    region: str
    roads: list[RoadStatusItem]
    data_source: Literal["live", "cache", "fixture"]
    fetched_at: str
    advisory: Optional[str] = None


# ── HTML keyword parser ────────────────────────────────────────────────────────

_CRITICAL_KEYWORDS = frozenset({"collapse", "collapsed", "washed out", "impassable", "emergency"})
_CLOSURE_KEYWORDS  = frozenset({"closed", "closure", "blocked", "blockage", "landslide",
                                 "rockfall", "flood", "cut off", "cut-off"})
_RESTRICT_KEYWORDS = frozenset({"restricted", "one-lane", "single lane", "alternate",
                                 "delay", "caution", "advisory", "damage"})
_CLEAR_KEYWORDS    = frozenset({"cleared", "reopened", "open", "passable", "normal traffic",
                                 "restored"})


def _parse_status_from_html(html: str) -> tuple[str, str, Optional[str]]:
    """
    Extract road status from raw HTML using keyword matching.

    Returns
    -------
    tuple[str, str, str | None]
        (status, severity, reason)
        status   : 'open' | 'closed' | 'restricted'
        severity : 'none' | 'minor' | 'major' | 'critical'
        reason   : short human-readable string or None
    """
    text = html.lower()
    # Strip HTML tags for cleaner matching
    text = re.sub(r"<[^>]+>", " ", text)

    if any(kw in text for kw in _CRITICAL_KEYWORDS):
        return "closed", "critical", "Road impassable — emergency closure"
    if "landslide" in text or "rockfall" in text:
        return "closed", "major", "Landslide / rockfall reported"
    if "flood" in text or "washed" in text:
        return "closed", "major", "Flooding / washout reported"
    if any(kw in text for kw in _CLOSURE_KEYWORDS):
        return "closed", "major", "Blockage reported — check locally"
    if any(kw in text for kw in _RESTRICT_KEYWORDS):
        return "restricted", "minor", "Restrictions in effect — reduced speed or one-lane"
    if any(kw in text for kw in _CLEAR_KEYWORDS):
        return "open", "none", None
    # Ambiguous: default to restricted with a caution note
    return "restricted", "minor", "Status unconfirmed — verify locally before travel"


# ── Bright Data scraper ───────────────────────────────────────────────────────

def _build_search_url(road_name: str, country: str) -> str:
    """
    Build a Google News search URL for the road name.
    Bright Data Web Unlocker bypasses bot-detection to retrieve these results.
    """
    query = f"{road_name} road closure status {country}"
    return f"https://www.google.com/search?{urlencode({'q': query, 'tbm': 'nws'})}"


async def _scrape_via_brightdata(url: str) -> Optional[str]:
    """
    Fetch a URL via the Bright Data Web Unlocker API.

    Uses the REST API (POST https://api.brightdata.com/request) rather than
    a proxy, so no SSL interception or proxy config is needed.
    Returns raw HTML string on success, None on any failure.
    """
    api_key = settings.brightdata_api_key
    if not api_key:
        return None  # No credentials → skip immediately

    try:
        async with httpx.AsyncClient(timeout=settings.brightdata_timeout_s) as client:
            resp = await client.post(
                "https://api.brightdata.com/request",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                json={
                    "zone": settings.brightdata_zone,
                    "url": url,
                    "format": "raw",
                },
            )
            resp.raise_for_status()
            return resp.text
    except Exception:
        return None


# ── Three-tier circuit breaker functions ──────────────────────────────────────

async def _fetch_live(region: str) -> Optional[list[dict]]:
    """
    Tier 1: Scrape road sources via Bright Data.
    Returns parsed bulletin list on success, None on any failure.
    On success, results are written to the SQLite edge cache.
    """
    config_path = settings.regions_dir / f"{region}.json"
    if not config_path.exists():
        return None

    with open(config_path, encoding="utf-8") as fh:
        config = json.load(fh)

    road_sources: list[dict] = config.get("road_sources", [])
    if not road_sources:
        return None

    results: list[dict] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for source in road_sources:
        name = source["name"]
        country = source["country"]
        url = _build_search_url(name, country)
        html = await _scrape_via_brightdata(url)

        if html is None:
            return None  # Any single failure aborts live fetch entirely

        status, severity, reason = _parse_status_from_html(html)
        results.append({
            "source_name": name,
            "country": country,
            "status": status,
            "reason": reason,
            "severity": severity,
            "last_updated": now_iso,
        })

    # Persist to SQLite cache on success
    try:
        await upsert_bulletins(results, region=region)
    except Exception:
        pass  # Cache write failure must not abort the live response

    return results


async def _fetch_from_cache(region: str) -> Optional[list[dict]]:
    """
    Tier 2: Read from SQLite edge cache (max age 6 h).
    Returns cached rows or None if cache is empty / stale.
    """
    try:
        rows = await get_cached_bulletins(region=region, max_age_hours=6.0)
        return rows if rows else None
    except Exception:
        return None


def _fetch_from_fixture(region: str) -> list[dict]:
    """
    Tier 3: Load bundled JSON fixture files.
    Always succeeds — these files are baked into the application.
    Falls back to empty list only if the region has no known countries
    (e.g., andes / east_africa blueprints have no road fixtures yet).
    """
    # Determine which fixture files apply to this region
    _REGION_FIXTURE_MAP: dict[str, list[str]] = {
        "himalaya": ["bhutan_roads.json", "nepal_roads.json"],
        "andes": [],
        "east_africa": [],
    }
    fixture_files = _REGION_FIXTURE_MAP.get(region, [])
    records: list[dict] = []

    for filename in fixture_files:
        fixture_path: Path = settings.fixtures_dir / filename
        if fixture_path.exists():
            with open(fixture_path, encoding="utf-8") as fh:
                records.extend(json.load(fh))

    return records


def _build_advisory(roads: list[dict]) -> Optional[str]:
    """
    Generate a concise advisory string from the bulletin summary.
    Used by the frontend to display a single-line farmer alert.
    """
    closed = [r["source_name"] for r in roads if r["status"] == "closed"]
    restricted = [r["source_name"] for r in roads if r["status"] == "restricted"]

    if closed:
        return f"CLOSED: {', '.join(closed)}. Do not travel on these routes."
    if restricted:
        return f"CAUTION: {', '.join(restricted)} have restrictions. Allow extra time."
    return "All monitored routes are currently open."


# ── Router endpoint ───────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=RoadBulletinResponse,
    summary="Get road pass closure bulletin",
    description=(
        "Returns real-time road-pass status for mountain passes in the selected region. "
        "Uses a three-tier circuit breaker: Bright Data live scrape → SQLite cache → "
        "offline JSON fixtures. Always returns data even with zero connectivity."
    ),
)
async def get_road_bulletin(
    region: str = Query(default="himalaya", description="Region key: himalaya / andes / east_africa"),
    country: Optional[str] = Query(default=None, description="Optional country filter (e.g. 'Bhutan')"),
) -> RoadBulletinResponse:
    """
    Road bulletin with three-tier circuit breaker fallback.
    Response always includes `data_source` so the frontend can show a freshness badge.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    data_source: Literal["live", "cache", "fixture"] = "fixture"

    # ── Tier 1: Live Bright Data ──────────────────────────────────────────────
    roads = await _fetch_live(region)
    if roads is not None:
        data_source = "live"
    else:
        # ── Tier 2: SQLite cache ──────────────────────────────────────────────
        roads = await _fetch_from_cache(region)
        if roads is not None:
            data_source = "cache"
        else:
            # ── Tier 3: Fixture files ─────────────────────────────────────────
            roads = _fetch_from_fixture(region)
            data_source = "fixture"

    # Apply optional country filter
    if country:
        roads = [r for r in roads if r.get("country", "").lower() == country.lower()]

    # Normalise to RoadStatusItem shape (fixture records may have extra fields)
    road_items = [
        RoadStatusItem(
            source_name=r["source_name"],
            country=r["country"],
            status=r["status"],
            reason=r.get("reason"),
            severity=r.get("severity", "none"),
            last_updated=r.get("last_updated", now_iso),
        )
        for r in roads
    ]

    return RoadBulletinResponse(
        region=region,
        roads=road_items,
        data_source=data_source,
        fetched_at=now_iso,
        advisory=_build_advisory(roads),
    )
