"""
Layer 2 Integration Tests — GET /road-bulletin Endpoint
========================================================

Tests the three-tier circuit breaker, response schema, advisory text,
and country filtering. All external I/O (Bright Data proxy, SQLite) is
mocked at the function boundary via conftest fixtures.

Test groups
-----------
  Group A  Response schema — all required fields present and typed correctly
  Group B  Circuit breaker — live → cache → fixture fallback in correct order
  Group C  Fixture tier — Himalaya fixtures load correct Bhutan/Nepal data
  Group D  Advisory text — generated from road status correctly
  Group E  Country filter — `?country=Bhutan` returns only Bhutan roads
  Group F  Data source label — response reflects actual data tier used
  Group G  Parser — HTML keyword extraction produces correct status
"""

import pytest

from app.routers.road_bulletin import _parse_status_from_html, _build_advisory


# ── Group A: Response schema ──────────────────────────────────────────────────

class TestResponseSchema:

    def test_returns_200(self, client, mock_cache_miss, mock_brightdata_timeout):
        resp = client.get("/road-bulletin/")
        assert resp.status_code == 200

    def test_response_has_region(self, client, mock_cache_miss, mock_brightdata_timeout):
        resp = client.get("/road-bulletin/")
        assert "region" in resp.json()

    def test_response_has_roads_list(self, client, mock_cache_miss, mock_brightdata_timeout):
        resp = client.get("/road-bulletin/")
        assert "roads" in resp.json()
        assert isinstance(resp.json()["roads"], list)

    def test_response_has_data_source(self, client, mock_cache_miss, mock_brightdata_timeout):
        resp = client.get("/road-bulletin/")
        assert resp.json()["data_source"] in ("live", "cache", "fixture")

    def test_response_has_fetched_at(self, client, mock_cache_miss, mock_brightdata_timeout):
        resp = client.get("/road-bulletin/")
        assert "fetched_at" in resp.json()
        assert len(resp.json()["fetched_at"]) > 0

    def test_road_item_has_required_fields(self, client, mock_cache_miss, mock_brightdata_timeout):
        resp = client.get("/road-bulletin/")
        roads = resp.json()["roads"]
        assert len(roads) > 0, "Himalaya fixture must return at least one road"
        road = roads[0]
        assert "source_name" in road
        assert "country" in road
        assert "status" in road
        assert "severity" in road
        assert "last_updated" in road

    def test_road_status_is_valid_enum(self, client, mock_cache_miss, mock_brightdata_timeout):
        roads = client.get("/road-bulletin/").json()["roads"]
        for road in roads:
            assert road["status"] in ("open", "closed", "restricted")

    def test_road_severity_is_valid_enum(self, client, mock_cache_miss, mock_brightdata_timeout):
        roads = client.get("/road-bulletin/").json()["roads"]
        for road in roads:
            assert road["severity"] in ("none", "minor", "major", "critical")

    def test_default_region_is_himalaya(self, client, mock_cache_miss, mock_brightdata_timeout):
        resp = client.get("/road-bulletin/")
        assert resp.json()["region"] == "himalaya"

    def test_explicit_region_param(self, client, mock_cache_miss, mock_brightdata_timeout):
        resp = client.get("/road-bulletin/?region=himalaya")
        assert resp.json()["region"] == "himalaya"


# ── Group B: Circuit breaker ordering ────────────────────────────────────────

class TestCircuitBreaker:

    def test_live_tier_returns_live_data_source(self, client, mock_brightdata_live):
        """When Bright Data succeeds, data_source must be 'live'."""
        resp = client.get("/road-bulletin/")
        assert resp.json()["data_source"] == "live"

    def test_timeout_falls_back_to_cache(self, client, mock_brightdata_timeout, mock_cache_hit):
        """Bright Data timeout + cache hit → data_source must be 'cache'."""
        resp = client.get("/road-bulletin/")
        assert resp.json()["data_source"] == "cache"

    def test_timeout_cache_miss_falls_back_to_fixture(
        self, client, mock_brightdata_timeout, mock_cache_miss
    ):
        """Bright Data timeout + empty cache → data_source must be 'fixture'."""
        resp = client.get("/road-bulletin/")
        assert resp.json()["data_source"] == "fixture"

    def test_fixture_tier_still_returns_200(
        self, client, mock_brightdata_timeout, mock_cache_miss
    ):
        """Fixture tier must always respond 200 — core offline guarantee."""
        resp = client.get("/road-bulletin/")
        assert resp.status_code == 200

    def test_cache_hit_does_not_call_fixture(
        self, client, mock_brightdata_timeout, mock_cache_hit, monkeypatch
    ):
        """When cache returns data, the fixture file must not be read."""
        fixture_calls = {"n": 0}

        def mock_fixture(region):
            fixture_calls["n"] += 1
            return []

        monkeypatch.setattr("app.routers.road_bulletin._fetch_from_fixture", mock_fixture)
        client.get("/road-bulletin/")
        assert fixture_calls["n"] == 0, "Fixture must not be read when cache has data."


# ── Group C: Fixture data content ─────────────────────────────────────────────

class TestFixtureContent:

    def test_himalaya_fixture_has_bhutan_roads(
        self, client, mock_brightdata_timeout, mock_cache_miss
    ):
        roads = client.get("/road-bulletin/").json()["roads"]
        countries = [r["country"] for r in roads]
        assert "Bhutan" in countries

    def test_himalaya_fixture_has_nepal_roads(
        self, client, mock_brightdata_timeout, mock_cache_miss
    ):
        roads = client.get("/road-bulletin/").json()["roads"]
        countries = [r["country"] for r in roads]
        assert "Nepal" in countries

    def test_himalaya_fixture_has_dochula_pass(
        self, client, mock_brightdata_timeout, mock_cache_miss
    ):
        roads = client.get("/road-bulletin/").json()["roads"]
        names = [r["source_name"] for r in roads]
        assert "Dochula Pass" in names

    def test_himalaya_fixture_has_prithvi_highway(
        self, client, mock_brightdata_timeout, mock_cache_miss
    ):
        roads = client.get("/road-bulletin/").json()["roads"]
        names = [r["source_name"] for r in roads]
        assert "Prithvi Highway" in names

    def test_himalaya_fixture_has_four_roads(
        self, client, mock_brightdata_timeout, mock_cache_miss
    ):
        """Fixture should have 2 Bhutan + 2 Nepal = 4 roads total."""
        roads = client.get("/road-bulletin/").json()["roads"]
        assert len(roads) == 4


# ── Group D: Advisory text ────────────────────────────────────────────────────

class TestAdvisoryText:

    def test_advisory_present_in_response(
        self, client, mock_brightdata_timeout, mock_cache_miss
    ):
        resp = client.get("/road-bulletin/")
        assert "advisory" in resp.json()
        assert resp.json()["advisory"] is not None

    def test_advisory_all_open_message(self):
        roads = [
            {"source_name": "Pass A", "status": "open"},
            {"source_name": "Pass B", "status": "open"},
        ]
        advisory = _build_advisory(roads)
        assert "open" in advisory.lower()

    def test_advisory_closed_road_mentions_name(self):
        roads = [{"source_name": "Dochula Pass", "status": "closed"}]
        advisory = _build_advisory(roads)
        assert "Dochula Pass" in advisory
        assert "CLOSED" in advisory

    def test_advisory_restricted_road_mentions_caution(self):
        roads = [
            {"source_name": "Prithvi Highway", "status": "restricted"},
            {"source_name": "Karnali Highway", "status": "open"},
        ]
        advisory = _build_advisory(roads)
        assert "CAUTION" in advisory
        assert "Prithvi Highway" in advisory

    def test_advisory_closed_takes_priority_over_restricted(self):
        roads = [
            {"source_name": "Pass A", "status": "restricted"},
            {"source_name": "Pass B", "status": "closed"},
        ]
        advisory = _build_advisory(roads)
        assert "CLOSED" in advisory  # Closed should dominate the message


# ── Group E: Country filter ────────────────────────────────────────────────────

class TestCountryFilter:

    def test_bhutan_filter_returns_only_bhutan_roads(
        self, client, mock_brightdata_timeout, mock_cache_miss
    ):
        roads = client.get("/road-bulletin/?country=Bhutan").json()["roads"]
        for road in roads:
            assert road["country"] == "Bhutan"

    def test_nepal_filter_returns_only_nepal_roads(
        self, client, mock_brightdata_timeout, mock_cache_miss
    ):
        roads = client.get("/road-bulletin/?country=Nepal").json()["roads"]
        for road in roads:
            assert road["country"] == "Nepal"

    def test_bhutan_filter_returns_two_roads(
        self, client, mock_brightdata_timeout, mock_cache_miss
    ):
        roads = client.get("/road-bulletin/?country=Bhutan").json()["roads"]
        assert len(roads) == 2

    def test_unknown_country_returns_empty_list(
        self, client, mock_brightdata_timeout, mock_cache_miss
    ):
        roads = client.get("/road-bulletin/?country=Mars").json()["roads"]
        assert roads == []


# ── Group F: Data source label ─────────────────────────────────────────────────

class TestDataSourceLabel:

    def test_live_label_when_brightdata_succeeds(self, client, mock_brightdata_live):
        assert client.get("/road-bulletin/").json()["data_source"] == "live"

    def test_cache_label_when_cache_has_data(
        self, client, mock_brightdata_timeout, mock_cache_hit
    ):
        assert client.get("/road-bulletin/").json()["data_source"] == "cache"

    def test_fixture_label_when_all_tiers_fail(
        self, client, mock_brightdata_timeout, mock_cache_miss
    ):
        assert client.get("/road-bulletin/").json()["data_source"] == "fixture"


# ── Group G: HTML keyword parser (pure unit) ───────────────────────────────────

class TestHtmlParser:

    def test_landslide_keyword_gives_closed_major(self):
        html = "<html>Dochula pass landslide road blocked</html>"
        status, severity, reason = _parse_status_from_html(html)
        assert status == "closed"
        assert severity == "major"
        assert reason is not None

    def test_flood_keyword_gives_closed_major(self):
        html = "<p>Highway closed due to flooding and road washed out</p>"
        status, severity, reason = _parse_status_from_html(html)
        assert status == "closed"
        assert severity == "major"

    def test_collapse_keyword_gives_critical(self):
        html = "<p>Road collapse — bridge collapsed impassable emergency</p>"
        status, severity, reason = _parse_status_from_html(html)
        assert status == "closed"
        assert severity == "critical"

    def test_restricted_keyword_gives_restricted_minor(self):
        html = "<p>Road restricted to one-lane alternate routing advised</p>"
        status, severity, reason = _parse_status_from_html(html)
        assert status == "restricted"
        assert severity == "minor"

    def test_open_keyword_gives_open_none(self):
        html = "<p>Road cleared normal traffic open passable</p>"
        status, severity, reason = _parse_status_from_html(html)
        assert status == "open"
        assert severity == "none"
        assert reason is None

    def test_ambiguous_html_gives_restricted_minor(self):
        """No recognisable keywords → default to restricted/unconfirmed."""
        html = "<html>Weather report: partly cloudy</html>"
        status, severity, _ = _parse_status_from_html(html)
        assert status == "restricted"
        assert severity == "minor"

    def test_html_tags_stripped_before_matching(self):
        """HTML tags must not interfere with keyword matching."""
        html = "<p class='alert'>Road is <strong>open</strong> and clear</p>"
        status, severity, reason = _parse_status_from_html(html)
        assert status == "open"
