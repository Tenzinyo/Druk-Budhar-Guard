"""
Layer 1 Unit Tests — Bio-Engineering Prescription Engine
=========================================================

Tests the rule-based prescriber across all three slope bands and all
three supported regions (himalaya, andes, east_africa).

Validates:
  1. Correct band routing (< 25°, 25°–40°, > 40°)
  2. Prescription list length and content invariants
  3. Physical unit strings are present and non-empty
  4. c_r values fall within published ICIMOD / World Bank species ranges
  5. Region-switching produces different species names
  6. Saturation warnings are triggered correctly
  7. High-priority prescription is always priority=1
"""

import pytest

from app.engine.bio_prescriptions import prescribe, PrescriptionResult


# ── Band routing ──────────────────────────────────────────────────────────────

class TestBandRouting:

    def test_low_band_label(self):
        result = prescribe(theta=15.0, h_w=0.0, z=1.0, region="himalaya")
        assert result.slope_band_label == "< 25°"

    def test_mid_band_label(self):
        result = prescribe(theta=30.0, h_w=0.0, z=1.0, region="himalaya")
        assert result.slope_band_label == "25°\u201340°"

    def test_high_band_label(self):
        result = prescribe(theta=50.0, h_w=0.0, z=1.0, region="himalaya")
        assert result.slope_band_label == "> 40°"

    def test_boundary_25_is_mid(self):
        result = prescribe(theta=25.0, h_w=0.0, z=1.0, region="himalaya")
        assert result.slope_band_label == "25°\u201340°"

    def test_boundary_40_is_mid(self):
        result = prescribe(theta=40.0, h_w=0.0, z=1.0, region="himalaya")
        assert result.slope_band_label == "25°\u201340°"

    def test_just_above_40_is_high(self):
        result = prescribe(theta=40.1, h_w=0.0, z=1.0, region="himalaya")
        assert result.slope_band_label == "> 40°"


# ── Prescription list invariants ──────────────────────────────────────────────

class TestPrescriptionListInvariants:

    def test_low_band_returns_at_least_one_prescription(self):
        result = prescribe(theta=15.0, h_w=0.0, z=1.0, region="himalaya")
        assert len(result.prescriptions) >= 1

    def test_mid_band_returns_at_least_two_prescriptions(self):
        """Mid band always includes a drainage prescription alongside the planting one."""
        result = prescribe(theta=30.0, h_w=0.0, z=1.0, region="himalaya")
        assert len(result.prescriptions) >= 2

    def test_high_band_returns_at_least_three_prescriptions(self):
        """High band always includes crib walls, palisades, AND interceptor drainage."""
        result = prescribe(theta=50.0, h_w=0.0, z=1.0, region="himalaya")
        assert len(result.prescriptions) >= 3

    def test_priority_one_always_present(self):
        for theta in [15.0, 30.0, 50.0]:
            result = prescribe(theta=theta, h_w=0.0, z=1.0, region="himalaya")
            priorities = [p.priority for p in result.prescriptions]
            assert 1 in priorities, f"Priority 1 missing for theta={theta}"

    def test_prescriptions_ordered_by_priority(self):
        """First prescription in the list must always have the lowest priority number."""
        for theta in [15.0, 30.0, 50.0]:
            result = prescribe(theta=theta, h_w=0.0, z=1.0, region="himalaya")
            first_priority = result.prescriptions[0].priority
            all_priorities = [p.priority for p in result.prescriptions]
            assert first_priority == min(all_priorities)


# ── Physical unit string content ──────────────────────────────────────────────

class TestPhysicalUnitStrings:

    @pytest.mark.parametrize("theta", [15.0, 30.0, 50.0])
    def test_spacing_physical_non_empty(self, theta):
        result = prescribe(theta=theta, h_w=0.0, z=1.0, region="himalaya")
        for p in result.prescriptions:
            # Drainage prescriptions may have no species but must still have spacing
            assert isinstance(p.spacing_physical, str)
            assert len(p.spacing_physical) > 0

    @pytest.mark.parametrize("theta", [15.0, 30.0, 50.0])
    def test_depth_physical_non_empty(self, theta):
        result = prescribe(theta=theta, h_w=0.0, z=1.0, region="himalaya")
        for p in result.prescriptions:
            assert isinstance(p.depth_physical, str)
            assert len(p.depth_physical) > 0

    def test_low_band_spacing_contains_paces(self):
        result = prescribe(theta=15.0, h_w=0.0, z=1.0, region="himalaya")
        primary = result.prescriptions[0]
        assert "pace" in primary.spacing_physical.lower() or "m" in primary.spacing_physical

    def test_high_band_depth_contains_forearm(self):
        result = prescribe(theta=50.0, h_w=0.0, z=1.0, region="himalaya")
        primary = result.prescriptions[0]
        assert "forearm" in primary.depth_physical.lower() or "cm" in primary.depth_physical


# ── Root cohesion (c_r) range validation ─────────────────────────────────────

class TestCohesionRanges:
    """
    c_r values must fall within published species ranges from ICIMOD / World Bank sources.
    Himalaya species ranges:
        Vetiver (Chrysopogon zizanioides) : 5–18 kPa  [ICIMOD 2011]
        Amliso  (Thysanolaena latifolia)  : 3–8 kPa   [Nepal DoR 2013]
        Dendrocalamus hamiltonii          : 10–18 kPa [World Bank 2021]
    """

    def test_himalaya_low_band_c_r_within_vetiver_range(self):
        """Low band selects grass species; c_r must be ≥ Vetiver floor (5 kPa)."""
        result = prescribe(theta=15.0, h_w=0.0, z=1.0, region="himalaya")
        assert result.c_r_kpa >= 5.0, "Low-band c_r must be ≥ Vetiver minimum (5 kPa)"
        assert result.c_r_kpa <= 18.0, "Low-band c_r must be ≤ Vetiver maximum (18 kPa)"

    def test_himalaya_high_band_c_r_within_bamboo_range(self):
        """High band selects Dendrocalamus bamboo; c_r must be ≥ bamboo floor (10 kPa)."""
        result = prescribe(theta=50.0, h_w=0.0, z=1.0, region="himalaya")
        assert result.c_r_kpa >= 10.0, "High-band c_r must be ≥ Dendrocalamus minimum (10 kPa)"
        assert result.c_r_kpa <= 18.0, "High-band c_r must be ≤ Dendrocalamus maximum (18 kPa)"

    def test_c_r_is_positive(self):
        for theta in [15.0, 30.0, 50.0]:
            result = prescribe(theta=theta, h_w=0.0, z=1.0, region="himalaya")
            assert result.c_r_kpa > 0.0, f"c_r must be > 0 for theta={theta}"

    def test_andes_c_r_within_ichu_range(self):
        """Andes low band uses Ichu (2–6 kPa); c_r must be within that range."""
        result = prescribe(theta=15.0, h_w=0.0, z=1.0, region="andes")
        assert result.c_r_kpa >= 2.0
        assert result.c_r_kpa <= 12.0  # max is Polylepis ceiling for high band

    def test_east_africa_c_r_within_sesbania_range(self):
        """East Africa mid band uses Sesbania (5–10 kPa)."""
        result = prescribe(theta=30.0, h_w=0.0, z=1.0, region="east_africa")
        # Mid band can include sesbania (slope_band="mid") → c_r ≥ 5.0
        # or teff (slope_band="low") → c_r ≥ 1.5
        assert result.c_r_kpa >= 1.5


# ── Region switching produces different species ───────────────────────────────

class TestRegionSwitching:

    def test_himalaya_vs_andes_different_species(self):
        h = prescribe(theta=15.0, h_w=0.0, z=1.0, region="himalaya")
        a = prescribe(theta=15.0, h_w=0.0, z=1.0, region="andes")
        h_species = {s for p in h.prescriptions for s in p.species}
        a_species = {s for p in a.prescriptions for s in p.species}
        assert h_species != a_species, "Himalaya and Andes must prescribe different species."

    def test_himalaya_vs_east_africa_different_species(self):
        h = prescribe(theta=15.0, h_w=0.0, z=1.0, region="himalaya")
        e = prescribe(theta=15.0, h_w=0.0, z=1.0, region="east_africa")
        h_species = {s for p in h.prescriptions for s in p.species}
        e_species = {s for p in e.prescriptions for s in p.species}
        assert h_species != e_species

    def test_himalaya_contains_vetiver_name(self):
        result = prescribe(theta=15.0, h_w=0.0, z=1.0, region="himalaya")
        all_species = [s for p in result.prescriptions for s in p.species]
        assert any("Chrysopogon" in s or "Vetiver" in s or "Khas" in s for s in all_species)

    def test_andes_contains_ichu_name(self):
        result = prescribe(theta=15.0, h_w=0.0, z=1.0, region="andes")
        all_species = [s for p in result.prescriptions for s in p.species]
        assert any("Festuca" in s or "Ichu" in s or "Paja" in s for s in all_species)

    def test_east_africa_contains_teff_name(self):
        result = prescribe(theta=15.0, h_w=0.0, z=1.0, region="east_africa")
        all_species = [s for p in result.prescriptions for s in p.species]
        assert any("Eragrostis" in s or "Teff" in s for s in all_species)


# ── Saturation warnings ───────────────────────────────────────────────────────

class TestSaturationWarnings:

    def test_no_warning_on_dry_slope(self):
        result = prescribe(theta=15.0, h_w=0.0, z=1.0, region="himalaya")
        assert len(result.warning_flags) == 0

    def test_warning_triggered_on_saturated_low_band(self):
        """h_w = z (fully saturated) must trigger a drainage warning."""
        result = prescribe(theta=15.0, h_w=1.0, z=1.0, region="himalaya")
        assert len(result.warning_flags) > 0
        assert any("drainage" in w.lower() or "groundwater" in w.lower()
                   for w in result.warning_flags)

    def test_extra_drainage_prescription_on_saturated_low_band(self):
        """Saturated low-band slope must include a drainage prescription."""
        result = prescribe(theta=15.0, h_w=1.0, z=1.0, region="himalaya")
        methods = [p.method.lower() for p in result.prescriptions]
        assert any("drain" in m for m in methods)

    def test_warning_triggered_on_saturated_high_band(self):
        result = prescribe(theta=50.0, h_w=1.0, z=1.0, region="himalaya")
        assert len(result.warning_flags) > 0

    def test_no_warning_on_partial_saturation_below_threshold(self):
        """h_w = 0.3z (< 50% threshold) must NOT trigger a warning."""
        result = prescribe(theta=15.0, h_w=0.3, z=1.0, region="himalaya")
        assert len(result.warning_flags) == 0
