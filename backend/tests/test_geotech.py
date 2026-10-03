"""
Layer 1 Unit Tests — Geotechnical FoS Engine
=============================================

All expected values are derived analytically from the verified equation:

    FoS = [c' + c_r + (γ·z − γ_w·h_w)·cos²θ·tan φ]
          ─────────────────────────────────────────────
                       γ·z·sin θ·cos θ

Reference anchor values are documented below each test.
pytest.approx tolerance: rel=1e-3 (0.1%) — appropriate for engineering FoS.
"""

import math

import pytest

from app.engine.geotech import classify_risk, compute_fos, get_slope_band
from app.models.audit_report import RiskLevel


# ── Helpers for expected-value computation ───────────────────────────────────

def _expected_fos(theta_deg, z, phi_deg, c_prime, gamma, gamma_w, h_w, c_r):
    """Pure Python reference implementation (mirrors geotech.py, used for test assertions)."""
    theta = math.radians(theta_deg)
    phi = math.radians(phi_deg)
    den = gamma * z * math.sin(theta) * math.cos(theta)
    num = c_prime + c_r + (gamma * z - gamma_w * h_w) * (math.cos(theta) ** 2) * math.tan(phi)
    return num / den


# ── compute_fos tests ─────────────────────────────────────────────────────────

class TestComputeFos:

    def test_dry_cohesionless_at_critical_angle(self, slope_dry_critical):
        """
        Classic result: cohesionless dry slope where theta = phi = 30°.
        Expected FoS = 1.000 exactly (slope is at its critical angle).
        Source: Das, Principles of Geotechnical Engineering, 9th Ed., Example 10.2.
        """
        fos = compute_fos(**slope_dry_critical)
        assert fos == pytest.approx(1.0, rel=1e-3)

    def test_fully_saturated_slope_is_critical(self, slope_saturated):
        """
        Fully saturated slope (h_w = z) at theta = phi = 30°.
        Groundwater reduces the normal effective stress → FoS < 1.0 (failure).

        Analytic check:
            num = (18 - 9.81) × 0.75 × tan(30°) = 8.19 × 0.75 × 0.5774 = 3.550 kPa
            den = 18 × 0.5 × cos(30°) = 7.794 kPa
            FoS = 3.550 / 7.794 ≈ 0.455
        """
        fos = compute_fos(**slope_saturated)
        expected = _expected_fos(**slope_saturated)
        assert fos == pytest.approx(expected, rel=1e-3)
        assert fos < 1.0, "Saturated slope at critical angle must be in failure state."

    def test_vetiver_c_r_minimum_lifts_slope_to_marginal(self, slope_saturated):
        """
        Adding Vetiver minimum root cohesion (c_r = 5 kPa) to a saturated critical slope
        should move it from CRITICAL → MARGINAL.
        Source: ICIMOD (2011), Table 4.2 — Vetiver root cohesion 5–18 kPa.
        """
        params = {**slope_saturated, "c_r": 5.0}
        fos = compute_fos(**params)
        assert fos > 1.0, "Vetiver c_r=5 kPa must produce FoS > 1.0 on this slope."
        assert fos <= 1.5, "Vetiver c_r=5 kPa should not reach STABLE on a saturated slope."

    def test_dendrocalamus_c_r_minimum_achieves_stable(self, slope_saturated):
        """
        Dendrocalamus bamboo minimum root cohesion (c_r = 10 kPa) on the saturated
        slope should achieve FoS > 1.5 (STABLE).
        Source: World Bank Mountain Infrastructure Resilience Programme (2021).
        """
        params = {**slope_saturated, "c_r": 10.0}
        fos = compute_fos(**params)
        assert fos > 1.5, "Dendrocalamus c_r=10 kPa must achieve STABLE on this slope."

    def test_vetiver_c_r_maximum_achieves_stable(self, slope_saturated):
        """
        Vetiver maximum root cohesion (c_r = 18 kPa) must produce FoS well above 1.5.
        Validates the upper bound of ICIMOD c_r range.
        """
        params = {**slope_saturated, "c_r": 18.0}
        fos = compute_fos(**params)
        assert fos > 1.5

    def test_cohesion_adds_to_stability(self, slope_dry_critical):
        """
        Adding effective soil cohesion (c' > 0) to the critical-angle dry slope
        must increase FoS above 1.0.
        """
        params = {**slope_dry_critical, "c_prime": 5.0}
        fos = compute_fos(**params)
        fos_bare = compute_fos(**slope_dry_critical)
        assert fos > fos_bare

    def test_partial_saturation_intermediate_fos(self, slope_dry_critical):
        """
        Half-saturated slope (h_w = z/2) should have FoS between dry and fully saturated.
        """
        fos_dry = compute_fos(**slope_dry_critical)
        fos_sat = compute_fos(**{**slope_dry_critical, "h_w": 1.0})
        fos_half = compute_fos(**{**slope_dry_critical, "h_w": 0.5})
        assert fos_sat < fos_half < fos_dry

    def test_steep_slope_low_fos(self):
        """
        A steep 45° slope with typical Himalayan soil and no cohesion (h_w=0)
        should have FoS < 1.0 when phi=30° (tan(30°) < tan(45°) → unstable).
        """
        fos = compute_fos(theta_deg=45.0, z=1.5, phi_deg=30.0, c_prime=0.0,
                          gamma=18.0, gamma_w=9.81, h_w=0.0, c_r=0.0)
        # tan(30°)/tan(45°) = 0.577 < 1 → FoS < 1
        assert fos < 1.0

    def test_gentle_slope_high_fos(self):
        """
        A gentle 10° slope with phi=30° and light soil should be highly stable.
        """
        fos = compute_fos(theta_deg=10.0, z=1.0, phi_deg=30.0, c_prime=0.0,
                          gamma=17.0, gamma_w=9.81, h_w=0.0, c_r=0.0)
        assert fos > 1.5

    def test_minimum_valid_theta(self):
        """
        theta = 1° should not raise and should produce a very large (stable) FoS.
        """
        fos = compute_fos(theta_deg=1.0, z=1.0, phi_deg=30.0,
                          c_prime=0.0, gamma=18.0, gamma_w=9.81, h_w=0.0, c_r=0.0)
        assert fos > 10.0, "A 1° slope must be overwhelmingly stable."

    def test_near_vertical_slope_low_fos(self):
        """
        theta = 85° with phi=30° should produce a very low FoS (near-vertical failure).
        """
        fos = compute_fos(theta_deg=85.0, z=1.0, phi_deg=30.0,
                          c_prime=0.0, gamma=18.0, gamma_w=9.81, h_w=0.0, c_r=0.0)
        assert fos < 0.3

    def test_zero_denominator_raises(self):
        """
        Passing z=0 should cause a non-positive denominator and raise ValueError.
        (Input validation in Pydantic prevents this at API level, but engine is defensive.)
        """
        with pytest.raises(ValueError, match="non-positive"):
            compute_fos(theta_deg=30.0, z=0.0, phi_deg=30.0)

    def test_c_r_is_additive_to_c_prime(self, slope_saturated):
        """
        c_r and c_prime must contribute equally (both in numerator kPa terms).
        FoS(c'=5, c_r=0) must equal FoS(c'=0, c_r=5).
        """
        fos_cprime = compute_fos(**{**slope_saturated, "c_prime": 5.0, "c_r": 0.0})
        fos_cr = compute_fos(**{**slope_saturated, "c_prime": 0.0, "c_r": 5.0})
        assert fos_cprime == pytest.approx(fos_cr, rel=1e-9)


# ── classify_risk tests ───────────────────────────────────────────────────────

class TestClassifyRisk:

    @pytest.mark.parametrize("fos,expected", [
        (2.0, RiskLevel.STABLE),
        (1.51, RiskLevel.STABLE),
        (1.5, RiskLevel.MARGINAL),   # boundary: 1.5 is NOT > 1.5
        (1.2, RiskLevel.MARGINAL),
        (1.01, RiskLevel.MARGINAL),
        (1.0, RiskLevel.CRITICAL),   # boundary: exactly 1.0 is CRITICAL
        (0.8, RiskLevel.CRITICAL),
        (0.1, RiskLevel.CRITICAL),
    ])
    def test_classification(self, fos, expected):
        assert classify_risk(fos) == expected


# ── get_slope_band tests ──────────────────────────────────────────────────────

class TestGetSlopeBand:

    @pytest.mark.parametrize("theta,expected", [
        (10.0,  "< 25°"),
        (24.9,  "< 25°"),
        (25.0,  "25°\u201340°"),   # boundary: 25.0 goes INTO mid band
        (32.0,  "25°\u201340°"),
        (40.0,  "25°\u201340°"),   # boundary: 40.0 is still mid (≤ 40)
        (40.1,  "> 40°"),
        (60.0,  "> 40°"),
    ])
    def test_standard_thresholds(self, theta, expected):
        assert get_slope_band(theta) == expected

    def test_custom_thresholds(self):
        """Custom threshold values produce correctly formatted band labels."""
        assert get_slope_band(20.0, low_max_deg=30.0, mid_max_deg=50.0) == "< 30°"
        assert get_slope_band(35.0, low_max_deg=30.0, mid_max_deg=50.0) == "30°\u201350°"
        assert get_slope_band(55.0, low_max_deg=30.0, mid_max_deg=50.0) == "> 50°"
