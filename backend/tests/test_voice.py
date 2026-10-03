"""
Layer 2 Integration Tests — POST /voice/synthesize + GET /voice/audio/*
========================================================================

Tests the three-tier voice synthesis pipeline:
  Tier 0  Local cache hit (no API call)
  Tier 1  ElevenLabs live synthesis (mocked)
  Tier 2  Pre-cached regional template fallback
  Tier 3  Text-only fallback (no audio available)

All ElevenLabs API calls are mocked via conftest fixtures.
Audio cache uses a temp directory via the `audio_cache` conftest fixture.

Test groups
-----------
  Group A  Request validation — schema enforcement
  Group B  Cache hit — returns cached audio without calling ElevenLabs
  Group C  ElevenLabs path — synthesis, cache write, response fields
  Group D  Template fallback — offline tier 2
  Group E  Text-only fallback — offline tier 3 (no template)
  Group F  GET /voice/audio/{cache_key} — retrieval endpoint
  Group G  GET /voice/audio/template/{region}/{risk_level}
  Group H  Cache key determinism — same script → same key
"""

import pytest

from tests.conftest import FAKE_MP3_BYTES
from app.routers.voice import _cache_key


# ── Shared payload ────────────────────────────────────────────────────────────

HINDI_ADVISORY = "ढलान खतरनाक है। तुरन्त वेटीवर घास लगाएं।"   # 42 chars
NEPALI_ADVISORY = "भिरालो ठाउँमा बाँस लगाउनुस् र पानी निकाल्नुस्।"   # 47 chars
MAX_SCRIPT = "A" * 140   # exactly at the 140-char limit


# ── Group A: Request validation ───────────────────────────────────────────────

class TestRequestValidation:

    def test_empty_script_returns_422(self, client, audio_cache, mock_elevenlabs_offline):
        resp = client.post("/voice/synthesize", json={"script": ""})
        assert resp.status_code == 422

    def test_script_over_140_chars_returns_422(self, client, audio_cache, mock_elevenlabs_offline):
        resp = client.post("/voice/synthesize", json={"script": "A" * 141})
        assert resp.status_code == 422

    def test_exactly_140_chars_is_accepted(self, client, audio_cache, mock_elevenlabs_offline):
        resp = client.post("/voice/synthesize", json={"script": MAX_SCRIPT})
        assert resp.status_code == 200

    def test_missing_script_returns_422(self, client, audio_cache, mock_elevenlabs_offline):
        resp = client.post("/voice/synthesize", json={"region": "himalaya"})
        assert resp.status_code == 422

    def test_default_region_is_himalaya(self, client, audio_cache, mock_elevenlabs_offline):
        resp = client.post("/voice/synthesize", json={"script": HINDI_ADVISORY})
        # Regardless of audio availability, the response must be 200
        assert resp.status_code == 200

    def test_valid_risk_levels_accepted(self, client, audio_cache, mock_elevenlabs_offline):
        for level in ["STABLE", "MARGINAL", "CRITICAL", "stable", "marginal", "critical"]:
            resp = client.post("/voice/synthesize",
                               json={"script": HINDI_ADVISORY, "risk_level": level})
            assert resp.status_code == 200


# ── Group B: Cache hit ────────────────────────────────────────────────────────

class TestCacheHit:

    def test_cache_hit_returns_200(self, client, audio_cache):
        """Pre-write audio to cache; synthesize endpoint must return 200 cache hit."""
        key = _cache_key(HINDI_ADVISORY)
        (audio_cache / f"{key}.mp3").write_bytes(FAKE_MP3_BYTES)

        resp = client.post("/voice/synthesize",
                           json={"script": HINDI_ADVISORY, "region": "himalaya"})
        assert resp.status_code == 200

    def test_cache_hit_source_is_cache(self, client, audio_cache):
        key = _cache_key(HINDI_ADVISORY)
        (audio_cache / f"{key}.mp3").write_bytes(FAKE_MP3_BYTES)

        data = client.post("/voice/synthesize",
                           json={"script": HINDI_ADVISORY}).json()
        assert data["source"] == "cache"

    def test_cache_hit_audio_available_true(self, client, audio_cache):
        key = _cache_key(HINDI_ADVISORY)
        (audio_cache / f"{key}.mp3").write_bytes(FAKE_MP3_BYTES)

        data = client.post("/voice/synthesize",
                           json={"script": HINDI_ADVISORY}).json()
        assert data["audio_available"] is True

    def test_cache_hit_does_not_call_elevenlabs(self, client, audio_cache, monkeypatch):
        """Cache hit must not trigger an ElevenLabs API call."""
        call_count = {"n": 0}

        async def counting_mock(script):
            call_count["n"] += 1
            return FAKE_MP3_BYTES

        monkeypatch.setattr("app.routers.voice._call_elevenlabs", counting_mock)

        key = _cache_key(HINDI_ADVISORY)
        (audio_cache / f"{key}.mp3").write_bytes(FAKE_MP3_BYTES)

        client.post("/voice/synthesize", json={"script": HINDI_ADVISORY})
        assert call_count["n"] == 0, "ElevenLabs must not be called on a cache hit."

    def test_cache_hit_audio_endpoint_correct(self, client, audio_cache):
        key = _cache_key(HINDI_ADVISORY)
        (audio_cache / f"{key}.mp3").write_bytes(FAKE_MP3_BYTES)

        data = client.post("/voice/synthesize",
                           json={"script": HINDI_ADVISORY}).json()
        assert data["audio_endpoint"] == f"/voice/audio/{key}"


# ── Group C: ElevenLabs path ──────────────────────────────────────────────────

class TestElevenLabsPath:

    def test_elevenlabs_success_returns_200(
        self, client, audio_cache, mock_elevenlabs_success
    ):
        resp = client.post("/voice/synthesize", json={"script": HINDI_ADVISORY})
        assert resp.status_code == 200

    def test_elevenlabs_success_source_is_elevenlabs(
        self, client, audio_cache, mock_elevenlabs_success
    ):
        data = client.post("/voice/synthesize",
                           json={"script": HINDI_ADVISORY}).json()
        assert data["source"] == "elevenlabs"

    def test_elevenlabs_success_audio_available_true(
        self, client, audio_cache, mock_elevenlabs_success
    ):
        data = client.post("/voice/synthesize",
                           json={"script": HINDI_ADVISORY}).json()
        assert data["audio_available"] is True

    def test_elevenlabs_success_writes_audio_to_cache(
        self, client, audio_cache, mock_elevenlabs_success
    ):
        """After synthesis, the MP3 must exist on disk in the cache directory."""
        client.post("/voice/synthesize", json={"script": HINDI_ADVISORY})
        key = _cache_key(HINDI_ADVISORY)
        cached_file = audio_cache / f"{key}.mp3"
        assert cached_file.exists(), f"Expected {cached_file} to exist after synthesis."

    def test_elevenlabs_cached_bytes_match_api_response(
        self, client, audio_cache, mock_elevenlabs_success
    ):
        """Bytes written to cache must exactly match what the API returned."""
        client.post("/voice/synthesize", json={"script": HINDI_ADVISORY})
        key = _cache_key(HINDI_ADVISORY)
        assert (audio_cache / f"{key}.mp3").read_bytes() == FAKE_MP3_BYTES

    def test_second_request_hits_cache_not_elevenlabs(
        self, client, audio_cache, monkeypatch
    ):
        """Second identical request must be a cache hit, not another ElevenLabs call."""
        call_count = {"n": 0}

        async def counting_mock(script):
            call_count["n"] += 1
            return FAKE_MP3_BYTES

        monkeypatch.setattr("app.routers.voice._call_elevenlabs", counting_mock)

        client.post("/voice/synthesize", json={"script": NEPALI_ADVISORY})
        client.post("/voice/synthesize", json={"script": NEPALI_ADVISORY})
        assert call_count["n"] == 1, "ElevenLabs must be called only once for repeated scripts."

    def test_elevenlabs_returns_correct_cache_key(
        self, client, audio_cache, mock_elevenlabs_success
    ):
        data = client.post("/voice/synthesize",
                           json={"script": HINDI_ADVISORY}).json()
        expected_key = _cache_key(HINDI_ADVISORY)
        assert data["cache_key"] == expected_key


# ── Group D: Template fallback ────────────────────────────────────────────────

class TestTemplateFallback:

    def test_template_source_when_offline_and_template_exists(
        self, client, audio_cache_with_template, mock_elevenlabs_offline
    ):
        data = client.post(
            "/voice/synthesize",
            json={"script": HINDI_ADVISORY, "region": "himalaya", "risk_level": "CRITICAL"},
        ).json()
        assert data["source"] == "template"

    def test_template_audio_available_true(
        self, client, audio_cache_with_template, mock_elevenlabs_offline
    ):
        data = client.post(
            "/voice/synthesize",
            json={"script": HINDI_ADVISORY, "region": "himalaya", "risk_level": "CRITICAL"},
        ).json()
        assert data["audio_available"] is True

    def test_template_audio_endpoint_points_to_template_route(
        self, client, audio_cache_with_template, mock_elevenlabs_offline
    ):
        data = client.post(
            "/voice/synthesize",
            json={"script": HINDI_ADVISORY, "region": "himalaya", "risk_level": "CRITICAL"},
        ).json()
        assert "/voice/audio/template/himalaya/critical" in data["audio_endpoint"]

    def test_no_template_for_marginal_falls_to_text_only(
        self, client, audio_cache_with_template, mock_elevenlabs_offline
    ):
        """
        audio_cache_with_template only creates himalaya_critical.mp3.
        Requesting MARGINAL should fall through to text_only.
        """
        data = client.post(
            "/voice/synthesize",
            json={"script": HINDI_ADVISORY, "region": "himalaya", "risk_level": "MARGINAL"},
        ).json()
        assert data["source"] == "text_only"


# ── Group E: Text-only fallback ───────────────────────────────────────────────

class TestTextOnlyFallback:

    def test_text_only_returns_200(
        self, client, audio_cache, mock_elevenlabs_offline
    ):
        resp = client.post("/voice/synthesize", json={"script": HINDI_ADVISORY})
        assert resp.status_code == 200

    def test_text_only_source_is_text_only(
        self, client, audio_cache, mock_elevenlabs_offline
    ):
        data = client.post("/voice/synthesize",
                           json={"script": HINDI_ADVISORY}).json()
        assert data["source"] == "text_only"

    def test_text_only_audio_available_false(
        self, client, audio_cache, mock_elevenlabs_offline
    ):
        data = client.post("/voice/synthesize",
                           json={"script": HINDI_ADVISORY}).json()
        assert data["audio_available"] is False

    def test_text_only_audio_endpoint_is_null(
        self, client, audio_cache, mock_elevenlabs_offline
    ):
        data = client.post("/voice/synthesize",
                           json={"script": HINDI_ADVISORY}).json()
        assert data["audio_endpoint"] is None

    def test_text_only_preserves_original_script(
        self, client, audio_cache, mock_elevenlabs_offline
    ):
        data = client.post("/voice/synthesize",
                           json={"script": HINDI_ADVISORY}).json()
        assert data["script"] == HINDI_ADVISORY


# ── Group F: GET /voice/audio/{cache_key} ─────────────────────────────────────

class TestGetCachedAudio:

    def test_get_existing_audio_returns_200(self, client, audio_cache):
        key = _cache_key(HINDI_ADVISORY)
        (audio_cache / f"{key}.mp3").write_bytes(FAKE_MP3_BYTES)

        resp = client.get(f"/voice/audio/{key}")
        assert resp.status_code == 200

    def test_get_existing_audio_content_type_is_mpeg(self, client, audio_cache):
        key = _cache_key(HINDI_ADVISORY)
        (audio_cache / f"{key}.mp3").write_bytes(FAKE_MP3_BYTES)

        resp = client.get(f"/voice/audio/{key}")
        assert "audio" in resp.headers.get("content-type", "")

    def test_get_missing_audio_returns_404(self, client, audio_cache):
        resp = client.get("/voice/audio/nonexistentkey1234")
        assert resp.status_code == 404

    def test_get_audio_bytes_match_written_bytes(self, client, audio_cache):
        key = _cache_key(NEPALI_ADVISORY)
        (audio_cache / f"{key}.mp3").write_bytes(FAKE_MP3_BYTES)

        resp = client.get(f"/voice/audio/{key}")
        assert resp.content == FAKE_MP3_BYTES


# ── Group G: GET /voice/audio/template/{region}/{risk_level} ─────────────────

class TestGetTemplateAudio:

    def test_existing_template_returns_200(self, client, audio_cache_with_template):
        resp = client.get("/voice/audio/template/himalaya/critical")
        assert resp.status_code == 200

    def test_existing_template_content_type_is_mpeg(self, client, audio_cache_with_template):
        resp = client.get("/voice/audio/template/himalaya/critical")
        assert "audio" in resp.headers.get("content-type", "")

    def test_missing_template_returns_404(self, client, audio_cache):
        resp = client.get("/voice/audio/template/himalaya/stable")
        assert resp.status_code == 404

    def test_template_bytes_match_written_bytes(self, client, audio_cache_with_template):
        resp = client.get("/voice/audio/template/himalaya/critical")
        assert resp.content == FAKE_MP3_BYTES


# ── Group H: Cache key determinism ───────────────────────────────────────────

class TestCacheKeyDeterminism:

    def test_same_script_produces_same_key(self):
        assert _cache_key(HINDI_ADVISORY) == _cache_key(HINDI_ADVISORY)

    def test_different_scripts_produce_different_keys(self):
        assert _cache_key(HINDI_ADVISORY) != _cache_key(NEPALI_ADVISORY)

    def test_cache_key_is_16_chars(self):
        assert len(_cache_key(HINDI_ADVISORY)) == 16

    def test_cache_key_is_hex_string(self):
        key = _cache_key(HINDI_ADVISORY)
        assert all(c in "0123456789abcdef" for c in key)

    def test_whitespace_difference_produces_different_key(self):
        assert _cache_key("test script") != _cache_key("test  script")
