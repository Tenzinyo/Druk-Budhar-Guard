# BioTerrace Sentinel (Druk-Bhudhar Guard)

**Global AI Hack Nation — Challenge 4: Small AI for Development**
*World Bank Track | MIT Club of Germany & MITCNC Collaboration*

---

## What It Does

An **offline-capable edge geotechnical slope auditor** and **nature-based bio-engineering prescriber** for mountain communities in Bhutan, Nepal, and globally replicable highland regions.

It replaces fragile, multi-million dollar concrete retaining walls with **indigenous vegetative root stabilization** (Vetiver grass, local bamboo, brush-layering, live fascines) — validated by World Bank and ICIMOD geotechnical research — and delivers prescriptions as spoken audio notes in local languages to illiterate farmers.

### Example: A Farmer in Sindhupalchok, Nepal

Parbati is a 52-year-old rice farmer in a hillside village above the Melamchi river. After the monsoon, a section of the terrace wall above her paddy is cracking and bulging. The nearest road is 4 hours away. There is no geotechnical engineer within 200 km.

1. **She opens BioTerrace Sentinel** on her Android phone — no internet needed.
2. **She holds the phone flat against the slope face.** The tilt meter reads 38° live from the accelerometer.
3. **She taps "Saturated / Monsoon"** — the app sets groundwater to full depth, reflecting the waterlogged soil after heavy rain.
4. **She taps "Run Slope Audit".** In under 2 seconds, the engine calculates FoS = 0.81 — **CRITICAL**.
5. **She taps "Hear Advisory in Nepali".** Ollama writes the prescription in Nepali script; ElevenLabs speaks it aloud:
   > *"भिरालो ढल्ने खतरामा छ। अहिले नै Dendrocalamus बाँस एक हात गहिरो, दुई पाइला बीच-बीचमा लाइन लगाउनुहोस्।"*
   > *(The slope is at risk of collapse. Plant Dendrocalamus bamboo now — one forearm deep, two paces between rows along the contour.)*
6. **She checks the Roads tab.** The Melamchi–Kathmandu pass shows **RESTRICTED** — cached 3 hours ago from a Bright Data scrape. She knows not to attempt the journey today.
7. **She calls the Slope Advisor** (ConvAI button) to ask follow-up questions — the ElevenLabs agent responds in Nepali.

Total cost to Parbati: **zero**. Total cost to deploy: **zero additional cloud spend**.

---

## Challenge 4 Compliance

| Constraint | Solution |
|---|---|
| Offline-capable | FastAPI engine + SQLite edge cache runs fully air-gapped |
| Zero paid cloud LLM | Local Ollama `llama3.2:1b` for all reasoning and translation |
| Cheap devices | Lightweight REST API + React PWA + Capacitor native app |
| Local languages | Ollama formats Hindi/Nepali scripts; ElevenLabs synthesizes audio |
| Real-world data | Bright Data Web Unlocker → SQLite edge cache with circuit breaker |
| Global replicability | JSON region configs swap species/parameters with zero code change |
| Zero additional spend | Bright Data ($300 credit), ElevenLabs Creator — $0.00 overage |
| Native mobile | Capacitor wraps PWA into native Android APK + iOS IPA |
| Real tilt meter | `@capacitor/motion` reads device accelerometer for slope angle |

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
│  React + Vite PWA Frontend                         │
│  ├── Web browser (PWA, installable)                │
│  ├── Android native APK  (Capacitor v6)            │
│  └── iOS native IPA      (Capacitor v6)            │
│                                                     │
│  TiltMeter — SVG gauge + real accelerometer        │
│  AuditForm — physical unit hints for low literacy  │
│  RoadBulletin — pass status cards + data_source    │
│  VoicePlayer — offline audio playback              │
│  ConnectivityBadge — live online/cached/offline    │
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
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── .coveragerc
│   ├── main.py
│   └── app/
│       ├── config/
│       │   ├── settings.py
│       │   └── regions/
│       │       ├── himalaya.json
│       │       ├── andes.json
│       │       └── east_africa.json
│       ├── engine/
│       │   ├── geotech.py            ✅
│       │   ├── bio_prescriptions.py  ✅
│       │   └── ollama_client.py      ✅
│       ├── models/
│       │   ├── slope_input.py
│       │   └── audit_report.py
│       ├── routers/
│       │   ├── audit.py              ✅
│       │   ├── road_bulletin.py      ✅
│       │   └── voice.py              ✅
│       ├── db/
│       │   ├── database.py           ✅
│       │   └── fixtures/
│       │       ├── bhutan_roads.json
│       │       └── nepal_roads.json
│       └── tests/
│           ├── conftest.py
│           ├── test_geotech.py             (20 tests)
│           ├── test_bio_prescriptions.py   (28 tests)
│           ├── test_audit_router.py        (37 tests)
│           ├── test_road_bulletin.py       (35 tests)
│           ├── test_voice.py               (38 tests)
│           └── test_region_configs.py      (57 tests)
└── frontend/
    ├── index.html
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── capacitor.config.ts
    └── src/
        ├── index.tsx
        ├── index.css
        ├── App.tsx                   (in progress)
        └── lib/
        │   ├── api.ts                ✅  TypeScript API client
        │   ├── offlineStorage.ts     ✅  IndexedDB cache layer
        │   └── deviceSensors.ts      ✅  Accelerometer + network + haptics
        └── components/
            ├── ConnectivityBadge.tsx (in progress)
            ├── TiltMeter.tsx         (in progress)
            ├── AuditForm.tsx         (in progress)
            ├── AuditResult.tsx       (in progress)
            ├── RoadBulletin.tsx      (in progress)
            └── VoicePlayer.tsx       (in progress)
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
| Phase 7 | React PWA + Capacitor native app (iOS/Android) | In Progress |

---

## Quickstart (Local Development)

### Backend

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

### Frontend — Web / PWA

```bash
cd frontend
npm install
npm run dev         # → http://localhost:5173
# Open in Chrome → "Install app" in address bar to install as PWA
```

### Frontend — Native Android

> Prerequisites: Android Studio + JDK 17 installed.

```bash
cd frontend
npm run build              # compile TypeScript + Vite bundle → dist/
npx cap add android        # one-time: scaffold android/ directory
npm run cap:android        # sync + open Android Studio
# In Android Studio: Run > Run 'app' (or Build > Generate Signed APK)
```

For live-reload on a physical device:

```bash
npm run cap:run:android    # bundles, pushes to device, hot-reloads on save
```

### Frontend — Native iOS

> Prerequisites: Xcode 15+ on macOS, Apple Developer account for device builds.

```bash
cd frontend
npm run build
npx cap add ios            # one-time: scaffold ios/ directory
npm run cap:ios            # sync + open Xcode
# In Xcode: select your device or simulator → press Run (▶)
```

### When to Add .env API Keys

| Key | When needed |
|---|---|
| `BRIGHTDATA_*` | Phase 4 live scraping (tests pass without it) |
| `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID` | Phase 5 live audio (falls back to template/text offline) |
| `OLLAMA_HOST` | Only if Ollama runs on a non-default host |

Tests run fully without any `.env` file — all external calls are mocked.

---

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

---

## Test Coverage

```bash
cd backend
pytest tests/ -v --tb=short --cov=app --cov-report=term-missing --cov-fail-under=80
```

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

## Frontend — Key Design Decisions

### Two-layer Offline Guarantee
| Layer | Technology | Scope |
|---|---|---|
| Browser/App | IndexedDB (`offlineStorage.ts`) | Last audit + bulletin per region |
| Backend | SQLite + JSON fixtures | Road data, audio templates |

### Native Accelerometer (Real Tilt Meter)
Farmers hold the phone flat against the slope face. `@capacitor/motion` reads the device accelerometer and derives slope angle via `θ = arcsin(|ay| / g)`. Falls back to a manual slider on desktop browsers.

### Circuit Breaker Labels
Every API response includes a `data_source` / `source` field (`live | cache | fixture | cache | template | text_only`). The `ConnectivityBadge` shows this to farmers so they know how fresh the data is.

### Low-Literacy UX
All prescription spacing and depth values are expressed in physical body-unit strings (`"two paces between rows / ~1.5 m"`, `"one forearm deep / ~40 cm"`), not just metric numbers.

---

## Data Sources & Citations

- ICIMOD (2011). *Bio-engineering for Slope Protection and Erosion Control in the Hindu Kush Himalayas.*
- Nepal Department of Roads (2013). *Bio-engineering Manual for Road Slope Stabilisation.*
- World Bank (2019). *Nepal Disaster Risk Reduction and Resilience Programme (DRRIP).*
- World Bank (2021). *Mountain Infrastructure Resilience Programme.*
- Das, B.M. *Principles of Geotechnical Engineering*, 9th Ed.
- FAO (2017). *Watershed Management in the Andes.*
- World Bank Ethiopia SLMP-II (2018). *Sustainable Land Management Programme.*
