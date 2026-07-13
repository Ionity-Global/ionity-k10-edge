"""Live-tunable Orb configuration — edited from localhost, pulled by the K10 every few seconds.
Everything the orb does (mood palette, thresholds, radius, brightness, fps) is here.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
"""
from __future__ import annotations
import json
from app.config import settings

# Hex colours are RRGGBB (no '#'); the device parses them with strtol(base16).
DEFAULTS: dict = {
    "calm":     "1E7BFF",   # blue   — calm / quiet
    "neutral":  "00D2FF",   # cyan
    "warn":     "26DE81",   # green
    "agitated": "E23B4E",   # red    — aggravated (also rendered darker)
    "base_r":   36,         # orb base radius (px)
    "pulse":    48,         # extra radius at full sound
    "darken":   0.55,       # how much darker at full agitation (0..1)
    "attack":   0.06,       # agitation rise rate
    "decay":    0.975,      # agitation fall rate
    "calm_th":  0.30,       # sustained level below this => CALM
    "agit_th":  0.72,       # sustained level above this => AGGRAVATED
    "bright_min": 3,        # LED brightness at silence (0..9)
    "bright_max": 9,        # LED brightness at full sound
    "fps_ms":   35,         # frame delay (ms)
}

_PATH = settings.data_dir / "orb_config.json"


def load() -> dict:
    if _PATH.exists():
        try:
            return {**DEFAULTS, **json.loads(_PATH.read_text())}
        except Exception:
            pass
    return dict(DEFAULTS)


def save(patch: dict) -> dict:
    cur = load()
    for k, v in (patch or {}).items():
        if k in DEFAULTS:
            cur[k] = v
    _PATH.write_text(json.dumps(cur, indent=2))
    return cur


def reset() -> dict:
    if _PATH.exists():
        _PATH.unlink()
    return dict(DEFAULTS)


# ---- Server-side render computation ----------------------------------------
# The node just uploads sensor data; the SERVER computes the mood, colour and LED
# states and returns them. The device (and the dashboard) simply display the result.
_agit: dict = {}   # per-device sustained-loudness state

def _rgb(h): h = h.lstrip("#"); return (int(h[0:2],16), int(h[2:4],16), int(h[4:6],16))
def _hx(r, g, b): return "".join("%02X" % max(0, min(255, int(x))) for x in (r, g, b))
def _lerp(a, b, t):
    A, B = _rgb(a), _rgb(b); t = max(0.0, min(1.0, t))
    return _hx(A[0]+(B[0]-A[0])*t, A[1]+(B[1]-A[1])*t, A[2]+(B[2]-A[2])*t)
def _dark(h, f): r, g, b = _rgb(h); f = max(0.0, min(1.0, f)); return _hx(r*f, g*f, b*f)
def _mood_color(cfg, x):
    if x < 0.34: return _lerp(cfg["calm"], cfg["neutral"], x/0.34)
    if x < 0.67: return _lerp(cfg["neutral"], cfg["warn"], (x-0.34)/0.33)
    return _lerp(cfg["warn"], cfg["agitated"], (x-0.67)/0.33)

def compute(device_id: str, tel: dict) -> dict:
    """From a node's sensor upload -> the exact orb render (colour, LEDs, size)."""
    cfg = load()
    lvl = tel.get("level")
    if lvl is None:
        lvl = float(tel.get("sound", 0)) / 50000.0
    lvl = max(0.0, min(1.0, float(lvl)))
    a = _agit.get(device_id, 0.0)
    a = a + (lvl - a) * float(cfg["attack"]) if lvl > a else a * float(cfg["decay"])
    a = max(0.0, min(1.0, a)); _agit[device_id] = a
    raw = 0.45 * lvl + 0.55 * a                       # responsive + sustained
    denom = max(0.05, float(cfg["agit_th"]) - float(cfg["calm_th"]))
    mood = max(0.0, min(1.0, (raw - float(cfg["calm_th"])) / denom))
    color = _dark(_mood_color(cfg, mood), 1.0 - float(cfg["darken"]) * mood)
    label = "CALM" if mood < 0.33 else ("ACTIVE" if mood < 0.7 else "AGGRAVATED")
    leds = [(_dark(color, 0.55 + 0.45*(i+1)/3) if lvl*3 > i else "000000") for i in range(3)]
    # LED brightness scales with sound between the tunable floor/ceiling (0..9); frame delay is tunable too.
    bmin, bmax = float(cfg["bright_min"]), float(cfg["bright_max"])
    brightness = int(round(max(0.0, min(9.0, bmin + (bmax - bmin) * lvl))))
    return {"color": color, "mood": round(mood, 3), "label": label,
            "level": round(lvl, 3), "radius": int(float(cfg["base_r"]) + lvl*float(cfg["pulse"])),
            "leds": leds, "brightness": brightness, "fps_ms": int(cfg["fps_ms"])}
