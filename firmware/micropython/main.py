# IonityEdge · K10 — MicroPython NODE
# A real thin node: uploads sensors to the Edge Brain and DISPLAYS the server-computed
# render — orb colour (AI state/tone) as an on-screen swatch + RGB LED, the AI state
# label, and Claude's words. All AI compute stays on the server (same contract as the
# C++ firmware; this path has no audio). © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
import time
from lib.edge_client import EdgeClient

# ---- configure me ----
WIFI_SSID = "Antwerp Ionity"
WIFI_PASS = ""                             # set your WiFi password (never commit it)
EDGE_HOST = "192.168.124.5"                # the PC running the Edge Brain
EDGE_PORT = 8765
DEVICE_ID = "ionity-k10-mpy"

# The DFRobot UNIHIKER K10 MicroPython BSP exposes the screen + sensors.
# Import guarded so this file still runs on a bare board / CPython for review.
try:
    from unihiker_k10 import K10           # adjust to your BSP module name if different
    k10 = K10()
except Exception as e:
    print("[k10] BSP not found, using stubs:", e)
    k10 = None


def wifi_connect():
    try:
        import network
        w = network.WLAN(network.STA_IF)
        w.active(True)
        if not w.isconnected():
            print("[wifi] connecting to", WIFI_SSID)
            w.connect(WIFI_SSID, WIFI_PASS)
            for _ in range(40):
                if w.isconnected():
                    break
                time.sleep(0.5)
        print("[wifi]", w.ifconfig()[0] if w.isconnected() else "FAILED")
        return w.isconnected()
    except Exception as e:
        print("[wifi] unavailable (CPython test run?):", e)
        return True


def read_sensors():
    if k10:
        try:
            return {"temp_c": k10.temperature(), "humidity": k10.humidity(),
                    "light": k10.ambient_light(), "level": 0.0}
        except Exception:
            pass
    return {"temp_c": 24.3, "humidity": 45, "light": 320, "level": 0.0}


def hex_rgb(h):
    try:
        v = int(h, 16)
        return (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF
    except Exception:
        return 30, 123, 255


def apply_state(st, reading):
    """Display exactly what the server computed — the node makes no decisions."""
    color = st.get("color", "1E7BFF")
    label = st.get("label", "IDLE")
    say = st.get("say", "")
    r, g, b = hex_rgb(color)
    if k10:
        try:
            k10.clear()
            k10.text("IONITY", 70, 6)
            k10.fill_rect(90, 60, 60, 60, (r, g, b))       # orb swatch, server colour
            k10.text(label, 8, 140)
            k10.text("T:%.1fC H:%d%% L:%d" % (reading["temp_c"], reading["humidity"], reading["light"]), 8, 170)
            if say:
                k10.text(say[:28], 8, 200)                 # Claude's words
            k10.rgb(0, (r, g, b)); k10.rgb(1, (r, g, b)); k10.rgb(2, (r, g, b))
        except Exception:
            pass
    print("[state] %s #%s say=%r" % (label, color, say[:40]))


print("IonityEdge · K10 (MicroPython node) — Building Tomorrow, Today.")
wifi_connect()
edge = EdgeClient(EDGE_HOST, EDGE_PORT, DEVICE_ID)

while True:
    reading = read_sensors()
    res = edge.telemetry(reading)              # upload -> server computes -> render back
    if res and isinstance(res, dict):
        apply_state(res.get("state") or {}, reading)
    else:
        print("[edge] no response — is the Edge Brain running on %s:%d?" % (EDGE_HOST, EDGE_PORT))
    time.sleep(0.5)
