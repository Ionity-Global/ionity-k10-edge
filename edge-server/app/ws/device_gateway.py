"""Device WebSocket gateway — one connection per K10. Demuxes JSON control frames
and binary media frames, drives the orchestrator, streams answers back.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0"""
from __future__ import annotations
import json
import struct
import time
import wave
from pathlib import Path

from fastapi import WebSocket, WebSocketDisconnect

from app.config import settings

# media frame header: type(1) seq(4,little) ts(4,little) len(3,little) pad(1)
_HDR = 12


class DeviceGateway:
    def __init__(self, orchestrator, recorder, geolocator, telemetry, ads) -> None:
        self.orc = orchestrator
        self.recorder = recorder
        self.geo = geolocator
        self.telemetry = telemetry
        self.ads = ads
        self.devices: dict[str, dict] = {}

    def snapshot(self) -> list[dict]:
        return [{"device_id": k, **{x: v[x] for x in ("last_seen", "caps", "ip")}}
                for k, v in self.devices.items()]

    async def handle(self, ws: WebSocket) -> None:
        await ws.accept()
        device_id = "unknown"
        audio_buf = bytearray()
        try:
            while True:
                msg = await ws.receive()
                if "text" in msg and msg["text"] is not None:
                    device_id = await self._on_text(ws, msg["text"], device_id)
                elif "bytes" in msg and msg["bytes"] is not None:
                    audio_buf = await self._on_binary(ws, msg["bytes"], device_id, audio_buf)
        except WebSocketDisconnect:
            if device_id in self.devices:
                self.devices[device_id]["online"] = False
        finally:
            # Finalize any open recording session so its manifest is written
            # (otherwise /api/recordings would never list this session).
            try:
                self.recorder.stop(device_id)
            except Exception:
                pass

    async def _on_text(self, ws: WebSocket, text: str, device_id: str) -> str:
        try:
            env = json.loads(text)
        except Exception:
            return device_id
        t = env.get("type")
        did = env.get("device_id", device_id)
        payload = env.get("payload", {}) or {}

        if t == "hello":
            self.devices[did] = {
                "caps": payload.get("caps", []), "fw": payload.get("fw"),
                "last_seen": time.time(), "ip": ws.client.host if ws.client else None,
                "online": True,
            }
            await self._send(ws, "hello_ack", {
                "features": {
                    "vision": settings.feat_vision, "ocr": settings.feat_ocr,
                    "voice": settings.feat_voice, "geo": settings.feat_geo,
                    "recording": settings.feat_recording, "ads": settings.feat_ads,
                },
                "audio_sr": 16000, "cam_fps": 8,
            })
        elif t in ("telemetry", "hb"):
            if did in self.devices:
                self.devices[did]["last_seen"] = time.time()
            if t == "telemetry":
                self.telemetry.ingest(did, payload)
                alert = self.telemetry.check_alerts(did, payload)
                if alert:
                    await self._send(ws, "notify", alert)
        elif t == "geo_scan":
            loc = self.geo.resolve(payload.get("aps", []))
            self.telemetry.set_location(did, loc)
            await self._send(ws, "cmd", {"cmd": "geo_ack", "loc": loc})
        elif t == "cmd":
            # a button press or device-side command -> treat label as an intent
            btn = payload.get("button")
            if btn is not None:
                intent = {0: "start voice query", 1: "scan and OCR the view"}.get(btn, "menu")
                res = self.orc.ask(f"User pressed button {btn}: {intent}")
                await self._send(ws, "answer", {"text": res["text"]})
        return did

    async def _on_binary(self, ws, data: bytes, device_id: str, audio_buf: bytearray) -> bytearray:
        if len(data) < _HDR:
            return audio_buf
        mtype = data[0]
        seq, ts = struct.unpack_from("<II", data, 1)
        length = data[9] | (data[10] << 8) | (data[11] << 16)
        payload = data[_HDR:_HDR + length]

        if mtype == 1:      # JPEG camera frame
            if settings.feat_recording:
                self.recorder.write_frame(device_id, "cam", payload)
            # (Vision/OCR on demand — the installer or a button triggers analyze)
        elif mtype == 2:    # audio frame (PCM16 mono)
            audio_buf.extend(payload)
            # naive end-of-utterance: flush ~2s of audio
            if len(audio_buf) >= 16000 * 2 * 2:
                wav_path = self._flush_wav(device_id, audio_buf)
                audio_buf = bytearray()
                if settings.feat_voice:
                    res = self.orc.ask_audio(wav_path)
                    await self._send(ws, "answer", {
                        "text": res.get("text", ""),
                        "transcript": res.get("transcript", ""),
                    })
        elif mtype == 3:    # screen capture
            if settings.feat_recording:
                self.recorder.write_frame(device_id, "screen", payload)
        return audio_buf

    def _flush_wav(self, device_id: str, pcm: bytearray) -> str:
        path = Path(settings.data_dir) / f"utter_{device_id}_{int(time.time())}.wav"
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
            w.writeframes(bytes(pcm))
        return str(path)

    async def _send(self, ws: WebSocket, mtype: str, payload: dict) -> None:
        await ws.send_text(json.dumps({"v": "1", "type": mtype, "ts": int(time.time() * 1000),
                                       "payload": payload}))
