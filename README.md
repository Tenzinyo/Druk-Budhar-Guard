# BioTerrace Sentinel (Druk-Bhudhar Guard)

**Global AI Hack Nation — Challenge 4: Small AI for Development**
*World Bank Track | MIT Club of Germany & MITCNC Collaboration*

---

## What It Does

An **offline-capable edge geotechnical slope auditor** and **nature-based bio-engineering prescriber** for mountain communities in Bhutan, Nepal, and globally replicable highland regions.

It replaces fragile, multi-million dollar concrete retaining walls with **indigenous vegetative root stabilization** (Vetiver grass, local bamboo, brush-layering, live fascines) — validated by World Bank and ICIMOD geotechnical research — and delivers prescriptions as spoken audio notes in local languages to illiterate farmers.

---

## Challenge 4 Compliance

| Constraint | Solution |
|---|---|
| Offline-capable | FastAPI engine + SQLite edge cache runs fully air-gapped |
| Zero paid cloud LLM | Local Ollama `llama3.2:1b` for all reasoning and translation |
| Cheap devices | Lightweight REST API + PWA frontend (Lovable Pro) |
| Local languages | Ollama formats Hindi/Nepali scripts; ElevenLabs synthesizes audio |
| Real-world data | Bright Data Web Unlocker → SQLite edge cache with circuit breaker |
| Global replicability | JSON region configs swap species/parameters with zero code change |
| Zero additional spend | Bright Data ($300 credit), ElevenLabs Creator, Lovable Pro — $0.00 overage |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  FastAPI Backend (fully offline-capable)            │
│                                                     │
│  POST /audit                                        │
│   └── geotech.py        Infinite Slope FoS engine  │
│   └── bio_prescriptions.py  Rule-based prescriber  │
│   └── ollama_client.py  Local LLM vernacular text  │
│                                                     │
│  GET /road-bulletin                                 │
│   └── road_bulletin.py  Bright Data + SQLite cache │
│                                                     │
│  POST /voice                                        │
│   └── voice.py          ElevenLabs + offline cache │
└─────────────────────────────────────────────────────┘
         ↕ REST / JSON
┌─────────────────────────────────────────────────────┐
│  Lovable Pro PWA Frontend                          │
│  Tilt-meter simulator · Offline/online toggle      │
│  Audio playback · Low-literacy physical units      │
└─────────────────────────────────────────────────────┘
```

---

## Geotechnical Model

**Infinite Slope Factor of Safety with Root Tensile Cohesion**

```
FoS = [c' + c_r + (γ·z − γ_w·h_w)·cos²θ·tan φ]
      ─────────────────────────────────────────────
              γ·z·sin θ·cos θ
```

| Parameter | Description |
|---|---|
| `c'` | Effective soil cohesion (kPa) |
| `c_r` | Root tensile cohesion: Vetiver 5–18 kPa, Dendrocalamus 10–18 kPa |
| `γ` | Bulk unit weight of soil (kN/m³) |
| `γ_w` | Unit weight of water (9.81 kN/m³) |
| `z` | Depth to failure plane (m) |
| `h_w` | Height of groundwater above failure plane (m) |
| `θ` | Slope angle (degrees) |
| `φ` | Internal friction angle (degrees) |

**Sources:** Das — *Principles of Geotechnical Engineering*; ICIMOD 2011; Nepal DoR Bio-engineering Manual 2013; World Bank DRRIP Nepal 2019.

---

## Bio-Engineering Prescription Rules

| Slope Band | Primary Intervention | Species |
|---|---|---|
| < 25° | Contour vegetative grass lines | Vetiver (Khas Khas), Amliso |
| 25°–40° | Live fascines, brush layering, contour diversion drains | Vetiver + Dendrocalamus |
| > 40° | Bamboo live crib walls, vegetative palisades, interceptor drainage | Dendrocalamus bamboo |

---

## Global Replicability

Swap the `region` parameter to deploy in a new highland context:

| Region Key | Pilot Area | Focus Species |
|---|---|---|
| `himalaya` | Bhutan & Nepal | Vetiver, Amliso, Dendrocalamus |
| `andes` | Andean Altiplano | Ichu grass, Polylepis (Queñoa) |
| `east_africa` | Ethiopian Highlands | Teff bunds, Sesbania |

---

## Project Structure

```
Druk-Budhar-Guard/
├── .env.example
├── .gitignore
├── README.md
└── backend/
    ├── requirements.txt
    ├── main.py
    └── app/
        ├── config/
        │   ├── settings.py
        │   └── regions/
        │       ├── himalaya.json
        │       ├── andes.json
        │       └── east_africa.json
        ├── engine/
        │   ├── geotech.py            ✅ (Phase 2)
        │   ├── bio_prescriptions.py  ✅ (Phase 2)
        │   └── ollama_client.py      (Phase 5)
        ├── models/
        │   ├── slope_input.py
        │   └── audit_report.py
        ├── routers/
        │   ├── audit.py              ✅ (Phase 3)
        │   ├── road_bulletin.py      ✅ (Phase 4)
        │   └── voice.py              ✅ (Phase 5)
        ├── db/
        │   ├── database.py           (Phase 4)
        │   └── fixtures/
        │       ├── bhutan_roads.json (Phase 4)
        │       └── nepal_roads.json  (Phase 4)
        └── tests/
            ├── conftest.py           (Phase 3)
            ├── test_geotech.py       (Phase 2)
            ├── test_bio_prescriptions.py (Phase 2)
            ├── test_audit_router.py  (Phase 3)
            ├── test_road_bulletin.py (Phase 4)
            ├── test_voice.py         (Phase 5)
            └── test_region_configs.py (Phase 6)
```

---

## Build Status

| Phase | Description | Status |
|---|---|---|
| Phase 1 | Foundation scaffolding, models, region configs, settings | ✅ Complete |
| Phase 2 | Geotechnical FoS engine + bio-engineering prescriber + Layer 1 tests | ✅ Complete |
| Phase 3 | FastAPI `/audit` endpoint + integration tests | ✅ Complete |
| Phase 4 | Bright Data road bulletin + SQLite edge cache | ✅ Complete |
| Phase 5 | Ollama vernacular client + ElevenLabs voice pipeline | ✅ Complete |
| Phase 6 | Full integration, docker-compose, coverage report | ✅ Complete |
| Phase 7 | Lovable Pro PWA frontend | Pending |

---

## Quickstart (Local Development)

```bash
# 1. Create virtual environment and install dependencies
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure environment (Phase 4/5 live features only — not needed for tests)
cp ../.env.example ../.env
# Edit .env: add BRIGHTDATA_* and ELEVENLABS_* keys when ready for live demo

# 3. Start Ollama (separate terminal — needed for vernacular script generation)
ollama pull llama3.2:1b
ollama serve

# 4. Run the API
uvicorn main:app --reload --port 8000
# Interactive docs: http://localhost:8000/docs

# 5. Run all tests (no .env or Ollama required — all external calls mocked)
pytest tests/ -v --tb=short --cov=app --cov-report=term-missing
```

## Docker Deployment

```bash
# 1. Build and start all services (FastAPI + Ollama)
docker compose up --build

# 2. Pull the LLM model (one-time, requires connectivity)
docker compose exec ollama ollama pull llama3.2:1b

# 3. Pre-generate offline audio templates (one-time, while connected)
for region in himalaya andes east_africa; do
  for risk in STABLE MARGINAL CRITICAL; do
    curl -s -X POST http://localhost:8000/voice/synthesize \
      -H "Content-Type: application/json" \
      -d "{\"script\":\"Advisory for ${region}: ${risk} slope detected.\",\"region\":\"${region}\",\"risk_level\":\"${risk}\"}" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('source','?'), d.get('audio_endpoint',''))"
  done
done
# Copy generated *.mp3 from audio_cache/ to audio_cache/templates/

# 4. API fully offline — disconnect network and test
curl http://localhost:8000/health
curl "http://localhost:8000/road-bulletin/"   # → data_source: "fixture"
```

## Test Coverage

```bash
cd backend
pytest tests/ -v --tb=short --cov=app --cov-report=term-missing --cov-fail-under=80
```

Expected coverage targets:
| Module | Target |
|---|---|
| `app/engine/geotech.py` | 100% |
| `app/engine/bio_prescriptions.py` | 100% |
| `app/engine/ollama_client.py` | 90%+ |
| `app/routers/audit.py` | 90%+ |
| `app/routers/road_bulletin.py` | 85%+ |
| `app/routers/voice.py` | 85%+ |
| `app/db/database.py` | 80%+ |

---

## Data Sources & Citations

- ICIMOD (2011). *Bio-engineering for Slope Protection and Erosion Control in the Hindu Kush Himalayas.*
- Nepal Department of Roads (2013). *Bio-engineering Manual for Road Slope Stabilisation.*
- World Bank (2019). *Nepal Disaster Risk Reduction and Resilience Programme (DRRIP).*
- World Bank (2021). *Mountain Infrastructure Resilience Programme.*
- Das, B.M. *Principles of Geotechnical Engineering*, 9th Ed.
- FAO (2017). *Watershed Management in the Andes.*
- World Bank Ethiopia SLMP-II (2018). *Sustainable Land Management Programme.*
