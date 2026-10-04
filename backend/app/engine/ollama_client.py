"""
Local Ollama Vernacular Translation Client
==========================================

Calls the on-device Ollama API to convert a deterministic geotechnical
diagnosis into a short conversational script in the farmer's local language.

Design principles
-----------------
- Zero paid cloud LLM: communicates exclusively with localhost Ollama.
- Graceful degradation: returns None on any error (network, timeout, model
  not loaded). The audit endpoint continues to function fully offline.
- Output target: < 140 characters to fit within ElevenLabs synthesis limits.
- Temperature 0.3 for near-deterministic, consistent field messaging.

Supported language targets (from region config)
------------------------------------------------
    himalaya     → Nepali (ne) / Hindi (hi)
    andes        → Spanish (es) / Quechua (qu)
    east_africa  → Amharic (am) / Swahili (sw)
"""

from typing import Optional

import httpx

from app.config.settings import settings
from app.models.audit_report import Prescription, RiskLevel

# Maps region key → primary language name for the Ollama prompt
_REGION_LANGUAGE: dict[str, str] = {
    "himalaya": "Nepali",
    "andes": "Spanish",
    "east_africa": "Amharic",
}

# Risk level → urgency phrase (English template, LLM translates)
_RISK_URGENCY: dict[RiskLevel, str] = {
    RiskLevel.CRITICAL: "This slope is at risk of immediate collapse.",
    RiskLevel.MARGINAL: "This slope needs treatment soon.",
    RiskLevel.STABLE: "This slope is safe but should be monitored.",
}


def _build_prompt(
    fos: float,
    risk_level: RiskLevel,
    prescriptions: list[Prescription],
    region: str,
    language: str = "",
) -> str:
    """
    Build a concise Ollama prompt targeting < 140 character output.

    The prompt instructs the model to produce a single plain-language
    sentence in the local language — suitable for ElevenLabs audio synthesis
    and audible to a farmer in a noisy field environment.
    """
    language = language or _REGION_LANGUAGE.get(region, "Hindi")
    urgency = _RISK_URGENCY.get(risk_level, "Action is needed.")

    top_method = prescriptions[0].method if prescriptions else "vegetative planting"
    top_species = prescriptions[0].species[0] if (prescriptions and prescriptions[0].species) else "local grass"

    return (
        f"You are an agricultural extension officer speaking to a farmer. "
        f"Write exactly ONE sentence in {language} (under 130 characters). "
        f"The sentence must: (1) warn about slope safety score {fos:.2f}, "
        f"(2) state '{urgency}', "
        f"(3) recommend '{top_method}' using '{top_species}'. "
        f"Use only simple spoken words. No technical jargon. Output only the sentence."
    )


async def translate_to_vernacular(
    fos: float,
    risk_level: RiskLevel,
    prescriptions: list[Prescription],
    region: str,
    language: str = "",
) -> Optional[str]:
    """
    Generate a vernacular advisory sentence via local Ollama.

    Parameters
    ----------
    fos : float
        Baseline Factor of Safety.
    risk_level : RiskLevel
        Classified risk level (STABLE / MARGINAL / CRITICAL).
    prescriptions : list[Prescription]
        Ordered prescription list from bio_prescriptions.py.
    region : str
        Region key for language selection.

    Returns
    -------
    str or None
        Translated sentence, or None if Ollama is unavailable.
        A None return is not an error — the audit report remains complete.
    """
    try:
        prompt = _build_prompt(fos, risk_level, prescriptions, region, language)

        async with httpx.AsyncClient(timeout=settings.ollama_timeout_s) as client:
            response = await client.post(
                f"{settings.ollama_host}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": 80,   # ~130 chars; keeps within ElevenLabs limit
                        "temperature": 0.3,  # near-deterministic for field consistency
                    },
                },
            )
            response.raise_for_status()
            text = response.json().get("response", "").strip()
            return text if text else None

    except Exception:
        # Graceful degradation: Ollama not running, model not loaded, or offline.
        # The audit report is complete without the vernacular field.
        return None
