"""
Shared pytest fixtures for BioTerrace Sentinel test suite.

Phase 2 : region config loaders, reusable SlopeInput dicts.
Phase 3 : FastAPI TestClient, Ollama mock fixtures.
Phase 4 : Bright Data / SQLite mock fixtures added.
Phase 5+: ElevenLabs mocks added when voice router is implemented.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.config.settings import settings


# ── FastAPI TestClient ────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client() -> TestClient:
    """
    A synchronous ASGI test client for the full FastAPI app.
    All external I/O (Ollama, Bright Data, ElevenLabs) must be mocked
    in individual test functions using monkeypatch or unittest.mock.patch.
    """
    from main import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ── Ollama mock helpers ───────────────────────────────────────────────────────

@pytest.fixture
def mock_ollama_success(monkeypatch):
    """
    Patches translate_to_vernacular to return a canned Hindi sentence.
    Use this fixture in tests that assert vernacular_script is populated.
    """
    mock = AsyncMock(return_value="ढलान खतरनाक है। अभी वेटीवर घास लगाएं।")
    monkeypatch.setattr("app.routers.audit.translate_to_vernacular", mock)
    return mock


@pytest.fixture
def mock_ollama_offline(monkeypatch):
    """
    Patches translate_to_vernacular to return None (Ollama not running).
    Use this fixture in tests that verify graceful offline degradation.
    """
    mock = AsyncMock(return_value=None)
    monkeypatch.setattr("app.routers.audit.translate_to_vernacular", mock)
    return mock


# ── Bright Data / road bulletin mock helpers ─────────────────────────────────

@pytest.fixture
def mock_brightdata_live(monkeypatch):
    """
    Patches _scrape_via_brightdata to return fake HTML (live path simulation).
    Also patches upsert_bulletins to a no-op to prevent SQLite writes during tests.
    First source returns 'landslide' HTML (→ closed); all others return 'open'.
    """
    call_count = {"n": 0}

    async def mock_scrape(url: str) -> str:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return "<html>Dochula pass landslide reported road blocked closed</html>"
        return "<html>Road cleared normal traffic open passable</html>"

    async def mock_upsert(*args, **kwargs) -> None:
        pass  # Suppress SQLite writes so tests don't create road_cache.db

    monkeypatch.setattr("app.routers.road_bulletin._scrape_via_brightdata", mock_scrape)
    monkeypatch.setattr("app.routers.road_bulletin.upsert_bulletins", mock_upsert)
    return call_count


@pytest.fixture
def mock_brightdata_timeout(monkeypatch):
    """Patches _scrape_via_brightdata to always return None (timeout/offline)."""
    async def mock_scrape(url: str):
        return None

    monkeypatch.setattr("app.routers.road_bulletin._scrape_via_brightdata", mock_scrape)


@pytest.fixture
def mock_cache_hit(monkeypatch):
    """Patches _fetch_from_cache to return a canned cache record."""
    async def mock_cache(region: str):
        return [
            {
                "source_name": "Dochula Pass",
                "country": "Bhutan",
                "status": "restricted",
                "reason": "Cached: surface damage",
                "severity": "minor",
                "last_updated": "2025-10-03T04:00:00Z",
                "fetched_at": "2025-10-03T05:00:00Z",
            }
        ]

    monkeypatch.setattr("app.routers.road_bulletin._fetch_from_cache", mock_cache)


@pytest.fixture
def mock_cache_miss(monkeypatch):
    """Patches _fetch_from_cache to return None (empty / stale cache)."""
    async def mock_cache(region: str):
        return None

    monkeypatch.setattr("app.routers.road_bulletin._fetch_from_cache", mock_cache)


# ── Voice / ElevenLabs mock helpers ──────────────────────────────────────────

# Minimal valid MP3 header bytes (ID3v2 tag + MPEG frame sync) for test assertions
FAKE_MP3_BYTES = b"ID3" + b"\x00" * 7 + b"\xff\xfb\x90\x00" + b"\x00" * 89


@pytest.fixture
def audio_cache(tmp_path, monkeypatch):
    """
    Redirects the audio cache to a temp directory for the duration of the test.
    Creates both audio_cache/ and audio_cache/templates/ subdirectories.
    """
    cache_dir = tmp_path / "audio_cache"
    cache_dir.mkdir()
    (cache_dir / "templates").mkdir()
    monkeypatch.setattr(settings, "audio_cache_dir", cache_dir)
    return cache_dir


@pytest.fixture
def audio_cache_with_template(audio_cache):
    """
    Extends audio_cache by pre-writing a fake himalaya_critical.mp3 template file.
    Use this to test the template fallback tier in the voice router.
    """
    template_file = audio_cache / "templates" / "himalaya_critical.mp3"
    template_file.write_bytes(FAKE_MP3_BYTES)
    return audio_cache


@pytest.fixture
def mock_elevenlabs_success(monkeypatch):
    """
    Patches _call_elevenlabs to return FAKE_MP3_BYTES without any API call.
    Use to test the ElevenLabs synthesis path and cache-write logic.
    """
    async def mock_call(script: str) -> bytes:
        return FAKE_MP3_BYTES

    monkeypatch.setattr("app.routers.voice._call_elevenlabs", mock_call)
    return FAKE_MP3_BYTES


@pytest.fixture
def mock_elevenlabs_offline(monkeypatch):
    """
    Patches _call_elevenlabs to return None (ElevenLabs unavailable / no creds).
    Use to test template and text-only fallback paths.
    """
    async def mock_call(script: str):
        return None

    monkeypatch.setattr("app.routers.voice._call_elevenlabs", mock_call)


# ── Region config fixtures ────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def regions_dir() -> Path:
    return settings.regions_dir


@pytest.fixture(scope="session")
def himalaya_config(regions_dir: Path) -> dict:
    with open(regions_dir / "himalaya.json", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="session")
def andes_config(regions_dir: Path) -> dict:
    with open(regions_dir / "andes.json", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="session")
def east_africa_config(regions_dir: Path) -> dict:
    with open(regions_dir / "east_africa.json", encoding="utf-8") as fh:
        return json.load(fh)


# ── Canonical SlopeInput keyword-arg dicts (reused across tests) ──────────────

@pytest.fixture
def slope_dry_critical() -> dict:
    """Cohesionless dry slope at theta = phi = 30°. Expected FoS ≈ 1.000."""
    return dict(theta_deg=30.0, z=1.0, phi_deg=30.0, c_prime=0.0,
                gamma=18.0, gamma_w=9.81, h_w=0.0, c_r=0.0)


@pytest.fixture
def slope_saturated() -> dict:
    """Fully saturated cohesionless slope at theta = phi = 30°. Expected FoS < 1.0."""
    return dict(theta_deg=30.0, z=1.0, phi_deg=30.0, c_prime=0.0,
                gamma=18.0, gamma_w=9.81, h_w=1.0, c_r=0.0)
