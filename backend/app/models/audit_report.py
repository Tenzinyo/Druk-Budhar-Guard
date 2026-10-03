from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """
    FoS thresholds aligned with World Bank / ICIMOD slope risk classification:
      STABLE   → FoS > 1.5  (adequate margin; monitoring recommended)
      MARGINAL → 1.0 < FoS ≤ 1.5  (intervention required; monitor closely)
      CRITICAL → FoS ≤ 1.0  (imminent failure; immediate action)
    """
    STABLE = "STABLE"
    MARGINAL = "MARGINAL"
    CRITICAL = "CRITICAL"


class Prescription(BaseModel):
    """A single bio-engineering intervention prescription."""

    method: str = Field(..., description="Engineering method name (e.g. 'Contour Vetiver Strips').")
    species: List[str] = Field(..., description="Recommended species (scientific and local names).")
    spacing_physical: str = Field(
        ...,
        description="Row spacing in low-literacy physical units (e.g. 'two paces apart / ~1.5 m').",
    )
    depth_physical: str = Field(
        ...,
        description="Planting depth in low-literacy physical units (e.g. 'one forearm deep / ~40 cm').",
    )
    priority: int = Field(
        ...,
        ge=1,
        description="Implementation priority. 1 = highest urgency.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional field notes or drainage requirements.",
    )


class AuditReport(BaseModel):
    """
    Full slope audit output combining deterministic geotechnical math
    and rule-based bio-engineering prescriptions.
    """

    # --- FoS results ---
    fos_baseline: float = Field(
        ..., description="Factor of Safety before any bio-engineering intervention."
    )
    fos_post_intervention: float = Field(
        ..., description="Estimated Factor of Safety after recommended bio-engineering."
    )
    fos_improvement: float = Field(
        ..., description="Absolute FoS gain from intervention (post − baseline)."
    )

    # --- Risk classification ---
    risk_level: RiskLevel = Field(..., description="Baseline risk level.")
    risk_level_post: RiskLevel = Field(..., description="Post-intervention risk level.")
    slope_band: str = Field(
        ..., description="Slope inclination band: '< 25°', '25°–40°', or '> 40°'."
    )

    # --- Prescriptions ---
    prescriptions: List[Prescription] = Field(
        ..., description="Ordered list of bio-engineering prescriptions (priority ascending)."
    )

    # --- Vernacular output ---
    vernacular_script: Optional[str] = Field(
        default=None,
        description="Ollama-generated conversational vernacular text (Hindi/Nepali).",
    )

    # --- Metadata ---
    region: str
    warning_flags: List[str] = Field(
        default_factory=list,
        description="Engineering warnings (e.g. 'Fully saturated — immediate drainage required').",
    )
