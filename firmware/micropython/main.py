# IonityEdge · K10 — MicroPython main demo
# Reads sensors, shows them on-screen, and posts telemetry to the Edge Brain.
# This is the "easy path" for education; the C++ firmware is the production front-end.
# © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
import time
from lib.edge_client import EdgeClient

# The DFRobot UNIHIKER K10 MicroPython BSP exposes the screen + sensors.
# Import guarded so this file still runs on a bare board for structure review.
try:
    from unihiker_k10 import K10          # TODO: match your BSP module name
    k10 = K10()
except Exception as e:
    print("[k10] BSP not found, using stubs:", e)
    k10 = None

EDGE_HOST = "192.168.1.100"               # your PC running the Edge Brain
EDGE_PORT = 8765
DEVICE_ID = "ionity-k10-mpy"

edge = EdgeClient(EDGE_HOST, EDGE_PORT, DEVICE_ID)

def read_sensors():
    if k10:
        return {
            "temp_c": k10.temperature(),
            "humidity": k10.humidity(),
            "light": k10.ambient_light(),
            "accel": k10.accel(),          # (x,y,z)
        }
    # stub values so the loop + upload path are demonstrable without hardware
    return {"temp_c": 24.3, "humidity": 45, "light": 320, "accel": (0.0, 0.0, 1.0)}

def draw(r):
    line = "T:%.1fC H:%d%% L:%d" % (r["temp_c"], r["humidity"], r["light"])
    if k10:
        k10.clear()
        k10.text("IonityEdge K10", 6, 6)
        k10.text(line, 6, 40)
    print("[screen]", line)

print("IonityEdge · K10 (MicroPython) — Building Tomorrow, Today")
while True:
    r = read_sensors()
    draw(r)
    try:
        edge.telemetry(r)                  # HTTP POST to the brain's /ingest
    except Exception as e:
        print("[edge] telemetry failed:", e)
    time.sleep(1)
