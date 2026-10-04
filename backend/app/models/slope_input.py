from typing import Literal
from pydantic import BaseModel, Field, model_validator


class SlopeInput(BaseModel):
    """
    Input parameters for the Infinite Slope Factor of Safety assessment.

    All geotechnical parameters are grounded in:
      - Infinite Slope stability analysis (Das, Principles of Geotechnical Engineering)
      - ICIMOD mountain bio-engineering field data
      - Nepal Department of Roads slope stabilisation guidelines
    """

    # --- Geometry ---
    theta: float = Field(
        ...,
        ge=1.0,
        le=89.0,
        description="Slope angle in degrees (1–89). 0° and 90° excluded: degenerate cases.",
    )
    z: float = Field(
        ...,
        gt=0.0,
        description="Vertical depth to failure plane in metres (e.g. 0.5–3.0 m for shallow slides).",
    )

    # --- Soil properties ---
    phi: float = Field(
        ...,
        ge=0.0,
        le=45.0,
        description="Effective internal friction angle in degrees. Himalayan soils: 25°–35°.",
    )
    c_prime: float = Field(
        default=0.0,
        ge=0.0,
        description="Effective cohesion of soil in kPa. Use 0 for cohesionless sandy soils.",
    )
    gamma: float = Field(
        default=18.0,
        gt=0.0,
        description="Bulk unit weight of soil in kN/m³. Himalayan residual soils: 16–20 kN/m³.",
    )

    # --- Groundwater ---
    gamma_w: float = Field(
        default=9.81,
        gt=0.0,
        description="Unit weight of water in kN/m³. Standard = 9.81.",
    )
    h_w: float = Field(
        default=0.0,
        ge=0.0,
        description=(
            "Height of groundwater above the failure plane in metres. "
            "h_w = 0 → dry slope; h_w = z → fully saturated (worst case)."
        ),
    )

    # --- Region ---
    region: Literal["himalaya", "andes", "east_africa"] = Field(
        default="himalaya",
        description="Region config key. Selects species palette and soil defaults.",
    )

    # --- Language ---
    language: str = Field(
        default="",
        description="User-selected language for vernacular advisory (e.g. 'Hindi', 'Nepali'). Empty = region default.",
    )

    @model_validator(mode="after")
    def hw_cannot_exceed_z(self) -> "SlopeInput":
        if self.h_w > self.z:
            raise ValueError(
                f"h_w ({self.h_w} m) cannot exceed z ({self.z} m). "
                "Groundwater cannot rise above the soil surface."
            )
        return self
