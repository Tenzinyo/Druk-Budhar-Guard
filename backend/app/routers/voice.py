"""
POST /voice/synthesize — ElevenLabs Multilingual Voice Synthesis
================================================================

Converts a vernacular advisory script (produced by Ollama via /audit) into
a downloadable MP3 audio note for farmers with low literacy.

Three-tier offline strategy
-----------------------------
    Tier 0  Audio already in local cache → serve immediately, no API call
    Tier 1  ElevenLabs Multilingual v2 API
              → requires connectivity + ELEVENLABS_API_KEY in .env
              → audio saved to app/audio_cache/{key}.mp3 after synthesis
    Tier 2  Pre-generated regional template
              → app/audio_cache/templates/{region}_{risk_level_lower}.mp3
              → produced offline during deployment (one-time ElevenLabs call)
              → generic advisory phrase for each region × risk-level combination
    Tier 3  Text-only fallback
              → audio_available=False; frontend displays text advisory instead

ElevenLabs API details
-----------------------
    Model   : eleven_multilingual_v2  (Hindi, Nepali, Spanish, Amharic, 30+ languages)
    Endpoint: POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}
    Auth    : xi-api-key header
    Input   : max 140 characters (fits within Creator tier per-request cost)
    Output  : audio/mpeg (MP3 bytes)

Audio cache
-----------
    Cache key : SHA-256(script)[:16] — deterministic, collision-resistant
    Cache dir : app/audio_cache/  (gitignored *.mp3; directory tracked via .gitkeep)
    Templates : app/audio_cache/templates/{region}_{risk_level_lower}.mp3

Template pre-generation
-----------------------
    To pre-generate offline templates before field deployment:
    POST /voice/synthesize for each (region, risk_level) combination while
    connectivity is available. The resulting files are copied into templates/.
    The app then serves these files in fully air-gapped mode.
"""

import hashlib
from pathlib import Path
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.config.settings import settings

router = APIRouter()

# ── ElevenLabs constants ──────────────────────────────────────────────────────
_ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
_MODEL_ID = "eleven_multilingual_v2"


# ── Request / Response models ─────────────────────────────────────────────────

class VoiceSynthesisRequest(BaseModel):
    script: str = Field(
        ...,
        min_length=1,
        max_length=140,
        description=(
            "Vernacular advisory text to synthesise. Max 140 characters. "
            "Produced by POST /audit → vernacular_script field."
        ),
    )
    region: str = Field(
        default="himalaya",
        description="Region key — used for template fallback selection.",
    )
    risk_level: str = Field(
        default="MARGINAL",
        description="Risk level (STABLE / MARGINAL / CRITICAL) — used for template fallback.",
    )


class VoiceSynthesisResponse(BaseModel):
    script: str
    cache_key: str
    audio_available: bool
    source: Literal["cache", "elevenlabs", "template", "text_only"]
    audio_endpoint: Optional[str] = Field(
        default=None,
        description="Relative URL to retrieve the MP3 audio file.",
    )


# ── Cache / path helpers ──────────────────────────────────────────────────────

def _cache_key(script: str) -> str:
    """16-char hex digest of the script — used as the MP3 filename stem."""
    return hashlib.sha256(script.encode("utf-8")).hexdigest()[:16]


def _cache_path(key: str) -> Path:
    return settings.audio_cache_dir / f"{key}.mp3"


def _template_path(region: str, risk_level: str) -> Optional[Path]:
    """
    Returns the path to a pre-generated template MP3, or None if absent.

    Template naming convention: {region}_{risk_level_lower}.mp3
    Examples:
        himalaya_critical.mp3  — Nepali/Hindi: "slope is failing, plant bamboo now"
        himalaya_marginal.mp3  — Nepali/Hindi: "slope needs treatment soon"
        himalaya_stable.mp3    — Nepali/Hindi: "slope is stable, continue monitoring"
        andes_critical.mp3     — Spanish/Quechua equivalent
        east_africa_critical.mp3 — Amharic/Swahili equivalent
    """
    filename = f"{region}_{risk_level.lower()}.mp3"
    path = settings.audio_cache_dir / "templates" / filename
    return path if path.exists() else None


# ── ElevenLabs API call ───────────────────────────────────────────────────────

async def _call_elevenlabs(script: str) -> Optional[bytes]:
    """
    Call ElevenLabs Multilingual v2 TTS API.

    Returns raw MP3 bytes on success, None on any error or missing credentials.
    Graceful None return is not an error — the caller falls through to next tier.
    """
    api_key = settings.elevenlabs_api_key
    voice_id = settings.elevenlabs_voice_id
    if not api_key or not voice_id:
        return None  # Credentials absent → skip immediately, no error raised

    url = _ELEVENLABS_TTS_URL.format(voice_id=voice_id)
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    body = {
        "text": script,
        "model_id": _MODEL_ID,
        "voice_settings": {
            "stability": 0.55,           # Moderate stability for natural rural delivery
            "similarity_boost": 0.75,    # High similarity to voice clone
        },
    }

    try:
        async with httpx.AsyncClient(timeout=settings.elevenlabs_timeout_s) as client:
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            return resp.content  # raw MP3 bytes
    except Exception:
        return None


# ── Synthesis endpoint ────────────────────────────────────────────────────────

@router.post(
    "/synthesize",
    response_model=VoiceSynthesisResponse,
    summary="Synthesize a vernacular voice advisory note",
    description=(
        "Accepts a short vernacular script (≤ 140 chars) and returns an MP3 audio note. "
        "Three-tier fallback: local cache → ElevenLabs live → pre-cached template → text-only. "
        "Fully offline-capable when templates are pre-generated."
    ),
)
async def synthesize_voice(payload: VoiceSynthesisRequest) -> VoiceSynthesisResponse:
    key = _cache_key(payload.script)

    # ── Tier 0: Already in cache ──────────────────────────────────────────────
    if _cache_path(key).exists():
        return VoiceSynthesisResponse(
            script=payload.script,
            cache_key=key,
            audio_available=True,
            source="cache",
            audio_endpoint=f"/voice/audio/{key}",
        )

    # ── Tier 1: ElevenLabs live synthesis ─────────────────────────────────────
    audio_bytes = await _call_elevenlabs(payload.script)
    if audio_bytes:
        settings.audio_cache_dir.mkdir(parents=True, exist_ok=True)
        _cache_path(key).write_bytes(audio_bytes)
        return VoiceSynthesisResponse(
            script=payload.script,
            cache_key=key,
            audio_available=True,
            source="elevenlabs",
            audio_endpoint=f"/voice/audio/{key}",
        )

    # ── Tier 2: Pre-cached regional template ──────────────────────────────────
    template = _template_path(payload.region, payload.risk_level)
    if template:
        template_key = _cache_key(f"template:{payload.region}:{payload.risk_level.upper()}")
        return VoiceSynthesisResponse(
            script=payload.script,
            cache_key=template_key,
            audio_available=True,
            source="template",
            audio_endpoint=(
                f"/voice/audio/template/{payload.region}/{payload.risk_level.lower()}"
            ),
        )

    # ── Tier 3: Text-only ─────────────────────────────────────────────────────
    return VoiceSynthesisResponse(
        script=payload.script,
        cache_key=key,
        audio_available=False,
        source="text_only",
        audio_endpoint=None,
    )


# ── Audio retrieval endpoints ─────────────────────────────────────────────────

@router.get(
    "/audio/template/{region}/{risk_level}",
    summary="Stream a pre-cached regional template audio note",
    response_class=FileResponse,
)
async def get_template_audio(region: str, risk_level: str) -> FileResponse:
    """
    Returns a pre-generated template MP3 for the given region and risk level.
    Template files are produced offline during deployment.
    This endpoint is registered BEFORE /audio/{cache_key} so FastAPI routes
    the literal path segment 'template' correctly.
    """
    template = _template_path(region, risk_level)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No pre-cached template for region='{region}', "
                f"risk_level='{risk_level}'. "
                "Generate via POST /voice/synthesize while connected."
            ),
        )
    return FileResponse(
        path=str(template),
        media_type="audio/mpeg",
        filename=f"{region}_{risk_level.lower()}.mp3",
    )


@router.get(
    "/audio/{cache_key}",
    summary="Stream a synthesized and cached audio note",
    response_class=FileResponse,
)
async def get_cached_audio(cache_key: str) -> FileResponse:
    """
    Returns the cached MP3 for the given cache key.
    Keys are 16-char hex strings returned by POST /voice/synthesize.
    """
    audio_path = _cache_path(cache_key)
    if not audio_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Audio not found for cache_key='{cache_key}'. "
                "Re-synthesize via POST /voice/synthesize."
            ),
        )
    return FileResponse(
        path=str(audio_path),
        media_type="audio/mpeg",
        filename=f"{cache_key}.mp3",
    )
