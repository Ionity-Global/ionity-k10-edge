"""Server-side renderer (Pillow) for the IonityEdge K10.

Renders the ENTIRE device screen on the edge — IONITY wordmark, a glowing/breathing
orb whose colour follows the AI state + tone, the AI glyph masked into the orb centre,
and Claude's reply text — then emits it as a raw RGB565 frame the K10 blits with
canvas->canvasDrawBitmap (the device does zero compute). Also PNG for previews.
Brand assets live in app/web/assets/. Pure-Pillow, no cloud.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
"""
from __future__ import annotations
import io
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

BG = (3, 8, 15)
_ASSETS = Path(__file__).resolve().parents[1] / "web" / "assets"
_cache: dict = {}


def _hex(c: str):
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _font(size: int):
    key = ("font", size)
    if key in _cache:
        return _cache[key]
    f = None
    for name in ("arialbd.ttf", "arial.ttf", "segoeui.ttf"):
        try:
            f = ImageFont.truetype(name, size); break
        except Exception:
            continue
    if f is None:
        f = ImageFont.load_default()
    _cache[key] = f
    return f


def _asset(name: str):
    if name in _cache:
        return _cache[name]
    p = _ASSETS / name
    img = None
    if p.exists():
        try:
            img = Image.open(p).convert("RGBA")
        except Exception:
            img = None
    _cache[name] = img
    return img


def _circular(img: Image.Image, d: int) -> Image.Image:
    """Crop-to-centre-square, resize to d, apply a soft circular alpha mask."""
    w, h = img.size
    s = min(w, h)
    img = img.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2)).resize((d, d), Image.LANCZOS)
    mask = Image.new("L", (d, d), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, d - 1, d - 1], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(d * 0.02))
    out = img.copy(); out.putalpha(mask)
    return out


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ---- small orb (dashboard preview / /api/orb-frame.png) ----
def render(size: int, color: str, level: float, phase: float, state: str = "idle") -> Image.Image:
    W = H = int(size)
    r, g, b = _hex(color)
    level = max(0.0, min(1.0, float(level)))
    breathe = 0.5 + 0.5 * math.sin(phase)
    if state == "sleeping":
        breathe *= 0.25; r, g, b = int(r * 0.5), int(g * 0.5), int(b * 0.5)
    img = Image.new("RGB", (W, H), BG)
    cx, cy = W / 2.0, H / 2.0
    core = W * 0.20 + level * W * 0.15 + breathe * W * 0.05
    glow = Image.new("RGB", (W, H), BG); gd = ImageDraw.Draw(glow)
    for rad, a in ((core * 2.1, 0.10), (core * 1.6, 0.22), (core * 1.25, 0.5)):
        gd.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(int(r * a), int(g * a), int(b * a)))
    glow = glow.filter(ImageFilter.GaussianBlur(W * 0.05))
    img = Image.blend(img, glow, 1.0)
    d = ImageDraw.Draw(img)
    d.ellipse([cx - core, cy - core, cx + core, cy + core], fill=(r, g, b))
    hr = core * 0.30
    d.ellipse([cx - core * 0.34 - hr, cy - core * 0.34 - hr, cx - core * 0.34 + hr, cy - core * 0.34 + hr], fill=(255, 255, 255))
    return img.filter(ImageFilter.GaussianBlur(0.6))


# ---- FULL 240x320 device screen (logo + orb + AI glyph + Claude text) ----
def render_screen(color: str, level: float, phase: float, state: str,
                  reply: str = "", label: str = "", W: int = 240, H: int = 320) -> Image.Image:
    r, g, b = _hex(color)
    level = max(0.0, min(1.0, float(level)))
    breathe = 0.5 + 0.5 * math.sin(phase)
    dim = 0.28 if state == "sleeping" else 1.0
    if state == "sleeping":
        breathe *= 0.25
    R, G, B = int(r * dim), int(g * dim), int(b * dim)

    img = Image.new("RGB", (W, H), BG)
    cx, cy = W / 2.0, 150.0
    core = 34 + level * 26 + breathe * 8

    # glow
    glow = Image.new("RGB", (W, H), BG); gd = ImageDraw.Draw(glow)
    for rad, a in ((core * 2.4, 0.09), (core * 1.8, 0.18), (core * 1.3, 0.42)):
        gd.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(int(R * a), int(G * a), int(B * a)))
    glow = glow.filter(ImageFilter.GaussianBlur(9))
    img = Image.blend(img, glow, 1.0)
    d = ImageDraw.Draw(img)
    if state == "listening":
        rr = core * (1.3 + level * 0.6)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(R, G, B), width=2)
    d.ellipse([cx - core, cy - core, cx + core, cy + core], fill=(R, G, B))

    # AI glyph masked into the orb centre
    glyph = _asset("ai-glyph.png")
    if glyph is not None:
        gd_ = int(core * 1.15)
        disc = _circular(glyph, max(24, gd_))
        img.paste(disc, (int(cx - gd_ / 2), int(cy - gd_ / 2)), disc)
    # specular
    d.ellipse([cx - core * 0.4, cy - core * 0.42, cx - core * 0.4 + core * 0.34, cy - core * 0.42 + core * 0.34], fill=(255, 255, 255, 0))
    ImageDraw.Draw(img).ellipse([cx - core * 0.42, cy - core * 0.44, cx - core * 0.18, cy - core * 0.20], fill=(255, 255, 255))

    # IONITY wordmark (top)
    wm = _asset("ionity-wordmark-blue.png") or _asset("ionity-wordmark.png")
    if wm is not None:
        tw = 190; th = int(wm.height * tw / wm.width)
        img.paste(wm.resize((tw, th), Image.LANCZOS), (int((W - tw) / 2), 14), wm.resize((tw, th), Image.LANCZOS))

    # state label under the orb
    dd = ImageDraw.Draw(img)
    lab = (label or state or "").upper()
    if lab:
        f = _font(16); tw = dd.textlength(lab, font=f)
        dd.text(((W - tw) / 2, cy + core + 16), lab, fill=(int(R), int(G), int(B)), font=f)

    # Claude reply text (bottom)
    if reply:
        f = _font(15)
        lines = _wrap(dd, reply, f, W - 24)[:4]
        y = 236
        for ln in lines:
            dd.text((12, y), ln, fill=(234, 246, 255), font=f); y += 19
    # footer
    dd.text((12, H - 16), "Policy 986 AED", fill=(70, 100, 120), font=_font(11))
    return img


def _to_rgb565(img: Image.Image) -> bytes:
    """Big-endian RGB565, row-major. numpy-vectorised (fast enough to stream ~10 fps)."""
    try:
        import numpy as np
        a = np.asarray(img.convert("RGB"), dtype=np.uint16)          # H x W x 3
        v = ((a[:, :, 0] & 0xF8) << 8) | ((a[:, :, 1] & 0xFC) << 3) | (a[:, :, 2] >> 3)
        out = np.empty(v.size * 2, dtype=np.uint8)
        flat = v.reshape(-1)
        out[0::2] = (flat >> 8) & 0xFF
        out[1::2] = flat & 0xFF
        return out.tobytes()
    except Exception:
        px = img.load(); W, H = img.size
        out = bytearray(W * H * 2); i = 0
        for y in range(H):
            for x in range(W):
                r, g, b = px[x, y][:3]
                v = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                out[i] = (v >> 8) & 0xFF; out[i + 1] = v & 0xFF; i += 2
        return bytes(out)


def screen_rgb565(color, level, phase, state, reply="", label="") -> bytes:
    return _to_rgb565(render_screen(color, level, phase, state, reply, label))


def screen_png(color, level, phase, state, reply="", label="") -> bytes:
    buf = io.BytesIO(); render_screen(color, level, phase, state, reply, label).save(buf, "PNG"); return buf.getvalue()


def png_bytes(size, color, level, phase, state="idle") -> bytes:
    buf = io.BytesIO(); render(size, color, level, phase, state).save(buf, "PNG"); return buf.getvalue()


def rgb565_bytes(size, color, level, phase, state="idle") -> bytes:
    return _to_rgb565(render(size, color, level, phase, state))
