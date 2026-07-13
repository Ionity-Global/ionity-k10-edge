"""IonityEdge · K10 — Edge Brain API + device gateway.

Run:  python -m app.main   (or: uvicorn app.main:app --host 0.0.0.0 --port 8765)
Boots immediately with graceful model fallbacks; features light up as you install them.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
"""
from __future__ import annotations
import json
import tempfile
import time
import urllib.request
from pathlib import Path

from fastapi import FastAPI, WebSocket, UploadFile, File, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.config import settings
from app.brain.orchestrator import Orchestrator
from app.ws.device_gateway import DeviceGateway
from app.location.geolocate import Geolocator
from app.recording.recorder import Recorder
from app.ads.ad_engine import AdEngine
from app.telemetry.sensors import Telemetry
from app.meta import provenance
from app import orb as orbcfg
from app.voice.assistant import Assistant
from app.render import orb_render

app = FastAPI(title="IonityEdge · K10 — Edge Brain", version=__version__)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

orc = Orchestrator()
telemetry = Telemetry()
recorder = Recorder()
geolocator = Geolocator()
ads = AdEngine()
gateway = DeviceGateway(orc, recorder, geolocator, telemetry, ads)
assistant = Assistant(orc, orc.mood)   # voice home-assistant: state machine + turns + tone

# Latest Claude/brain reply — shown on the K10 "readback" segment + spoken by the dashboard (TTS).
_LAST_SAY = {"text": "", "ts": 0.0}


# ---------- Device WebSocket ----------
@app.websocket("/device")
async def device_ws(ws: WebSocket):
    await gateway.handle(ws)


# ---------- Health / meta ----------
@app.get("/")
def root():
    dash = Path(__file__).resolve().parent / "web" / "dashboard.html"
    if dash.exists():
        return FileResponse(str(dash))
    return {"project": "IonityEdge · K10", "version": __version__,
            "tagline": "Building Tomorrow, Today.", "policy": "Policy 986 AED"}


@app.get("/api/status")
def status():
    return {"version": __version__, "features": {
        "vision": settings.feat_vision, "ocr": settings.feat_ocr,
        "voice": settings.feat_voice, "mood": settings.feat_mood,
        "geo": settings.feat_geo, "recording": settings.feat_recording,
        "ads": settings.feat_ads}, "brain": orc.status()}


@app.get("/api/devices")
def devices():
    # Merge both registries: WS-gateway devices AND HTTP /ingest nodes (telemetry store),
    # so the installer's Stream page sees the live sensory-frontend node regardless of transport.
    out: dict[str, dict] = {}
    for d in gateway.snapshot():
        did = d["device_id"]
        out[did] = {**d, "transport": "ws", "telemetry": telemetry.get(did)}
    for did in telemetry.latest.keys():
        tel = telemetry.get(did)
        entry = out.get(did, {"device_id": did, "transport": "http"})
        entry["telemetry"] = tel
        entry.setdefault("ip", (tel.get("latest") or {}).get("ip"))
        entry["state"] = tel.get("state") or {}
        entry["online"] = (time.time() - (tel.get("latest") or {}).get("_ts", 0)) < 10
        out[did] = entry
    return {"devices": list(out.values())}


# ---------- Text / voice / vision ----------
@app.post("/api/ask")
def ask(body: dict = Body(...)):
    q = (body or {}).get("query", "")
    return orc.ask(q, body.get("context"))


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...), ocr: bool = True):
    suffix = Path(file.filename or "frame.jpg").suffix or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        path = tmp.name
    return orc.analyze_image(path, want_ocr=ocr)


# ---------- MicroPython demo ingest ----------
@app.post("/ingest")
def ingest(body: dict = Body(...)):
    """Node uploads sensors -> server computes the orb render and returns it."""
    did = (body or {}).get("device_id", "mpy")
    tel = body.get("telemetry", {})
    telemetry.ingest(did, tel)
    # Optional WiFi scan for the moving device -> local BSSID geolocation (no cloud).
    aps = tel.get("aps")
    if aps:
        try:
            telemetry.set_location(did, geolocator.resolve(aps))
        except Exception:
            pass
    state = orbcfg.compute(did, tel)
    # Merge the voice-assistant so the node reflects the AI: lights follow the AI's STATE + TONE,
    # and Claude's words show on the device readback. Ambient sound-orb when the AI is idle/asleep.
    assistant.tick()
    a = assistant.snapshot()
    if a["state"] in ("listening", "thinking", "speaking"):
        c = a["color"]
        state["color"] = c
        state["label"] = a["state"].upper()
        state["leds"] = [orbcfg._dark(c, 0.9), orbcfg._dark(c, 0.6), orbcfg._dark(c, 0.35)]
    state["ai_state"] = a["state"]
    if a.get("reply"):
        state["say"] = a["reply"][:96]           # Claude's words on the device
    elif _LAST_SAY["text"] and (time.time() - _LAST_SAY["ts"] < 25):
        state["say"] = _LAST_SAY["text"][:96]
    telemetry.set_state(did, state)
    return {"ok": True, "state": state}


# ---------- Cache / recordings / ads / config ----------
@app.get("/api/cache")
def cache_stats():
    return orc.cache.stats()


@app.get("/api/recordings")
def recordings():
    return {"recordings": recorder.list()}


@app.get("/api/ads/next")
def ad_next():
    return ads.next() or {"kind": "none"}


@app.get("/api/config")
def get_config():
    return {"edge_host": settings.edge_host, "edge_port": settings.edge_port,
            "cache_threshold": settings.cache_threshold,
            "bridge_mode": settings.bridge_mode, "ollama_model": settings.ollama_model}


# ---------- Live-tunable Orb config (edited in localhost, pulled by the K10) ----------
@app.get("/api/orb-config")
def orb_get():
    return orbcfg.load()

@app.post("/api/orb-config")
def orb_set(body: dict = Body(...)):
    return orbcfg.save(body or {})

@app.post("/api/orb-config/reset")
def orb_reset():
    return orbcfg.reset()


# ---------- Live device feed (drives the dashboard's mini ESP screen mirror) ----------
@app.get("/api/live")
def live():
    return {"devices": {d: telemetry.get(d) for d in list(telemetry.latest.keys())}}


@app.get("/api/orb-state")
def orb_state(device: str = "ionity-k10"):
    return telemetry.get(device).get("state") or {}


# ---------- Interactive chat with the brain (local Gemma / Claude bridge) ----------
# The reply is SPOKEN by the dashboard (TTS) and streamed to the K10 readback segment.
@app.post("/api/chat")
def chat(body: dict = Body(...)):
    text = ((body or {}).get("text") or "").strip()
    if not text:
        return {"reply": "", "source": "none"}
    turn = assistant.handle_text(text)          # drives state machine + tone + TTS
    reply = turn.get("reply", "")
    _LAST_SAY["text"] = reply
    _LAST_SAY["ts"] = time.time()
    return {"reply": reply, "source": turn.get("source"), "tone": turn.get("tone"),
            "state": turn.get("state"), "audio": turn.get("audio")}


# ---------- Voice home-assistant: utterance in (WAV), reply + state + tone out ----------
@app.post("/api/voice")
async def voice(file: UploadFile = File(...)):
    """Dashboard/device push-to-talk: upload an utterance WAV -> STT -> brain -> reply(+TTS)."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(await file.read())
        path = tmp.name
    turn = assistant.handle_wav(path)
    if turn.get("reply"):
        _LAST_SAY["text"] = turn["reply"]; _LAST_SAY["ts"] = time.time()
    return turn


@app.post("/api/voice-raw")
async def voice_raw(request: Request):
    """Raw WAV body from the K10 (I2S capture) -> STT -> brain -> reply(+TTS).
    The device shows the reply via its next /ingest poll (state.say + tone colour)."""
    data = await request.body()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(data)
        path = tmp.name
    turn = assistant.handle_wav(path)
    if turn.get("reply"):
        _LAST_SAY["text"] = turn["reply"]; _LAST_SAY["ts"] = time.time()
    return turn


@app.get("/api/assistant")
def assistant_state():
    assistant.tick()                    # relax state over time (speaking->idle->sleeping)
    return assistant.snapshot()


@app.post("/api/level")
def set_level(body: dict = Body(...)):
    assistant.set_level((body or {}).get("level", 0))
    return {"ok": True, "level": assistant.level, "state": assistant.state}


@app.get("/api/say")
def say_get():
    return {"text": _LAST_SAY["text"], "ts": _LAST_SAY["ts"]}


@app.get("/api/say.wav")
def say_wav():
    p = assistant.last_audio
    if p and Path(p).exists():
        return FileResponse(p, media_type="audio/wav", filename="ionity-say.wav")
    return JSONResponse({"available": False, "note": "no server TTS audio (set TTS_VOICE / PIPER_VOICE)"},
                        status_code=404)


# ---------- Server-rendered orb frame (preview / device stream source) ----------
@app.get("/api/orb-frame.png")
def orb_frame(size: int = 240):
    s = assistant.snapshot()
    phase = (time.time() * 3.0) % (2 * 3.14159)
    png = orb_render.png_bytes(size, s["color"], s["level"], phase, s["state"])
    from fastapi.responses import Response
    return Response(content=png, media_type="image/png")


# ---------- Dispatch / home-assistance hook ----------
@app.post("/api/dispatch")
def dispatch(body: dict = Body(...)):
    cmd = ((body or {}).get("command") or "").strip().lower()
    device = (body or {}).get("device", "ionity-k10")
    known = {"lights on": "LIGHTS_ON", "lights off": "LIGHTS_OFF",
             "record": "RECORD", "stop": "STOP", "locate": "GEO", "read": "TTS"}
    action = known.get(cmd, "UNKNOWN")
    st = (telemetry.get(device) or {}).get("state") or {}
    result = {"command": cmd, "action": action, "device": device}
    url = settings.dispatch_webhook_url
    if not url:
        result.update({"configured": False,
                       "note": "Set DISPATCH_WEBHOOK_URL (e.g. a Home Assistant webhook) to forward commands."})
        return result
    try:
        data = json.dumps({"command": cmd, "action": action, "device": device, "state": st}).encode()
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=4) as r:
            result.update({"configured": True, "forwarded": True, "status": getattr(r, "status", 200)})
    except Exception as e:
        result.update({"configured": True, "forwarded": False, "error": str(e)})
    return result


# ---------- Image generation (local model relay, else a real procedural SVG) ----------
def _mood_orb_svg(prompt: str) -> str:
    """A real, deterministic 240x320 mood-orb card built from the prompt + live palette.
    No cloud — always returns something the K10 can display as a background frame."""
    cfg = orbcfg.load()
    pal = [cfg["calm"], cfg["neutral"], cfg["warn"], cfg["agitated"]]
    h = sum(ord(c) for c in (prompt or "ionity"))
    col = pal[h % len(pal)]
    r2 = pal[(h // 7) % len(pal)]
    safe = (prompt or "IONITY").strip()[:40].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="240" height="320" viewBox="0 0 240 320">'
        f'<defs><radialGradient id="g" cx="50%" cy="42%" r="60%">'
        f'<stop offset="0%" stop-color="#{col}"/><stop offset="100%" stop-color="#03080f"/></radialGradient></defs>'
        f'<rect width="240" height="320" fill="#03080f"/>'
        f'<circle cx="120" cy="132" r="78" fill="url(#g)"/>'
        f'<circle cx="120" cy="132" r="78" fill="none" stroke="#{r2}" stroke-opacity="0.5" stroke-width="2"/>'
        f'<circle cx="96" cy="108" r="14" fill="#ffffff" opacity="0.85"/>'
        f'<text x="16" y="30" fill="#00d2ff" font-family="system-ui" font-size="16" letter-spacing="1">IONITY · ORB</text>'
        f'<text x="16" y="286" fill="#eaf6ff" font-family="system-ui" font-size="13">{safe}</text>'
        f'<text x="16" y="306" fill="#7fa6c9" font-family="system-ui" font-size="10">Policy 986 AED · generated locally</text>'
        f'</svg>'
    )


@app.post("/api/generate-image")
def generate_image(body: dict = Body(...)):
    prompt = (body or {}).get("prompt", "")
    url = settings.image_api_url
    if url:
        try:
            data = json.dumps({"prompt": prompt}).encode()
            req = urllib.request.Request(url, data=data,
                                         headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=30) as r:
                payload = r.read().decode("utf-8", "ignore")
            try:
                relayed = json.loads(payload)
            except Exception:
                relayed = {"raw": payload[:2000]}
            return {"status": "ok", "backend": "relay", "prompt": prompt, "result": relayed,
                    "provenance": provenance.stamp("image_relay", {"prompt": prompt})}
        except Exception as e:
            # fall through to the local SVG if the relay is unreachable
            note = f"relay failed ({e}); returned local SVG"
    else:
        note = "no IMAGE_API_URL set — returned a local procedural SVG"
    svg = _mood_orb_svg(prompt)
    import base64
    data_uri = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
    return {"status": "ok", "backend": "svg", "prompt": prompt, "note": note,
            "svg": svg, "data_uri": data_uri,
            "provenance": provenance.stamp("image_svg", {"prompt": prompt})}


# ---------- Server-side TTS (Piper) — optional; browser TTS is the default ----------
@app.get("/api/speak")
def speak_status():
    return {"available": orc.tts.available,
            "note": "POST {text} to synthesize a WAV" if orc.tts.available
                    else "server TTS off — set PIPER_VOICE to a .onnx voice; the dashboard uses browser TTS meanwhile"}


@app.post("/api/speak")
def speak(body: dict = Body(...)):
    text = ((body or {}).get("text") or "").strip()
    if not text:
        return {"available": orc.tts.available, "note": "empty text"}
    if not orc.tts.available:
        return {"available": False,
                "note": "server TTS not configured (set PIPER_VOICE); the dashboard speaks replies via browser TTS"}
    out = str(Path(settings.data_dir) / f"say_{int(time.time())}.wav")
    p = orc.speak(text, out)
    if p and Path(p).exists():
        return FileResponse(p, media_type="audio/wav", filename="ionity-say.wav")
    return {"available": False, "note": "synthesis failed"}


# ---------- Serve the built installer (optional) ----------
_web = Path(__file__).resolve().parent / "web"
if _web.exists():
    app.mount("/web", StaticFiles(directory=str(_web)), name="web")   # logo, favicon

_dist = Path(__file__).resolve().parents[2] / "installer" / "dist"
if _dist.exists():
    app.mount("/app", StaticFiles(directory=str(_dist), html=True), name="installer")


def main():
    import uvicorn
    print(f"IonityEdge · K10 — Edge Brain v{__version__}  |  Policy 986 AED")
    print(f"  ws://<lan-ip>:{settings.edge_port}/device   ·   http://<lan-ip>:{settings.edge_port}/api/status")
    uvicorn.run("app.main:app", host=settings.edge_host, port=settings.edge_port, reload=False)


if __name__ == "__main__":
    main()
