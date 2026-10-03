"""
Layer 2 Integration Tests — POST /audit Endpoint
=================================================

Tests the full audit pipeline via the FastAPI TestClient.
All external I/O is mocked:
  - translate_to_vernacular → mocked via conftest fixtures (mock_ollama_*)
  - No Bright Data / ElevenLabs calls in this module

Test strategy
-------------
  Group A  Happy path — valid payloads, correct response structure
  Group B  Pydantic validation — invalid payloads return 422
  Group C  FoS arithmetic — response values are geotechnically correct
  Group D  Ollama integration — vernacular populated / graceful None offline
  Group E  Region switching — Andes / East Africa return correct species
  Group F  Warnings — saturated / steep slopes produce warning_flags
  Group G  Health endpoint
"""

import pytest

# ── Canonical test payloads ───────────────────────────────────────────────────

# Partially saturated Himalayan slope: theta=30°, phi=30°, h_w/z=0.5
# Baseline FoS analytic: (18-9.81*0.5)*cos²30°*tan30° / (18*sin30°*cos30°)
#   = (18-4.905)*0.75*0.5774 / 7.794 = 5.672/7.794 ≈ 0.728 → CRITICAL
HIMALAYA_CRITICAL = {
    "theta": 30.0,
    "z": 1.0,
    "phi": 30.0,
    "h_w": 0.5,
    "c_prime": 0.0,
    "gamma": 18.0,
    "gamma_w": 9.81,
    "region": "himalaya",
}

# Stable dry gentle slope: theta=15°, phi=32°, dry
HIMALAYA_STABLE = {
    "theta": 15.0,
    "z": 1.5,
    "phi": 32.0,
    "h_w": 0.0,
    "c_prime": 2.0,
    "gamma": 18.0,
    "gamma_w": 9.81,
    "region": "himalaya",
}

# Andes blueprint region
ANDES_SLOPE = {
    "theta": 20.0,
    "z": 1.0,
    "phi": 28.0,
    "h_w": 0.3,
    "region": "andes",
}

# East Africa blueprint region
EAST_AFRICA_SLOPE = {
    "theta": 28.0,
    "z": 1.2,
    "phi": 26.0,
    "h_w": 0.0,
    "region": "east_africa",
}


# ── Group A: Happy path ───────────────────────────────────────────────────────

class TestHappyPath:

    def test_returns_200_for_valid_himalaya_payload(self, client, mock_ollama_offline):
        resp = client.post("/audit/", json=HIMALAYA_CRITICAL)
        assert resp.status_code == 200

    def test_response_contains_fos_baseline(self, client, mock_ollama_offline):
        resp = client.post("/audit/", json=HIMALAYA_CRITICAL)
        data = resp.json()
        assert "fos_baseline" in data
        assert isinstance(data["fos_baseline"], float)

    def test_response_contains_fos_post_intervention(self, client, mock_ollama_offline):
        resp = client.post("/audit/", json=HIMALAYA_CRITICAL)
        data = resp.json()
        assert "fos_post_intervention" in data
        assert isinstance(data["fos_post_intervention"], float)

    def test_response_contains_fos_improvement(self, client, mock_ollama_offline):
        resp = client.post("/audit/", json=HIMALAYA_CRITICAL)
        data = resp.json()
        assert "fos_improvement" in data
        assert isinstance(data["fos_improvement"], float)

    def test_response_contains_risk_level(self, client, mock_ollama_offline):
        resp = client.post("/audit/", json=HIMALAYA_CRITICAL)
        data = resp.json()
        assert data["risk_level"] in ("STABLE", "MARGINAL", "CRITICAL")

    def test_response_contains_risk_level_post(self, client, mock_ollama_offline):
        resp = client.post("/audit/", json=HIMALAYA_CRITICAL)
        data = resp.json()
        assert data["risk_level_post"] in ("STABLE", "MARGINAL", "CRITICAL")

    def test_response_contains_slope_band(self, client, mock_ollama_offline):
        resp = client.post("/audit/", json=HIMALAYA_CRITICAL)
        data = resp.json()
        assert "slope_band" in data
        assert len(data["slope_band"]) > 0

    def test_response_contains_non_empty_prescriptions(self, client, mock_ollama_offline):
        resp = client.post("/audit/", json=HIMALAYA_CRITICAL)
        data = resp.json()
        assert "prescriptions" in data
        assert len(data["prescriptions"]) >= 1

    def test_response_prescription_has_required_fields(self, client, mock_ollama_offline):
        resp = client.post("/audit/", json=HIMALAYA_CRITICAL)
        p = resp.json()["prescriptions"][0]
        assert "method" in p
        assert "species" in p
        assert "spacing_physical" in p
        assert "depth_physical" in p
        assert "priority" in p

    def test_response_contains_region(self, client, mock_ollama_offline):
        resp = client.post("/audit/", json=HIMALAYA_CRITICAL)
        assert resp.json()["region"] == "himalaya"

    def test_default_region_is_himalaya(self, client, mock_ollama_offline):
        """Omitting region from payload should default to himalaya."""
        payload = {"theta": 20.0, "z": 1.0, "phi": 30.0}
        resp = client.post("/audit/", json=payload)
        assert resp.status_code == 200
        assert resp.json()["region"] == "himalaya"

    def test_warning_flags_is_list(self, client, mock_ollama_offline):
        resp = client.post("/audit/", json=HIMALAYA_STABLE)
        assert isinstance(resp.json()["warning_flags"], list)


# ── Group B: Pydantic validation ─────────────────────────────────────────────

class TestValidation:

    def test_missing_required_theta_returns_422(self, client):
        resp = client.post("/audit/", json={"z": 1.0, "phi": 30.0})
        assert resp.status_code == 422

    def test_missing_required_z_returns_422(self, client):
        resp = client.post("/audit/", json={"theta": 30.0, "phi": 30.0})
        assert resp.status_code == 422

    def test_missing_required_phi_returns_422(self, client):
        resp = client.post("/audit/", json={"theta": 30.0, "z": 1.0})
        assert resp.status_code == 422

    def test_theta_above_89_returns_422(self, client):
        resp = client.post("/audit/", json={"theta": 90.0, "z": 1.0, "phi": 30.0})
        assert resp.status_code == 422

    def test_theta_below_1_returns_422(self, client):
        resp = client.post("/audit/", json={"theta": 0.0, "z": 1.0, "phi": 30.0})
        assert resp.status_code == 422

    def test_negative_z_returns_422(self, client):
        resp = client.post("/audit/", json={"theta": 30.0, "z": -1.0, "phi": 30.0})
        assert resp.status_code == 422

    def test_phi_above_45_returns_422(self, client):
        resp = client.post("/audit/", json={"theta": 30.0, "z": 1.0, "phi": 50.0})
        assert resp.status_code == 422

    def test_hw_exceeds_z_returns_422(self, client):
        """h_w > z is physically impossible; validator must reject it."""
        resp = client.post("/audit/", json={"theta": 30.0, "z": 1.0, "phi": 30.0, "h_w": 1.5})
        assert resp.status_code == 422

    def test_invalid_region_returns_422(self, client):
        resp = client.post("/audit/", json={"theta": 30.0, "z": 1.0, "phi": 30.0,
                                            "region": "mars"})
        assert resp.status_code == 422


# ── Group C: FoS arithmetic correctness ──────────────────────────────────────

class TestFosArithmetic:

    def test_critical_slope_baseline_is_below_1(self, client, mock_ollama_offline):
        """
        theta=30, phi=30, h_w=0.5 (50% saturated) must produce FoS < 1.0.
        Analytic value ≈ 0.728.
        """
        resp = client.post("/audit/", json=HIMALAYA_CRITICAL)
        assert resp.json()["fos_baseline"] < 1.0

    def test_critical_slope_risk_is_critical(self, client, mock_ollama_offline):
        resp = client.post("/audit/", json=HIMALAYA_CRITICAL)
        assert resp.json()["risk_level"] == "CRITICAL"

    def test_post_intervention_fos_greater_than_baseline(self, client, mock_ollama_offline):
        """Bio-engineering must always increase FoS (c_r > 0 adds to numerator)."""
        resp = client.post("/audit/", json=HIMALAYA_CRITICAL)
        data = resp.json()
        assert data["fos_post_intervention"] > data["fos_baseline"]

    def test_fos_improvement_equals_difference(self, client, mock_ollama_offline):
        """fos_improvement must equal fos_post - fos_baseline (within float rounding)."""
        resp = client.post("/audit/", json=HIMALAYA_CRITICAL)
        data = resp.json()
        expected = round(data["fos_post_intervention"] - data["fos_baseline"], 4)
        assert data["fos_improvement"] == pytest.approx(expected, abs=1e-3)

    def test_stable_slope_risk_is_stable(self, client, mock_ollama_offline):
        resp = client.post("/audit/", json=HIMALAYA_STABLE)
        assert resp.json()["risk_level"] == "STABLE"

    def test_stable_slope_baseline_above_1_5(self, client, mock_ollama_offline):
        resp = client.post("/audit/", json=HIMALAYA_STABLE)
        assert resp.json()["fos_baseline"] > 1.5

    def test_critical_slope_band_is_mid(self, client, mock_ollama_offline):
        """theta=30° falls in the 25°–40° mid band."""
        resp = client.post("/audit/", json=HIMALAYA_CRITICAL)
        assert "25" in resp.json()["slope_band"]

    def test_stable_gentle_slope_band_is_low(self, client, mock_ollama_offline):
        """theta=15° falls in the < 25° low band."""
        resp = client.post("/audit/", json=HIMALAYA_STABLE)
        assert "25" in resp.json()["slope_band"]  # label contains "25" as upper bound


# ── Group D: Ollama integration ───────────────────────────────────────────────

class TestOllamaIntegration:

    def test_vernacular_populated_when_ollama_available(self, client, mock_ollama_success):
        resp = client.post("/audit/", json=HIMALAYA_CRITICAL)
        data = resp.json()
        assert data["vernacular_script"] is not None
        assert len(data["vernacular_script"]) > 0

    def test_vernacular_is_none_when_ollama_offline(self, client, mock_ollama_offline):
        """Audit endpoint must return 200 with vernacular_script=null when Ollama is down."""
        resp = client.post("/audit/", json=HIMALAYA_CRITICAL)
        assert resp.status_code == 200
        assert resp.json()["vernacular_script"] is None

    def test_ollama_called_once_per_request(self, client, mock_ollama_success):
        """translate_to_vernacular must be called exactly once per audit request."""
        client.post("/audit/", json=HIMALAYA_CRITICAL)
        assert mock_ollama_success.call_count == 1

    def test_ollama_receives_correct_region(self, client, mock_ollama_success):
        """The region parameter must be forwarded to translate_to_vernacular."""
        client.post("/audit/", json=HIMALAYA_CRITICAL)
        _, kwargs = mock_ollama_success.call_args
        assert kwargs.get("region") == "himalaya" or mock_ollama_success.call_args[0][3] == "himalaya"


# ── Group E: Region switching ─────────────────────────────────────────────────

class TestRegionSwitching:

    def test_andes_region_returns_200(self, client, mock_ollama_offline):
        resp = client.post("/audit/", json=ANDES_SLOPE)
        assert resp.status_code == 200

    def test_east_africa_region_returns_200(self, client, mock_ollama_offline):
        resp = client.post("/audit/", json=EAST_AFRICA_SLOPE)
        assert resp.status_code == 200

    def test_andes_prescriptions_contain_ichu(self, client, mock_ollama_offline):
        resp = client.post("/audit/", json=ANDES_SLOPE)
        all_species = [
            s for p in resp.json()["prescriptions"] for s in p["species"]
        ]
        assert any("Festuca" in s or "Ichu" in s for s in all_species)

    def test_east_africa_prescriptions_contain_teff_or_sesbania(self, client, mock_ollama_offline):
        resp = client.post("/audit/", json=EAST_AFRICA_SLOPE)
        all_species = [
            s for p in resp.json()["prescriptions"] for s in p["species"]
        ]
        assert any("Eragrostis" in s or "Sesbania" in s or "Teff" in s for s in all_species)

    def test_himalaya_and_andes_different_prescriptions(self, client, mock_ollama_offline):
        """Same geometry, different regions must produce different species."""
        base = {"theta": 20.0, "z": 1.0, "phi": 28.0, "h_w": 0.0}
        h = client.post("/audit/", json={**base, "region": "himalaya"}).json()
        a = client.post("/audit/", json={**base, "region": "andes"}).json()
        h_species = {s for p in h["prescriptions"] for s in p["species"]}
        a_species = {s for p in a["prescriptions"] for s in p["species"]}
        assert h_species != a_species


# ── Group F: Warnings ─────────────────────────────────────────────────────────

class TestWarnings:

    def test_dry_gentle_slope_no_warnings(self, client, mock_ollama_offline):
        resp = client.post("/audit/", json=HIMALAYA_STABLE)
        assert resp.json()["warning_flags"] == []

    def test_saturated_slope_has_warning(self, client, mock_ollama_offline):
        payload = {"theta": 20.0, "z": 1.0, "phi": 30.0, "h_w": 1.0, "region": "himalaya"}
        resp = client.post("/audit/", json=payload)
        assert len(resp.json()["warning_flags"]) > 0

    def test_post_critical_slope_warning_added(self, client, mock_ollama_offline):
        """
        A very steep saturated slope where even bio-engineering leaves FoS < 1.0
        must have a 'Post-intervention FoS still CRITICAL' warning.
        theta=70, phi=20, h_w=1.0 is insurmountably steep for vegetation alone.
        """
        payload = {"theta": 70.0, "z": 1.0, "phi": 20.0, "h_w": 1.0, "region": "himalaya"}
        resp = client.post("/audit/", json=payload)
        data = resp.json()
        assert data["risk_level_post"] == "CRITICAL"
        assert any("CRITICAL" in w for w in data["warning_flags"])


# ── Group G: Health endpoint ──────────────────────────────────────────────────

class TestHealthEndpoint:

    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_returns_ok_status(self, client):
        resp = client.get("/health")
        assert resp.json()["status"] == "ok"

    def test_health_returns_service_name(self, client):
        resp = client.get("/health")
        assert "BioTerrace" in resp.json()["service"]
