"""Smart-home control — turns spoken/typed intents into real actions.

Backends (all optional, config-gated, lazy, and fully graceful if absent):
  - Home Assistant  (homeassistant-api / aiohttp REST)  -> generic entities, scenes, media
  - Philips Hue     (phue)                               -> lights
  - Google Cast     (pychromecast)                       -> media / smart displays
  - MQTT            (paho-mqtt)                           -> ESP32 / custom IoT devices

parse_and_act(text) returns {"handled": bool, "spoken": str, ...}. If no home intent is
recognised the assistant falls through to the LLM brain.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
"""
from __future__ import annotations
import re

from app.config import settings

_COLORS = {
    "red": (255, 0, 0), "green": (0, 255, 0), "blue": (0, 0, 255), "white": (255, 255, 255),
    "warm": (255, 180, 100), "cyan": (0, 210, 255), "purple": (160, 90, 240),
    "orange": (255, 140, 0), "pink": (255, 90, 160), "yellow": (255, 220, 40),
}


class HomeController:
    def __init__(self) -> None:
        self._ha = None; self._hue = None; self._mqtt = None
        self._ha_tried = self._hue_tried = self._mqtt_tried = False

    # ---------- lazy backends ----------
    def _ha_client(self):
        if self._ha_tried:
            return self._ha
        self._ha_tried = True
        if settings.ha_url and settings.ha_token:
            try:
                from homeassistant_api import Client
                self._ha = Client(settings.ha_url.rstrip("/") + "/api", settings.ha_token)
            except Exception:
                self._ha = None
        return self._ha

    def _hue_bridge(self):
        if self._hue_tried:
            return self._hue
        self._hue_tried = True
        if settings.hue_bridge:
            try:
                from phue import Bridge
                b = Bridge(settings.hue_bridge); b.connect()
                self._hue = b
            except Exception:
                self._hue = None
        return self._hue

    def _mqtt_pub(self, topic: str, payload: str) -> bool:
        if not settings.mqtt_host:
            return False
        try:
            import paho.mqtt.publish as publish
            publish.single(topic, payload, hostname=settings.mqtt_host, port=settings.mqtt_port)
            return True
        except Exception:
            return False

    def status(self) -> dict:
        return {"ha": bool(settings.ha_url and settings.ha_token), "hue": bool(settings.hue_bridge),
                "cast": bool(settings.chromecast_name), "mqtt": bool(settings.mqtt_host)}

    # ---------- actions ----------
    def _lights(self, on: bool, color=None, entity: str | None = None) -> str:
        hue = self._hue_bridge()
        if hue is not None:
            try:
                for lid in hue.get_light_objects("id"):
                    hue.set_light(lid, "on", on)
                    if on and color:
                        hue.set_light(lid, "xy", _rgb_to_xy(*color))
                return f"Okay, lights {'on' if on else 'off'}" + (f", {_name(color)}" if (on and color) else "") + "."
            except Exception:
                pass
        ha = self._ha_client()
        if ha is not None:
            try:
                dom = "light"
                svc = "turn_on" if on else "turn_off"
                data = {"entity_id": entity or "light.all", "rgb_color": list(color)} if (on and color) else {"entity_id": entity or "all"}
                ha.trigger_service(dom, svc, **data)
                return f"Okay, lights {'on' if on else 'off'}."
            except Exception:
                pass
        # generic MQTT fallback for ESP32 relays
        if self._mqtt_pub("ionity/lights", "on" if on else "off"):
            return f"Okay, lights {'on' if on else 'off'}."
        return "I couldn't reach your lights — set up Home Assistant, a Hue bridge, or MQTT."

    def _media(self, verb: str, query: str = "") -> str:
        name = settings.chromecast_name
        if name:
            try:
                import pychromecast
                chromecasts, browser = pychromecast.get_chromecasts()
                cc = next((c for c in chromecasts if c.name.lower() == name.lower()), None)
                if cc:
                    cc.wait(timeout=6); mc = cc.media_controller
                    if verb == "pause": mc.pause()
                    elif verb == "stop": mc.stop()
                    else: mc.play()
                    pychromecast.discovery.stop_discovery(browser)
                    return f"Okay, {verb}."
                pychromecast.discovery.stop_discovery(browser)
            except Exception:
                pass
        ha = self._ha_client()
        if ha is not None:
            try:
                svc = {"play": "media_play", "pause": "media_pause", "stop": "media_stop"}.get(verb, "media_play")
                ha.trigger_service("media_player", svc, entity_id="all")
                return f"Okay, {verb}."
            except Exception:
                pass
        return "I couldn't reach a media player — set up a Cast device or Home Assistant."

    def _scene(self, name: str) -> str:
        ha = self._ha_client()
        if ha is not None:
            try:
                ha.trigger_service("scene", "turn_on", entity_id=f"scene.{name.replace(' ', '_')}")
                return f"Okay, activating {name}."
            except Exception:
                pass
        return f"I couldn't set the {name} scene — Home Assistant isn't configured."

    # ---------- intent parsing ----------
    def parse_and_act(self, text: str) -> dict:
        t = (text or "").lower().strip()
        if not t:
            return {"handled": False}

        # lights
        if re.search(r"\blight", t) or "lamp" in t:
            on = not re.search(r"\b(off|out|kill)\b", t)
            color = next((rgb for w, rgb in _COLORS.items() if w in t), None)
            return {"handled": True, "spoken": self._lights(on, color)}

        # media
        if re.search(r"\b(pause|stop)\b.*\b(music|media|video|playback|song)\b", t) or t in ("pause", "stop"):
            return {"handled": True, "spoken": self._media("pause" if "pause" in t else "stop")}
        if re.search(r"\bplay\b", t) and re.search(r"\b(music|song|media|video|play)\b", t):
            return {"handled": True, "spoken": self._media("play", t)}

        # scenes
        m = re.search(r"\b(?:activate|set|start)\s+(?:the\s+)?([a-z ]+?)\s+scene\b", t)
        if m:
            return {"handled": True, "spoken": self._scene(m.group(1).strip())}

        # generic MQTT command: "publish <topic> <payload>"
        m = re.search(r"\bpublish\s+(\S+)\s+(.+)", t)
        if m:
            ok = self._mqtt_pub(m.group(1), m.group(2))
            return {"handled": True, "spoken": "Sent." if ok else "MQTT isn't configured."}

        return {"handled": False}


def _rgb_to_xy(r, g, b):
    r, g, b = [x / 255.0 for x in (r, g, b)]
    r = ((r + 0.055) / 1.055) ** 2.4 if r > 0.04045 else r / 12.92
    g = ((g + 0.055) / 1.055) ** 2.4 if g > 0.04045 else g / 12.92
    b = ((b + 0.055) / 1.055) ** 2.4 if b > 0.04045 else b / 12.92
    X = r * 0.649926 + g * 0.103455 + b * 0.197109
    Y = r * 0.234327 + g * 0.743075 + b * 0.022598
    Z = r * 0.0000000 + g * 0.053077 + b * 1.035763
    s = X + Y + Z or 1.0
    return [round(X / s, 4), round(Y / s, 4)]


def _name(color):
    for w, rgb in _COLORS.items():
        if rgb == color:
            return w
    return ""
