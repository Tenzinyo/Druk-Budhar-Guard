"""
Infinite Slope Factor of Safety Engine with Root Tensile Cohesion
=================================================================

Implements the augmented Infinite Slope model for shallow translational
slides common in Himalayan and other mountain terrain.

Governing equation (Das, Principles of Geotechnical Engineering, 9th Ed.;
ICIMOD Bio-engineering for Slope Protection, 2011):

    FoS = [c' + c_r + (γ·z − γ_w·h_w)·cos²θ·tan φ]
          ─────────────────────────────────────────────
                       γ·z·sin θ·cos θ

Variable legend
---------------
    c'    Effective cohesion of soil (kPa)
    c_r   Root tensile cohesion contributed by vegetation (kPa)
           Vetiver (Chrysopogon zizanioides) : 5–18 kPa  [ICIMOD 2011]
           Amliso  (Thysanolaena latifolia)  : 3–8 kPa   [Nepal DoR 2013]
           Dendrocalamus hamiltonii (bamboo) : 10–18 kPa [World Bank 2021]
    γ     Bulk unit weight of soil (kN/m³)
    γ_w   Unit weight of water = 9.81 kN/m³ (standard)
    z     Vertical depth to failure plane (m)
    h_w   Height of groundwater above failure plane (m); 0 ≤ h_w ≤ z
    θ     Slope angle (degrees)
    φ     Internal friction angle (degrees)

FoS interpretation
------------------
    FoS > 1.5   STABLE   — adequate margin; routine monitoring recommended
    1.0 < FoS ≤ 1.5   MARGINAL — bio-engineering intervention required
    FoS ≤ 1.0   CRITICAL — imminent or active failure; emergency response

This module contains zero I/O and zero network calls.
All functions are pure and deterministic.
"""

import math

from app.models.audit_report import RiskLevel

# ── Risk classification thresholds (World Bank / ICIMOD convention) ──────────
_FOS_STABLE: float = 1.5
_FOS_CRITICAL: float = 1.0


def compute_fos(
    theta_deg: float,
    z: float,
    phi_deg: float,
    c_prime: float = 0.0,
    gamma: float = 18.0,
    gamma_w: float = 9.81,
    h_w: float = 0.0,
    c_r: float = 0.0,
) -> float:
    """
    Compute the Infinite Slope Factor of Safety.

    Parameters
    ----------
    theta_deg : float
        Slope angle in degrees. Must be in (0, 90) exclusive.
    z : float
        Depth to failure plane in metres. Must be > 0.
    phi_deg : float
        Effective internal friction angle in degrees [0, 45].
    c_prime : float
        Effective soil cohesion in kPa (default 0 = cohesionless soil).
    gamma : float
        Bulk unit weight of soil in kN/m³ (default 18).
    gamma_w : float
        Unit weight of water in kN/m³ (default 9.81).
    h_w : float
        Height of groundwater above failure plane in metres (default 0 = dry).
        Must satisfy 0 ≤ h_w ≤ z.
    c_r : float
        Root tensile cohesion in kPa (default 0 = bare soil, no vegetation).

    Returns
    -------
    float
        Factor of Safety. Values ≤ 1.0 indicate failure; > 1.5 indicate stability.

    Raises
    ------
    ValueError
        If the denominator is non-positive (degenerate geometry).
    """
    theta = math.radians(theta_deg)
    phi = math.radians(phi_deg)

    cos_t = math.cos(theta)
    sin_t = math.sin(theta)

    denominator = gamma * z * sin_t * cos_t
    if denominator <= 0.0:
        raise ValueError(
            f"Denominator is non-positive ({denominator:.6f} kPa). "
            "Ensure theta_deg > 0 and z > 0."
        )

    # Effective normal stress component on the failure plane
    normal_stress_frictional = (gamma * z - gamma_w * h_w) * (cos_t ** 2) * math.tan(phi)

    # Total shear strength (Mohr-Coulomb + root cohesion)
    numerator = c_prime + c_r + normal_stress_frictional

    return numerator / denominator


def classify_risk(fos: float) -> RiskLevel:
    """
    Map a Factor of Safety value to a risk level.

    Thresholds (ICIMOD / World Bank mountain infrastructure convention):
      STABLE   : FoS > 1.5
      MARGINAL : 1.0 < FoS ≤ 1.5
      CRITICAL : FoS ≤ 1.0

    Parameters
    ----------
    fos : float
        Factor of Safety value.

    Returns
    -------
    RiskLevel
    """
    if fos > _FOS_STABLE:
        return RiskLevel.STABLE
    if fos > _FOS_CRITICAL:
        return RiskLevel.MARGINAL
    return RiskLevel.CRITICAL


def get_slope_band(
    theta_deg: float,
    low_max_deg: float = 25.0,
    mid_max_deg: float = 40.0,
) -> str:
    """
    Classify slope angle into a bio-engineering prescription band.

    Parameters
    ----------
    theta_deg : float
        Slope angle in degrees.
    low_max_deg : float
        Upper boundary of the low (grass strip) band (default 25°).
    mid_max_deg : float
        Upper boundary of the medium (fascine / brush) band (default 40°).

    Returns
    -------
    str
        One of: '< 25°', '25°–40°', '> 40°'
        (or equivalent strings for non-default thresholds).
    """
    if theta_deg < low_max_deg:
        return f"< {low_max_deg:.0f}\u00b0"
    if theta_deg <= mid_max_deg:
        return f"{low_max_deg:.0f}\u00b0\u2013{mid_max_deg:.0f}\u00b0"
    return f"> {mid_max_deg:.0f}\u00b0"
