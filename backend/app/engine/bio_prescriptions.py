"""
Rule-Based Bio-Engineering Prescription Engine
===============================================

Maps slope geometry and groundwater conditions to indigenous vegetative
bio-engineering prescriptions validated by:
  - ICIMOD (2011) Bio-engineering for Slope Protection and Erosion Control
  - Nepal Department of Roads Bio-engineering Manual (2013)
  - World Bank Mountain Infrastructure Resilience Programme (2021)
  - World Bank Ethiopia SLMP-II (2018)
  - World Bank Andes Resilience DPL (2020)

Prescription bands
------------------
    Slope < 25°    : Contour vegetative grass strips (Vetiver / Amliso / Ichu / Teff)
    Slope 25°–40°  : Live fascines, brush layering, contour diversion drains
    Slope > 40°    : Live crib walls, vegetative palisades, interceptor drainage

Physical unit translations are provided alongside metric values so that
prescriptions can be communicated to illiterate farmers:
    "two paces between rows / ~1.5 m"
    "one forearm deep / ~40 cm"
    "shoulder width between stakes / ~60 cm"

This module is region-aware: species names are loaded from JSON configs
under app/config/regions/. Swapping the region key (himalaya / andes /
east_africa) produces a culturally appropriate prescription in the same
engineering framework.

This module contains zero network calls. File I/O is limited to a
one-time load of the region JSON with in-process caching.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.models.audit_report import Prescription
from app.config.settings import settings


# ── In-process region config cache ───────────────────────────────────────────
_region_cache: dict[str, dict] = {}


def _load_region(region: str) -> dict:
    """Load and cache the region JSON config. Raises FileNotFoundError on bad key."""
    if region not in _region_cache:
        config_path: Path = settings.regions_dir / f"{region}.json"
        with open(config_path, encoding="utf-8") as fh:
            _region_cache[region] = json.load(fh)
    return _region_cache[region]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _band_key(theta: float, low_max: float, mid_max: float) -> str:
    """Return the internal band key ('low', 'mid', 'high') for a slope angle."""
    if theta < low_max:
        return "low"
    if theta <= mid_max:
        return "mid"
    return "high"


def _saturation_ratio(h_w: float, z: float) -> float:
    """Return h_w / z clamped to [0, 1]. Represents fractional groundwater height."""
    return min(h_w / z, 1.0) if z > 0 else 0.0


def _species_for_band(band: str, species_list: list[dict]) -> list[dict]:
    """
    Return species appropriate for a slope band.
    Low  : slope_band == 'low'
    Mid  : slope_band in ('low', 'mid')
    High : slope_band == 'high'; fallback to all if none tagged 'high'
    """
    if band == "low":
        candidates = [s for s in species_list if s["slope_band"] == "low"]
    elif band == "mid":
        candidates = [s for s in species_list if s["slope_band"] in ("low", "mid")]
    else:  # high
        candidates = [s for s in species_list if s["slope_band"] == "high"]
        if not candidates:  # region has no high-specific species; use strongest available
            candidates = sorted(
                species_list,
                key=lambda s: s["root_cohesion_kpa"]["min"],
                reverse=True,
            )[:2]
    return candidates


def _conservative_c_r(candidates: list[dict]) -> float:
    """
    Select the conservative (minimum published) root cohesion for the
    most effective species in the candidate list.

    Uses the MAXIMUM of minimum values — i.e. the best conservative floor
    among the recommended species. This approach is defensible to World
    Bank evaluators: it neither overstates (uses min, not max) nor
    understates (picks the strongest recommended species).
    """
    if not candidates:
        return 0.0
    return max(s["root_cohesion_kpa"]["min"] for s in candidates)


def _format_species_names(candidates: list[dict]) -> list[str]:
    return [
        f"{s['name_scientific']} ({s['name_local']})"
        for s in candidates
    ]


# ── Prescription builders (one per slope band) ───────────────────────────────

def _prescriptions_low(
    candidates: list[dict],
    sat_ratio: float,
    warnings: list[str],
) -> list[Prescription]:
    """Build prescriptions for low slopes (< 25°): contour grass strips."""
    species_names = _format_species_names(candidates)
    items: list[Prescription] = [
        Prescription(
            method="Contour Vegetative Grass Strips",
            species=species_names,
            spacing_physical="two paces between rows / ~1.5 m",
            depth_physical="one forearm deep / ~40 cm",
            priority=1,
            notes=(
                "Plant along contour lines following slope topography. "
                "Maintain rows at 40 cm height before first trimming. "
                "Row spacing can be doubled on slopes below 15°."
            ),
        )
    ]
    if sat_ratio > 0.5:
        warnings.append("High groundwater (> 50% saturation) — install surface drainage before planting.")
        items.append(
            Prescription(
                method="Contour Diversion Drain",
                species=[],
                spacing_physical="one pace upslope of each grass row / ~0.75 m",
                depth_physical="half forearm deep / ~20 cm",
                priority=2,
                notes="Urgent: channel surface runoff laterally off the slope before establishing vegetation.",
            )
        )
    return items


def _prescriptions_mid(
    candidates: list[dict],
    sat_ratio: float,
    warnings: list[str],
) -> list[Prescription]:
    """Build prescriptions for medium slopes (25°–40°): fascines + brush layering + drainage."""
    species_names = _format_species_names(candidates)
    items: list[Prescription] = [
        Prescription(
            method="Live Fascines and Brush Layering",
            species=species_names,
            spacing_physical="one arm's length between bundles / ~0.75 m",
            depth_physical="half forearm deep / ~20 cm",
            priority=1,
            notes=(
                "Bundle fresh cuttings (thumb-thick diameter) into fascines ~1 m long. "
                "Lay horizontally along contour; anchor with wooden stakes one pace apart. "
                "Backfill with excavated soil and tamp firmly."
            ),
        ),
        Prescription(
            method="Contour Diversion Drain",
            species=[],
            spacing_physical="one pace above each fascine row / ~0.75 m",
            depth_physical="half forearm deep / ~20 cm",
            priority=2,
            notes=(
                "Critical drainage intervention: diverts concentrated runoff before it "
                "saturates the soil behind the fascines."
            ),
        ),
    ]
    if sat_ratio > 0.5:
        warnings.append(
            "High groundwater on mid-slope — excavate drainage trench BEFORE installing fascines."
        )
    return items


def _prescriptions_high(
    candidates: list[dict],
    sat_ratio: float,
    warnings: list[str],
) -> list[Prescription]:
    """Build prescriptions for high slopes (> 40°): live crib walls + palisades + interceptor drain."""
    species_names = _format_species_names(candidates)
    items: list[Prescription] = [
        Prescription(
            method="Live Crib Walls",
            species=species_names,
            spacing_physical="one pace between crib poles / ~0.75 m",
            depth_physical="two forearms deep / ~80 cm",
            priority=1,
            notes=(
                "Construct log crib frames at horizontal intervals down the slope. "
                "Backfill with compacted soil; insert living cuttings or rooted stakes "
                "through crib members. Bamboo (Dendrocalamus) or dense shrub cuttings preferred."
            ),
        ),
        Prescription(
            method="Vegetative Palisades",
            species=species_names,
            spacing_physical="shoulder width between stakes / ~60 cm",
            depth_physical="one forearm deep / ~40 cm",
            priority=2,
            notes=(
                "Drive living stakes vertically in rows perpendicular to slope direction. "
                "Interweave with brush material to create a flexible retaining curtain."
            ),
        ),
        Prescription(
            method="Interceptor Drainage Channel",
            species=[],
            spacing_physical="one pace above crib wall series / ~0.75 m",
            depth_physical="half forearm deep / ~20 cm",
            priority=3,
            notes=(
                "Install at slope crown to intercept and divert surface and sub-surface flow "
                "away from the active failure zone. This is mandatory on slopes > 40°."
            ),
        ),
    ]
    if sat_ratio > 0.5:
        warnings.append(
            "CRITICAL: Saturated steep slope — immediate interceptor drainage and surface protection required."
        )
    return items


# ── Public API ────────────────────────────────────────────────────────────────

@dataclass
class PrescriptionResult:
    """Container returned by `prescribe()` — consumed by the audit router."""
    prescriptions: list[Prescription]
    c_r_kpa: float
    slope_band_label: str
    warning_flags: list[str] = field(default_factory=list)


def prescribe(
    theta: float,
    h_w: float,
    z: float,
    region: str = "himalaya",
) -> PrescriptionResult:
    """
    Generate bio-engineering prescriptions for a slope assessment.

    Parameters
    ----------
    theta : float
        Slope angle in degrees.
    h_w : float
        Groundwater height above failure plane in metres.
    z : float
        Depth to failure plane in metres.
    region : str
        Region config key: 'himalaya', 'andes', or 'east_africa'.

    Returns
    -------
    PrescriptionResult
        Contains the ordered prescription list, conservative c_r value for
        post-intervention FoS computation, slope band label, and any warnings.
    """
    config = _load_region(region)
    thresholds = config["slope_thresholds"]
    low_max: float = thresholds["low_max_deg"]
    mid_max: float = thresholds["mid_max_deg"]

    band = _band_key(theta, low_max, mid_max)
    sat_ratio = _saturation_ratio(h_w, z)
    candidates = _species_for_band(band, config["species"])
    c_r = _conservative_c_r(candidates)
    warnings: list[str] = []

    if band == "low":
        prescriptions = _prescriptions_low(candidates, sat_ratio, warnings)
        band_label = f"< {low_max:.0f}\u00b0"
    elif band == "mid":
        prescriptions = _prescriptions_mid(candidates, sat_ratio, warnings)
        band_label = f"{low_max:.0f}\u00b0\u2013{mid_max:.0f}\u00b0"
    else:
        prescriptions = _prescriptions_high(candidates, sat_ratio, warnings)
        band_label = f"> {mid_max:.0f}\u00b0"

    return PrescriptionResult(
        prescriptions=prescriptions,
        c_r_kpa=c_r,
        slope_band_label=band_label,
        warning_flags=warnings,
    )
