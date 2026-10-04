from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables / .env file.
    All external service credentials are optional at import time so the
    deterministic engine boots fully offline without any keys present.
    """

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Local Ollama (zero-cost, runs on-device) ---
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:latest"
    ollama_timeout_s: float = 30.0

    # --- ElevenLabs Creator Tier ---
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    elevenlabs_agent_id: str = ""
    elevenlabs_timeout_s: float = 20.0

    # --- Bright Data Web Unlocker API ---
    brightdata_api_key: str = ""
    brightdata_zone: str = "datacenter_proxy1_himalagri"
    brightdata_timeout_s: float = 15.0

    # --- App ---
    default_region: str = "himalaya"
    db_path: str = "app/db/road_cache.db"
    fixtures_dir: Path = Path(__file__).parent.parent / "db" / "fixtures"
    regions_dir: Path = Path(__file__).parent / "regions"
    audio_cache_dir: Path = Path(__file__).parent.parent / "audio_cache"


settings = Settings()
