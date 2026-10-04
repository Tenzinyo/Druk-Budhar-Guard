# BioTerrace Sentinel — Pitch Notes

---

## Product Demo (60 seconds)

> *Speak naturally from these bullets. Each bullet ≈ 5–6 seconds.*

- "Every monsoon season, landslides kill hundreds and cut off mountain villages from food and healthcare — because farmers can't afford geotechnical engineers."
- "BioTerrace Sentinel puts a certified slope safety audit in a farmer's pocket — for free, offline, in their own language."
- "I open the app. I hold my phone against the slope face — the tilt meter reads the angle live."
- "I tap the Monsoon preset — worst-case groundwater. One tap: Run Audit."
- "In under two seconds, the app calculates the Factor of Safety using the infinite slope model — the same formula geotechnical engineers use."
- "This slope is CRITICAL. The app prescribes: plant Dendrocalamus bamboo at 50 cm depth, two paces between rows, along the contour."
- "I tap 'Hear Advisory' — Ollama writes the prescription in Nepali, ElevenLabs speaks it aloud. The farmer doesn't need to read."
- "The Road Bulletin tab shows whether the pass to market is open — scraped live via Bright Data, cached offline if there's no signal."
- "This replaces a $200,000 concrete wall with a $30 bamboo planting programme — validated by the World Bank and ICIMOD."
- "One phone. No engineer. No internet required. Saving lives and livelihoods at the edge of the world."

---

## Technical Walkthrough (60 seconds)

> *Speak to the architecture diagram as you go.*

- "The backend is a FastAPI Python service — fully air-gapped. No paid cloud LLM at runtime."
- "POST /audit runs the infinite slope FoS equation — cohesion, friction, groundwater depth, slope angle — in pure Python. Zero ML inference needed for the core safety calculation."
- "A rule-based prescriber maps the FoS band and slope angle to the correct bio-engineering intervention: vetiver lines, live fascines, or bamboo crib walls."
- "Ollama runs llama3.2 locally — it formats the prescription as a vernacular script in the user's language. No API call, no cost, no connectivity."
- "ElevenLabs Multilingual v2 synthesizes the audio. If ElevenLabs is unavailable, a pre-cached MP3 template plays. If that's missing, the text script displays. Three-tier fallback — always delivers."
- "Road bulletin uses Bright Data Web Unlocker to scrape Google News for closure keywords — landslide, blocked, rockfall — then parses HTML with regex and writes results to SQLite. Falls back to fixtures."
- "The frontend is a React PWA wrapped in Capacitor. The accelerometer reads real slope angle via arcsin of the gravity vector. IndexedDB caches the last audit offline."
- "215 passing pytest tests, 80%+ coverage across all modules."
- "Swap the region JSON — Himalaya, Andes, East Africa — zero code change. The same engine works globally."
- "Total runtime cost: zero dollars. Bright Data credit, ElevenLabs Creator tier, local Ollama — all within free allocations."

---

## Architecture (one-page reference)

```
FARMER'S PHONE
  |
  | HTTPS REST (or offline IndexedDB cache)
  v
+---------------------------------------------+
|  React PWA + Capacitor (iOS / Android)      |
|                                             |
|  TiltMeter  ← @capacitor/motion arcsin(ay)  |
|  AuditForm  → POST /audit                   |
|  VoicePlayer → POST /voice/synthesize       |
|  RoadBulletin → GET /road-bulletin/         |
|  ConvAI     → GET /voice/convai-url         |
+---------------------------------------------+
  |
  v
+---------------------------------------------+
|  FastAPI Backend                            |
|                                             |
|  /audit                                     |
|   geotech.py        Infinite Slope FoS      |
|   bio_prescriptions.py  Rule-based species  |
|   ollama_client.py  Local LLM → vernacular  |
|                                             |
|  /road-bulletin                             |
|   Bright Data Web Unlocker (live)           |
|   → SQLite edge cache (6 h TTL)             |
|   → JSON fixtures (always available)        |
|                                             |
|  /voice                                     |
|   ElevenLabs TTS (live)                     |
|   → pre-cached MP3 template                 |
|   → plain text script                       |
+---------------------------------------------+
  |                    |
  v                    v
Ollama llama3.2    SQLite + fixtures
(on-device LLM)    (edge data store)
```

### Key numbers
| Metric | Value |
|---|---|
| Offline boot time | < 1 s (no network needed) |
| Audit latency (offline) | < 200 ms |
| Audit latency (with Ollama) | 3–8 s |
| Voice synthesis (ElevenLabs) | 2–5 s |
| Test suite | 215 tests, 80%+ coverage |
| Runtime cloud cost | $0.00 |
| Regions supported | himalaya, andes, east_africa |
| Languages | 10 (Hindi, Nepali, Dzongkha, English, Spanish, Quechua, Portuguese, Amharic, Swahili, French) |
