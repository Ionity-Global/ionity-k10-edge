"""Server-side orb renderer (Pillow).

Renders a glowing, breathing Ionity orb from the AI state + reply tone + audio level,
then emits it as PNG (dashboard/preview) or raw RGB565 (streamed to the K10 LCD via
canvas->canvasDrawBitmap). The device is a pure display — this is the "stream from the
server as screen" source. Pure-Pillow, no cloud.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
"""
from __future__ import annotations
import io
import math

from PIL import Image, ImageDraw, ImageFilter

BG = (3, 8, 15)


def _hex(c: str):
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def render(size: int, color: str, level: float, phase: float, state: str = "idle") -> Image.Image:
    """A square RGB image of the orb. `phase` animates the breathe; `level` (0..1) pumps size."""
    W = H = int(size)
    r, g, b = _hex(color)
    level = max(0.0, min(1.0, float(level)))
    breathe = 0.5 + 0.5 * math.sin(phase)
    if state == "sleeping":
        breathe *= 0.25
        r, g, b = int(r * 0.5), int(g * 0.5), int(b * 0.5)

    img = Image.new("RGB", (W, H), BG)
    cx, cy = W / 2.0, H / 2.0
    core = W * 0.20 + level * W * 0.15 + breathe * W * 0.05

    # layered glow (blurred translucent rings)
    glow = Image.new("RGB", (W, H), BG)
    gd = ImageDraw.Draw(glow)
    for rad, a in ((core * 2.1, 0.10), (core * 1.6, 0.22), (core * 1.25, 0.5)):
        gd.ellipse([cx - rad, cy - rad, cx + rad, cy + rad],
                   fill=(int(r * a), int(g * a), int(b * a)))
    glow = glow.filter(ImageFilter.GaussianBlur(W * 0.05))
    img = Image.blend(img, glow, 1.0)

    d = ImageDraw.Draw(img)
    # thinking: a swirling secondary lobe
    if state == "thinking":
        ox = math.cos(phase * 1.7) * core * 0.5
        oy = math.sin(phase * 1.7) * core * 0.5
        d.ellipse([cx + ox - core * 0.5, cy + oy - core * 0.5,
                   cx + ox + core * 0.5, cy + oy + core * 0.5],
                  fill=(int(r * 0.7), int(g * 0.7), int(b * 0.7)))
    # core
    d.ellipse([cx - core, cy - core, cx + core, cy + core], fill=(r, g, b))
    # ring for listening (reacts to level)
    if state == "listening":
        rr = core * (1.25 + level * 0.6)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(r, g, b), width=max(1, W // 90))
    # specular highlight
    hr = core * 0.30
    hx, hy = cx - core * 0.34, cy - core * 0.34
    d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=(255, 255, 255))
    return img.filter(ImageFilter.GaussianBlur(0.6))


def png_bytes(size: int, color: str, level: float, phase: float, state: str = "idle") -> bytes:
    buf = io.BytesIO()
    render(size, color, level, phase, state).save(buf, format="PNG")
    return buf.getvalue()


def rgb565_bytes(size: int, color: str, level: float, phase: float, state: str = "idle") -> bytes:
    """Raw big-endian RGB565, row-major — ready for K10 canvasDrawBitmap(x,y,w,h,data)."""
    img = render(size, color, level, phase, state)
    px = img.load()
    W, H = img.size
    out = bytearray(W * H * 2)
    i = 0
    for y in range(H):
        for x in range(W):
            r, g, b = px[x, y]
            v = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            out[i] = (v >> 8) & 0xFF
            out[i + 1] = v & 0xFF
            i += 2
    return bytes(out)
