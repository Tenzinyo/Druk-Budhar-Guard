from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.db.database import init_db, purge_stale_bulletins
from app.routers import audit, road_bulletin, voice


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup tasks (executed once before the app begins serving requests):
      1. Initialise SQLite edge cache schema
      2. Purge road bulletin records older than 48 h
      3. Ensure audio cache directories exist for voice synthesis
    """
    await init_db()
    await purge_stale_bulletins(max_age_hours=48.0)
    settings.audio_cache_dir.mkdir(parents=True, exist_ok=True)
    (settings.audio_cache_dir / "templates").mkdir(parents=True, exist_ok=True)
    yield
    # Shutdown: nothing required — SQLite and filesystem close automatically


app = FastAPI(
    title="BioTerrace Sentinel (Druk-Bhudhar Guard)",
    description=(
        "Offline-capable edge geotechnical slope auditor and "
        "nature-based bio-engineering prescriber for mountain communities. "
        "Challenge 4: Small AI for Development — World Bank / MIT Hackathon."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audit.router,         prefix="/audit",          tags=["Slope Audit"])
app.include_router(road_bulletin.router, prefix="/road-bulletin",  tags=["Road Bulletin"])
app.include_router(voice.router,         prefix="/voice",          tags=["Voice"])


@app.get("/health", tags=["Health"])
def health_check():
    """Liveness probe — returns immediately with no external calls."""
    return {"status": "ok", "service": "BioTerrace Sentinel", "version": "1.0.0"}
