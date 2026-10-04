"""
POST /audit — Slope Audit Endpoint
====================================

Orchestrates the full BioTerrace Sentinel assessment pipeline:

    1. Baseline FoS  → geotech.compute_fos (c_r = 0, bare soil)
    2. Prescriptions → bio_prescriptions.prescribe (species + c_r from region config)
    3. Post-FoS      → geotech.compute_fos (c_r = conservative species minimum)
    4. Risk labels   → geotech.classify_risk (baseline + post-intervention)
    5. Vernacular    → ollama_client.translate_to_vernacular (optional, graceful None)

Zero external calls are required for steps 1–4.
Step 5 requires local Ollama running on localhost:11434.
All five steps return a complete AuditReport even in fully offline mode
(vernacular_script = None when Ollama is unavailable).
"""

from fastapi import APIRouter, HTTPException, status

from app.engine.bio_prescriptions import prescribe
from app.engine.geotech import classify_risk, compute_fos, get_slope_band
from app.engine.ollama_client import translate_to_vernacular
from app.models.audit_report import AuditReport, RiskLevel
from app.models.slope_input import SlopeInput

router = APIRouter()


@router.post(
    "/",
    response_model=AuditReport,
    summary="Run a full slope stability audit",
    description=(
        "Accepts slope geometry and soil parameters, computes the Infinite Slope "
        "Factor of Safety, selects indigenous bio-engineering prescriptions, and "
        "optionally generates a vernacular farmer advisory via local Ollama. "
        "Fully offline-capable — no external network calls required for FoS computation."
    ),
)
async def slope_audit(payload: SlopeInput) -> AuditReport:
    """
    Full slope audit pipeline. See module docstring for step-by-step flow.
    """

    # ── Step 1: Baseline FoS (bare soil, no vegetation) ──────────────────────
    try:
        fos_baseline = compute_fos(
            theta_deg=payload.theta,
            z=payload.z,
            phi_deg=payload.phi,
            c_prime=payload.c_prime,
            gamma=payload.gamma,
            gamma_w=payload.gamma_w,
            h_w=payload.h_w,
            c_r=0.0,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Geotechnical computation error: {exc}",
        ) from exc

    # ── Step 2: Bio-engineering prescriptions + conservative c_r ─────────────
    prescription_result = prescribe(
        theta=payload.theta,
        h_w=payload.h_w,
        z=payload.z,
        region=payload.region,
    )

    # ── Step 3: Post-intervention FoS (with root cohesion) ───────────────────
    fos_post = compute_fos(
        theta_deg=payload.theta,
        z=payload.z,
        phi_deg=payload.phi,
        c_prime=payload.c_prime,
        gamma=payload.gamma,
        gamma_w=payload.gamma_w,
        h_w=payload.h_w,
        c_r=prescription_result.c_r_kpa,
    )

    # ── Step 4: Risk classification ───────────────────────────────────────────
    risk_baseline = classify_risk(fos_baseline)
    risk_post = classify_risk(fos_post)

    # Augment warning flags if post-intervention slope is still CRITICAL
    warning_flags = list(prescription_result.warning_flags)
    if risk_post == RiskLevel.CRITICAL:
        warning_flags.append(
            "Post-intervention FoS still CRITICAL — consider engineered drainage "
            "or structural intervention in addition to bio-engineering."
        )

    # ── Step 5: Vernacular advisory (Ollama, optional) ────────────────────────
    vernacular = await translate_to_vernacular(
        fos=round(fos_baseline, 3),
        risk_level=risk_baseline,
        prescriptions=prescription_result.prescriptions,
        region=payload.region,
        language=payload.language,
    )

    # ── Assemble and return report ────────────────────────────────────────────
    return AuditReport(
        fos_baseline=round(fos_baseline, 4),
        fos_post_intervention=round(fos_post, 4),
        fos_improvement=round(fos_post - fos_baseline, 4),
        risk_level=risk_baseline,
        risk_level_post=risk_post,
        slope_band=prescription_result.slope_band_label,
        prescriptions=prescription_result.prescriptions,
        vernacular_script=vernacular,
        region=payload.region,
        warning_flags=warning_flags,
    )
