# Edge Brain (FastAPI)

The hybrid "brain" that does everything the K10 can't: STT, TTS, OCR, vision, mood, a local LLM,
a semantic cache, geolocation, recording, ads, and an optional **Claude-desktop bridge**. Runs on
your PC (or a mini-PC / Jetson / the Ionity AI-M board). **No cloud, no API keys required.**

## Run

```bash
./scripts/setup.sh            # Windows: .\scripts\setup.ps1
source .venv/bin/activate     # Windows: .\.venv\Scripts\Activate.ps1
python -m app.main            # serves ws://0.0.0.0:8765/device + REST /api/*
```

It **boots immediately** with graceful fallbacks. Turn on real intelligence as you like:

| Capability | Enable it |
|---|---|
| Semantic cache (good) | `pip install sentence-transformers` (else hashing fallback works now) |
| Local LLM | `ollama serve` + `ollama pull llama3.2` |
| Speech-to-text | `pip install faster-whisper` |
| OCR | `pip install paddleocr` (or `pytesseract` + Tesseract) |
| Vision (faces/QR) | `pip install opencv-python` |
| TTS | `pip install piper-tts` + a voice model |
| Claude bridge | set `BRIDGE_MODE=http` + run a local relay (see `app/bridge/claude_desktop.py`) |

Or install everything: `EDGE_INSTALL_MODELS=1 ./scripts/setup.sh`.

## Key endpoints

- `GET  /api/status` — feature + model availability (drives the installer dashboard)
- `GET  /api/devices` — connected K10s + live telemetry + location
- `POST /api/ask` `{query}` — text query through cache → local → bridge
- `POST /api/analyze` (multipart image) — OCR + vision
- `GET  /api/cache` · `GET /api/recordings` · `GET /api/ads/next`
- `WS   /device` — the K10 front-end connection

## Layout

```
app/
├── main.py            FastAPI app + routes
├── ws/                device_gateway (WS demux)
├── brain/             orchestrator + router (cache→local→bridge)
├── models/            stt, tts, ocr, vision, mood, llm_local
├── bridge/            claude_desktop (no-API relay)
├── cache/             semantic_cache
├── location/          geolocate (WiFi BSSID → coords, local DB)
├── recording/         recorder (SD/stream persistence)
├── ads/               ad_engine (opt-in, brand-safe)
├── telemetry/         sensors (store + alerts)
└── meta/              provenance (AEDI / Policy 986)
```

© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
