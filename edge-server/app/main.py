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
from app import logbuf, store

# ---- user settings overlay (dashboard Settings panel) — persisted, applied at boot ----
_TUNABLE = ("wake_word", "wake_words", "assistant_name", "ollama_model", "vision_model", "stt_model",
            "bridge_mode", "idle_sleep_s", "temp_alert_c",
            "ha_url", "ha_token", "hue_bridge", "chromecast_name", "mqtt_host", "mqtt_port",
            "dispatch_webhook_url", "image_api_url")
_SETTINGS_PATH = Path(settings.data_dir) / "settings.json"
try:
    if _SETTINGS_PATH.exists():
        for k, v in json.loads(_SETTINGS_PATH.read_text()).items():
            if k in _TUNABLE:
                setattr(settings, k, v)
except Exception:
    pass

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
assistant.telemetry = telemetry        # instant sensor answers ("what's the temperature?")
_TEMP_ALERT = {"ts": 0.0}

# Prewarm the local brain in the background so the FIRST question answers fast.
import threading as _threading
_threading.Thread(target=orc.llm.prewarm, daemon=True).start()

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
    store.add_telemetry(did, tel)   # persistent history (sampled)
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
    state["audio_seq"] = a.get("audio_seq", 0)   # device plays say.wav when this bumps
    state["ocr_req"] = 1 if (time.time() - _OCR_REQ["ts"] < 6) else 0   # dashboard OCR trigger
    # TEMPERATURE INDICATION: hot room -> orb tints orange->red while idle, and Peper
    # speaks an alert (at most once per 10 min).
    try:
        t = float(tel.get("temp_c") or 0)
        if t >= settings.temp_alert_c:
            frac = min(1.0, (t - settings.temp_alert_c) / 8.0)
            state["temp_hot"] = 1
            if a["state"] in ("idle", "sleeping"):
                state["color"] = orbcfg._lerp("FF8C00", "FF2D00", frac)   # orange -> red
                state["label"] = f"HOT {t:.0f}C"
            if time.time() - _TEMP_ALERT["ts"] > 600:
                _TEMP_ALERT["ts"] = time.time()
                assistant.handle_text(f"Alert: the room temperature is {t:.0f} degrees.")
                logbuf.add("alert", f"temperature {t:.1f}C >= {settings.temp_alert_c}C")
    except Exception:
        pass
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
    logbuf.add("chat", f"{text[:60]!r} -> [{turn.get('source')}] {reply[:60]!r}")
    store.add_event("chat", f"{text[:120]} -> {reply[:200]}")
    return {"reply": reply, "source": turn.get("source"), "tone": turn.get("tone"),
            "state": turn.get("state"), "audio": turn.get("audio")}


# ---------- Voice home-assistant: utterance in (WAV), reply + state + tone out ----------
@app.post("/api/voice")
async def voice(file: UploadFile = File(...)):
    """Dashboard/device push-to-talk: upload an utterance WAV -> STT -> brain -> reply(+TTS)."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(await file.read())
        path = tmp.name
    turn = assistant.handle_wav(path, gate=False)   # dashboard mic = explicit intent (no wake word)
    if turn.get("reply"):
        _LAST_SAY["text"] = turn["reply"]; _LAST_SAY["ts"] = time.time()
    return turn


@app.post("/api/voice-raw")
async def voice_raw(request: Request):
    """Raw WAV body from the K10 (I2S capture) -> STT -> brain -> reply(+TTS).
    The device shows the reply via its next /ingest poll (state.say + tone colour)."""
    data = await request.body()
    # The device's on-board WAV header is unreliable; rebuild a correct one server-side.
    # Body = 44-byte header + raw PCM16 stereo @ 16 kHz. Re-wrap the PCM cleanly for Whisper.
    import wave as _wave
    try:
        (Path(settings.data_dir) / "last_raw.bin").write_bytes(data)
    except Exception:
        pass
    raw = data[44:] if len(data) > 44 else data
    raw = raw[: len(raw) // 4 * 4]
    rms = 0
    mono = raw
    try:
        import numpy as _np
        # The ESP32 I2S gives native little-endian int16 stereo. Do NOT guess byte order by
        # loudness — byte-swapped speech looks like LOUD white noise and always "wins",
        # which fed Whisper garbage. Verify LE with lag-1 autocorrelation (speech is smooth).
        le = _np.frombuffer(raw, dtype="<i2")
        L, R = le[0::2].astype(_np.float32), le[1::2].astype(_np.float32)
        def _rms(x): return float(_np.sqrt(_np.mean(x ** 2))) if x.size else 0.0
        def _ac1(x):
            if x.size < 3: return 0.0
            x = x - x.mean(); d = float(_np.dot(x, x))
            return float(_np.dot(x[:-1], x[1:]) / d) if d else 0.0
        a = L if _rms(L) >= _rms(R) else R          # the mic lives on one channel
        a -= a.mean()                                # remove DC offset
        rms = int(_rms(a)); ac = _ac1(a)
        peak = float(_np.abs(a).max()) if a.size else 0.0
        if rms < 25:                                 # silence — don't waste an STT pass
            print(f"[mic] silence rms={rms}", flush=True)
            return {"ok": False, "note": "silence", "transcript": ""}
        if peak > 0:                                 # gentle normalise to ~60% FS (no clipping)
            a = a * min(6.0, 0.6 * 32767.0 / peak)
        mono = _np.clip(a, -32768, 32767).astype("<i2").tobytes()
        print(f"[mic] rms={rms} ac1={ac:.2f} peak={int(peak)}", flush=True)
    except Exception as e:
        print("[mic-analyze] err", e, flush=True)
    path = str(Path(settings.data_dir) / "last_device.wav")
    try:
        with _wave.open(path, "wb") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(16000); wf.writeframes(mono)
    except Exception:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(data); path = tmp.name
    turn = assistant.handle_wav(path)
    print(f"[voice-raw] bytes={len(data)} rms={rms} transcript={turn.get('transcript')!r} "
          f"woke={turn.get('woke')} ignored={turn.get('ignored')} reply={ (turn.get('reply') or '')[:40]!r}",
          flush=True)
    if turn.get("transcript"):
        logbuf.add("voice", f"heard: {turn.get('transcript')!r} -> {'IGNORED' if turn.get('ignored') else (turn.get('reply') or '')[:60]}")
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


# ---------- Full device screen rendered on the EDGE (IONITY logo + orb + AI glyph + text) ----------
@app.get("/api/screen.png")
def screen_png():
    s = assistant.snapshot()
    phase = (time.time() * 3.0) % (2 * 3.14159)
    from fastapi.responses import Response
    png = orb_render.screen_png(s["color"], s["level"], phase, s["state"], s.get("reply", ""), s["state"])
    return Response(content=png, media_type="image/png")


@app.get("/api/screen565")
def screen_565():
    """Raw 240x320 big-endian RGB565 the K10 blits with canvasDrawBitmap. Device does no compute."""
    s = assistant.snapshot()
    phase = (time.time() * 3.0) % (2 * 3.14159)
    from fastapi.responses import Response
    data = orb_render.screen_rgb565(s["color"], s["level"], phase, s["state"], s.get("reply", ""), s["state"])
    return Response(content=data, media_type="application/octet-stream",
                    headers={"X-Screen-On": "1" if s.get("screen_on") else "0",
                             "X-Audio-Seq": str(s.get("audio_seq", 0))})


# ---------- Settings (dashboard panel; persisted; applied live) ----------
@app.get("/api/settings")
def settings_get():
    return {k: getattr(settings, k, "") for k in _TUNABLE}


@app.post("/api/settings")
def settings_set(body: dict = Body(...)):
    changed = {}
    for k, v in (body or {}).items():
        if k in _TUNABLE:
            cur = getattr(settings, k)
            try:
                v = type(cur)(v) if not isinstance(cur, str) else str(v)
            except Exception:
                continue
            setattr(settings, k, v)
            changed[k] = v
    try:
        _SETTINGS_PATH.write_text(json.dumps({k: getattr(settings, k) for k in _TUNABLE}, indent=2))
    except Exception:
        pass
    # apply live where possible
    try:
        orc.llm.model = settings.ollama_model
        orc.bridge.mode = (settings.bridge_mode or "off").lower()
        if assistant.home:
            assistant.home._ha_tried = assistant.home._hue_tried = False   # re-init lazily
    except Exception:
        pass
    logbuf.add("settings", f"updated: {list(changed.keys())}")
    return {"ok": True, "changed": changed}


# ---------- Logs (dashboard panel) ----------
@app.get("/api/logs")
def logs():
    return {"logs": logbuf.recent()}


# ---------- Persistent history (SQLite) ----------
@app.get("/api/history")
def api_history(hours: float = 24, device: str | None = None):
    return store.history(hours, device)


# ---------- AiD Sigil: a scannable identity/context card (from the AiD design doc) ----------
@app.get("/api/sigil.png")
def sigil():
    """A brand 'Sigil' — QR to the public repo over an Ionity-blue generative-art tile,
    with provenance in PNG metadata. The dashboard's portable identity artifact."""
    from fastapi.responses import Response
    import io, hashlib
    try:
        import qrcode
        from PIL import Image, ImageDraw
        from PIL.PngImagePlugin import PngInfo
        payload = "https://github.com/Ionity-Global/ionity-k10-edge"
        qr = qrcode.QRCode(border=2, box_size=8)
        qr.add_data(payload); qr.make(fit=True)
        qimg = qr.make_image(fill_color="#0b2036", back_color="#eaf6ff").convert("RGB")
        W = 420; card = Image.new("RGB", (W, W + 60), (5, 11, 20))
        d = ImageDraw.Draw(card)
        seed = int(hashlib.sha256(payload.encode()).hexdigest(), 16)
        for i in range(160):                              # deterministic generative-art field
            x = (seed >> (i % 32)) % W; y = (seed >> ((i * 3) % 40)) % (W + 60)
            r = 6 + (seed >> i) % 26
            c = [(0, 180, 216), (46, 125, 225), (0, 210, 255)][i % 3]
            d.ellipse([x - r, y - r, x + r, y + r], outline=c)
        q = qimg.resize((300, 300)); card.paste(q, ((W - 300) // 2, 40))
        d.text((W // 2 - 30, 12), "IONITY · AiD", fill=(0, 210, 255))
        d.text((16, W + 40), "Policy 986 AED · scan to pull the public brain", fill=(70, 100, 120))
        meta = PngInfo()
        meta.add_text("Author", "Johan Wilhelm van Antwerp")
        meta.add_text("Entity", "Ionity (Pty) Ltd (AEDI)")
        meta.add_text("Policy", "986 AED"); meta.add_text("Payload", payload)
        buf = io.BytesIO(); card.save(buf, "PNG", pnginfo=meta)
        return Response(content=buf.getvalue(), media_type="image/png")
    except Exception as e:
        return JSONResponse({"error": str(e), "note": "pip install qrcode Pillow"}, status_code=500)


# ---------- Installable app (PWA): manifest + service worker ----------
@app.get("/api/manifest.webmanifest")
def manifest():
    return JSONResponse({
        "name": "Ionity Home Assistant", "short_name": "Ionity",
        "description": "Peper — the Ionity edge voice home assistant. Policy 986 AED.",
        "start_url": "/", "display": "standalone",
        "background_color": "#050b14", "theme_color": "#050b14",
        "icons": [{"src": "/web/ionity-logo.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"}],
    }, media_type="application/manifest+json")


@app.get("/api/sw.js")
def service_worker():
    from fastapi.responses import Response
    sw = (
        "const C='ionity-v1';"
        "self.addEventListener('install',e=>{self.skipWaiting();});"
        "self.addEventListener('activate',e=>{self.clients.claim();});"
        "self.addEventListener('fetch',e=>{const u=new URL(e.request.url);"
        "if(u.pathname==='/'||u.pathname.startsWith('/web/')){"
        "e.respondWith(fetch(e.request).then(r=>{const c=r.clone();caches.open(C).then(x=>x.put(e.request,c));return r})"
        ".catch(()=>caches.match(e.request)));}});"
    )
    return Response(content=sw, media_type="application/javascript")


# ---------- Vision: camera image -> Gemma multimodal (OCR + description), OCR fallback ----------
_LAST_VISION = {"text": "", "ts": 0.0, "backend": ""}
_OCR_REQ = {"ts": 0.0}   # dashboard "OCR now" -> device grabs a camera frame on its next sync


def _vision(img: bytes, prompt: str) -> dict:
    """Shared vision pipeline: Gemma multimodal via Ollama; classic OCR fallback.
    Speaks the answer (device plays it via audio_seq) and adds it to the transcript."""
    logbuf.add("see", f"image {len(img)} bytes")
    try:
        import base64
        req = urllib.request.Request(
            settings.ollama_url.rstrip("/") + "/api/generate",
            data=json.dumps({"model": settings.vision_model, "prompt": prompt,
                             "images": [base64.b64encode(img).decode()], "stream": False,
                             "keep_alive": "30m"}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            res = json.loads(r.read())
        text = (res.get("response") or "").strip()
        if text:
            assistant.last_reply = text; assistant.tone = "neutral"
            assistant.transcript.append({"role": "assistant", "text": "[vision] " + text[:300], "ts": time.time()})
            assistant._speak(text[:300]); assistant.set_state("speaking")
            _LAST_SAY["text"] = text[:300]; _LAST_SAY["ts"] = time.time()
            logbuf.add("see", "gemma vision ok")
            store.add_event("vision", text[:300])
            _LAST_VISION.update(text=text, ts=time.time(), backend="gemma-vision")
            return {"ok": True, "backend": "gemma-vision", "text": text,
                    "provenance": provenance.stamp("vision", {"len": len(img)})}
    except Exception as e:
        logbuf.add("see", f"gemma vision failed: {e}")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp.write(img); path = tmp.name
    out = orc.analyze_image(path, want_ocr=True)
    txt = " ".join((out.get("ocr") or {}).get("lines", []))[:400] if isinstance(out.get("ocr"), dict) else ""
    if txt:
        assistant.last_reply = txt; assistant._speak(txt[:300]); assistant.set_state("speaking")
        assistant.transcript.append({"role": "assistant", "text": "[ocr] " + txt[:300], "ts": time.time()})
    _LAST_VISION.update(text=txt or "(no text found)", ts=time.time(), backend="ocr")
    return {"ok": True, "backend": "ocr", "text": txt or "(no text found)", "detail": out}


# ---------- OCR stream to the dashboard ----------
@app.get("/api/cam.jpg")
def cam_jpg():
    p = Path(settings.data_dir) / "last_cam.jpg"
    if p.exists():
        return FileResponse(str(p), media_type="image/jpeg",
                            headers={"Cache-Control": "no-store"})
    return JSONResponse({"note": "no camera frame yet — press [A] on the K10 or click OCR now"}, status_code=404)


@app.get("/api/vision")
def vision_last():
    p = Path(settings.data_dir) / "last_cam.jpg"
    return {**_LAST_VISION, "has_frame": p.exists(),
            "frame_ts": (p.stat().st_mtime if p.exists() else 0)}


@app.post("/api/ocr-now")
def ocr_now():
    """Remote OCR trigger: the device sees ocr_req on its next /ingest sync and grabs a frame."""
    _OCR_REQ["ts"] = time.time()
    logbuf.add("see", "OCR requested from dashboard")
    return {"ok": True, "note": "device will capture on its next sync (~2 s)"}


@app.post("/api/see")
async def see(file: UploadFile = File(...), prompt: str = "Describe this image and read any text in it (OCR). Be concise."):
    return _vision(await file.read(), prompt)


@app.post("/api/see-raw565")
async def see_raw565(request: Request, w: int = 320, h: int = 240):
    """OCR MODE from the K10: raw big-endian RGB565 camera frame -> JPEG -> Gemma vision.
    The spoken answer reaches the device automatically (audio_seq -> say.wav)."""
    raw = await request.body()
    try:
        import numpy as _np
        import io as _io
        from PIL import Image as _Img
        a = _np.frombuffer(raw[: w * h * 2], dtype=">u2").reshape(h, w)
        r = ((a >> 11) & 0x1F) << 3; g = ((a >> 5) & 0x3F) << 2; b = (a & 0x1F) << 3
        rgb = _np.dstack([r, g, b]).astype(_np.uint8)
        buf = _io.BytesIO(); _Img.fromarray(rgb).save(buf, "JPEG", quality=88)
        (Path(settings.data_dir) / "last_cam.jpg").write_bytes(buf.getvalue())
        return _vision(buf.getvalue(), "You are looking through a home assistant's camera. "
                                       "Read any text you can see (OCR) and briefly say what is in view.")
    except Exception as e:
        logbuf.add("see", f"raw565 decode failed: {e}")
        return {"ok": False, "error": str(e)}


# ---------- Smart-home control (Home Assistant / Hue / Cast / MQTT) ----------
@app.get("/api/home")
def home_status():
    return assistant.home.status() if assistant.home else {"enabled": False}


@app.post("/api/dispatch")
def dispatch(body: dict = Body(...)):
    """Actuate a spoken/typed home command via the configured backends."""
    cmd = ((body or {}).get("command") or "").strip()
    if not cmd:
        return {"handled": False, "note": "no command"}
    if assistant.home is None:
        return {"handled": False, "note": "home control unavailable"}
    res = assistant.home.parse_and_act(cmd)
    res["backends"] = assistant.home.status()
    # optional extra webhook fan-out (kept for compatibility)
    if settings.dispatch_webhook_url:
        try:
            data = json.dumps({"command": cmd}).encode()
            req = urllib.request.Request(settings.dispatch_webhook_url, data=data,
                                         headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=4)
            res["webhook"] = "sent"
        except Exception as e:
            res["webhook"] = f"failed: {e}"
    return res


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
