#!/usr/bin/env python3
"""
Create the BioTerrace Sentinel ElevenLabs Conversational AI agent.

Run once before first deployment:
    cd backend
    python scripts/create_elevenlabs_agent.py

Reads ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID from .env (or environment).
Creates the agent via ElevenLabs API and writes ELEVENLABS_AGENT_ID back into .env.

Requirements: httpx, python-dotenv  (already in requirements.txt)
"""

import re
import sys
from pathlib import Path

import httpx
from dotenv import dotenv_values

# ── Paths ──────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent.parent          # repo root
ENV_FILE = ROOT / ".env"
CONVAI_CREATE = "https://api.elevenlabs.io/v1/convai/agents/create"

# ── Agent base config (system prompt is overridden per-audit at runtime) ───────

AGENT_NAME = "BioTerrace Slope Advisor"

BASE_SYSTEM_PROMPT = (
    "You are a slope safety field advisor for mountain farmers in the Himalaya, "
    "Andes, and East Africa. You speak the local language of the region. "
    "Keep every reply under two short sentences. "
    "Use simple farming language — no technical jargon. "
    "When a slope audit result is provided, refer to the Factor of Safety score "
    "and the recommended bio-engineering treatment."
)

FIRST_MESSAGE_EN = (
    "Hello! I am your slope safety advisor. "
    "You can ask me about your slope audit result or planting recommendations."
)

# The runtime code in voice.py overrides both prompt and first_message
# with region-specific Nepali / Spanish / Amharic versions per conversation.

AGENT_CONFIG = {
    "name": AGENT_NAME,
    "conversation_config": {
        "agent": {
            "prompt": {
                "prompt": BASE_SYSTEM_PROMPT,
                "llm": "gemini-1.5-flash",      # fast, cheap, multilingual
                "temperature": 0.5,
                "max_tokens": 120,              # keep replies short for low bandwidth
            },
            "first_message": FIRST_MESSAGE_EN,
            "language": "en",                  # overridden per-conversation at runtime
        },
        "tts": {
            "model_id": "eleven_multilingual_v2",
            # voice_id injected below from .env / ELEVENLABS_VOICE_ID
        },
        "asr": {
            "quality": "high",
            "provider": "elevenlabs",
            "user_input_audio_format": "pcm_16000",
        },
        "turn": {
            "turn_timeout": 7,
        },
        "conversation": {
            "max_duration_seconds": 300,
            "client_events": [
                "audio",
                "user_transcript",
                "agent_response",
                "interruption",
                "ping",
            ],
        },
    },
}


# ── .env helpers ───────────────────────────────────────────────────────────────

def load_env() -> dict[str, str]:
    """Load .env file if present, then overlay real env vars."""
    import os
    values = {}
    if ENV_FILE.exists():
        values.update({k: v for k, v in dotenv_values(ENV_FILE).items() if v})
    # Real env vars take precedence
    for key in ("ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID", "ELEVENLABS_AGENT_ID"):
        if os.environ.get(key):
            values[key] = os.environ[key]
    return values


def write_agent_id_to_env(agent_id: str) -> None:
    """
    Upsert ELEVENLABS_AGENT_ID in .env.
    Creates the file if it doesn't exist.
    """
    if ENV_FILE.exists():
        content = ENV_FILE.read_text(encoding="utf-8")
    else:
        content = ""

    pattern = r"^ELEVENLABS_AGENT_ID=.*$"
    new_line = f"ELEVENLABS_AGENT_ID={agent_id}"

    if re.search(pattern, content, flags=re.MULTILINE):
        content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
    else:
        content = content.rstrip("\n") + ("\n" if content else "") + new_line + "\n"

    ENV_FILE.write_text(content, encoding="utf-8")
    print(f"  Written to {ENV_FILE}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    env = load_env()

    # ── Validate credentials ───────────────────────────────────────────────────
    api_key = env.get("ELEVENLABS_API_KEY", "").strip()
    voice_id = env.get("ELEVENLABS_VOICE_ID", "").strip()

    if not api_key:
        print("ERROR: ELEVENLABS_API_KEY not found in .env or environment.")
        print(f"  Add it to {ENV_FILE}  →  ELEVENLABS_API_KEY=your_key_here")
        sys.exit(1)

    if not voice_id:
        print("WARNING: ELEVENLABS_VOICE_ID not set — agent will use your account default voice.")
        print(f"  You can add it later to {ENV_FILE}  →  ELEVENLABS_VOICE_ID=your_voice_id")
        print()

    # ── Check if agent already exists ─────────────────────────────────────────
    existing_id = env.get("ELEVENLABS_AGENT_ID", "").strip()
    if existing_id:
        print(f"ELEVENLABS_AGENT_ID already set: {existing_id}")
        answer = input("Create a new agent anyway? [y/N] ").strip().lower()
        if answer != "y":
            print("Keeping existing agent. Done.")
            sys.exit(0)

    # ── Inject voice_id into config ───────────────────────────────────────────
    config = AGENT_CONFIG.copy()
    if voice_id:
        config["conversation_config"]["tts"]["voice_id"] = voice_id  # type: ignore[index]

    # ── Call ElevenLabs API ───────────────────────────────────────────────────
    print(f"Creating agent '{AGENT_NAME}' via ElevenLabs API...")

    try:
        resp = httpx.post(
            CONVAI_CREATE,
            json=config,
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
    except httpx.RequestError as exc:
        print(f"ERROR: Network request failed — {exc}")
        sys.exit(1)

    if not resp.is_success:
        print(f"ERROR: ElevenLabs API returned HTTP {resp.status_code}")
        try:
            body = resp.json()
            print(f"  Detail: {body.get('detail', resp.text[:400])}")
        except Exception:
            print(f"  Body: {resp.text[:400]}")
        sys.exit(1)

    data = resp.json()
    agent_id: str = data.get("agent_id", "")

    if not agent_id:
        print("ERROR: Response did not contain agent_id.")
        print(f"  Full response: {data}")
        sys.exit(1)

    # ── Success ───────────────────────────────────────────────────────────────
    print()
    print("Agent created successfully!")
    print(f"  Agent name : {AGENT_NAME}")
    print(f"  Agent ID   : {agent_id}")
    print()
    print("Writing ELEVENLABS_AGENT_ID to .env...")
    write_agent_id_to_env(agent_id)

    print()
    print("Done. Next steps:")
    print("  1. Restart the backend  →  uvicorn main:app --reload")
    print("  2. Open the app and tap 'Talk to Slope Advisor' after running an audit.")
    print(f"  3. To edit the agent's base voice/LLM, visit:")
    print(f"     https://elevenlabs.io/app/conversational-ai/agents/{agent_id}")


if __name__ == "__main__":
    main()
