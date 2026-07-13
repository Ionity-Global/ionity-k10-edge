# IonityEdge · K10 — MicroPython boot: join WiFi
# © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
import network, time

WIFI_SSID = "Antwerp Ionity"
WIFI_PASS = ""          # leave empty here; set in a local, un-shared copy if needed

def connect(ssid=WIFI_SSID, pw=WIFI_PASS, timeout=20):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected() and ssid:
        print("[wifi] joining", ssid)
        wlan.connect(ssid, pw)
        t0 = time.time()
        while not wlan.isconnected() and time.time() - t0 < timeout:
            time.sleep(0.25)
    if wlan.isconnected():
        print("[wifi] up:", wlan.ifconfig()[0])
    else:
        print("[wifi] not connected (set WIFI_PASS or provision via installer)")
    return wlan

wlan = connect()
