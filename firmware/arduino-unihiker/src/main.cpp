// IonityEdge · K10 — SENSORY FRONTEND NODE v7 (DFRobot UNIHIKER core)
// The node uploads raw sensor data; the SERVER (Edge Brain) computes the mood, colour,
// LED states, LED brightness and frame rate and returns them in the /ingest response.
// The device simply DISPLAYS the server's render — everything is live and centrally
// tunable at localhost with NO reflash. Also hosts its own tiny web server
// (http://<device-ip>/) mirroring the same server-driven state, and periodically
// uploads a WiFi scan (aps) so the Edge Brain can geolocate the moving device.
// © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
#include "unihiker_k10.h"
#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <math.h>

#if __has_include("secrets.h")
  #include "secrets.h"
#endif
#ifndef WIFI_SSID
#define WIFI_SSID "Antwerp Ionity"
#endif
#ifndef WIFI_PASS
#define WIFI_PASS ""
#endif
#ifndef EDGE_HOST
#define EDGE_HOST "192.168.124.5"
#endif
#ifndef EDGE_PORT
#define EDGE_PORT 8765
#endif
// Extra K10 hardware is OFF by default so the build never breaks on a BSP that
// lacks the API. Flip to 1 once you've confirmed the method names for your library.
#ifndef USE_K10_BUTTONS
#define USE_K10_BUTTONS 0
#endif
#ifndef USE_K10_ACCEL
#define USE_K10_ACCEL 0
#endif

UNIHIKER_K10 k10;
AHT20 aht20;
WebServer web(80);

static const int SW = 240, SH = 320, CX = 120, CY = 132;
static const uint32_t BG = 0x03080F;

// ---- server-computed render (device just displays these) ----
static uint32_t gOrb = 0x1E7BFF, gLeds[3] = {0, 0, 0};
static float gLevel = 0; static int gRadius = 40; static char gLabel[16] = "CALM";
static uint8_t gBright = 6;      // LED brightness from the server (0..9), live-tunable
static uint32_t gFps = 35;       // frame delay in ms from the server, live-tunable
static char gSay[120] = "";      // Claude / brain reply, streamed from the server (readback)
// ---- local sensor state (uploaded to the server) ----
static float gTemp = 0, gHum = 0, micMax = 2000, level = 0, levelSmooth = 0, phase = 0;
static uint16_t gAls = 0; static uint32_t gSound = 0;
static uint32_t lastPost = 0; static bool webUp = false;
// ---- WiFi scan (feeds server geolocation) ----
static String gAps = "";                 // JSON array of {bssid,rssi}, most-recent scan
static uint32_t lastScan = 0; static bool scanRunning = false;

static uint32_t hex2u32(const char* s) { return s ? (uint32_t)strtol(s, nullptr, 16) : 0; }

// Non-blocking WiFi scan: kick off async, harvest when done, keep the top-6 APs.
static void maybeScan(uint32_t now) {
  if (WiFi.status() != WL_CONNECTED) return;
  if (!scanRunning && (lastScan == 0 || now - lastScan > 60000)) {
    WiFi.scanNetworks(/*async=*/true, /*show_hidden=*/false);
    scanRunning = true;
    return;
  }
  if (scanRunning) {
    int n = WiFi.scanComplete();
    if (n >= 0) {
      String s = "[";
      int lim = n < 6 ? n : 6;
      for (int i = 0; i < lim; i++) {
        if (i) s += ",";
        s += "{\"bssid\":\"" + WiFi.BSSIDstr(i) + "\",\"rssi\":" + String(WiFi.RSSI(i)) + "}";
      }
      s += "]";
      gAps = s;
      WiFi.scanDelete();
      scanRunning = false; lastScan = now;
    } else if (n == WIFI_SCAN_FAILED) {
      scanRunning = false; lastScan = now;
    }
  }
}

static String liveJson() {
  char b[320];
  snprintf(b, sizeof(b),
    "{\"device\":\"ionity-k10\",\"ip\":\"%s\",\"temp_c\":%.1f,\"humidity\":%.0f,\"light\":%u,"
    "\"level\":%.3f,\"mood_label\":\"%s\",\"color\":\"%06X\",\"brightness\":%u,\"rssi\":%d}",
    WiFi.localIP().toString().c_str(), gTemp, gHum, gAls, gLevel, gLabel,
    gOrb & 0xFFFFFF, gBright, WiFi.RSSI());
  return String(b);
}
static void handleLive() { web.send(200, "application/json", liveJson()); }
static void handleRoot() {
  String h = "<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
    "<title>IonityEdge K10</title><style>body{margin:0;background:#03080f;color:#eaf6ff;font-family:system-ui;text-align:center}"
    ".orb{width:150px;height:150px;border-radius:50%;margin:26px auto;transition:.4s}h1{color:#00d2ff;letter-spacing:1px}.k{color:#7fa6c9}</style>"
    "</head><body><h1>IONITY &middot; ORB</h1><div id=o class=orb></div><div id=t></div>"
    "<p class=k>on-device node &middot; colour computed by the Edge Brain &middot; Policy 986 AED</p>"
    "<script>async function u(){let d=await (await fetch('/live')).json();let o=document.getElementById('o');"
    "let s=80+d.level*130;o.style.width=o.style.height=s+'px';let c='#'+d.color;o.style.background=c;o.style.boxShadow='0 0 44px '+c;"
    "document.getElementById('t').innerHTML='MOOD '+d.mood_label+'<br>Temp '+d.temp_c+'C &middot; Light '+d.light+' &middot; Sound '+Math.round(d.level*100)+'%';}"
    "setInterval(u,400);u();</script></body></html>";
  web.send(200, "text/html", h);
}

// upload sensors (+ optional WiFi scan), receive the server's render
static void syncWithServer() {
  HTTPClient http;
  http.begin(String("http://") + EDGE_HOST + ":" + EDGE_PORT + "/ingest");
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(1500);
  String body = String("{\"device_id\":\"ionity-k10\",\"telemetry\":{\"temp_c\":") + gTemp +
    ",\"humidity\":" + gHum + ",\"light\":" + gAls + ",\"sound\":" + gSound +
    ",\"level\":" + levelSmooth + ",\"ip\":\"" + WiFi.localIP().toString() + "\"";
  if (gAps.length()) { body += ",\"aps\":" + gAps; }
  body += "}}";
  int code = http.POST(body);
  if (code == 200) {
    JsonDocument d;
    if (!deserializeJson(d, http.getString())) {
      JsonObject s = d["state"];
      if (!s.isNull()) {
        gOrb = hex2u32(s["color"] | "1E7BFF");
        gLevel = s["level"] | levelSmooth;
        gRadius = s["radius"] | gRadius;
        gBright = (uint8_t)(s["brightness"] | (int)gBright);
        gFps = (uint32_t)(s["fps_ms"] | (int)gFps);
        strncpy(gLabel, s["label"] | "CALM", sizeof(gLabel) - 1);
        JsonArray leds = s["leds"];
        for (int i = 0; i < 3 && i < (int)leds.size(); i++) gLeds[i] = hex2u32(leds[i] | "000000");
        strncpy(gSay, s["say"] | "", sizeof(gSay) - 1); gSay[sizeof(gSay) - 1] = 0;
      }
    }
  }
  http.end();
}

void setup() {
  Serial.begin(115200);
  k10.begin(); k10.initScreen(2); k10.creatCanvas(); k10.setScreenBackground(BG);
  k10.rgb->brightness(6); k10.rgb->write(-1, 0x1E7BFF);
  WiFi.mode(WIFI_STA); WiFi.begin(WIFI_SSID, WIFI_PASS);
}

void loop() {
  uint32_t now = millis();
  if (webUp) web.handleClient();

  // sensory frontend: read + compute upload level (NOT colour)
  uint64_t mic = k10.readMICData();
  gTemp = aht20.getData(AHT20::eAHT20TempC);
  gHum  = aht20.getData(AHT20::eAHT20HumiRH);
  gAls  = k10.readALS();
  gSound = (uint32_t)mic;
  float m = (float)mic; micMax = micMax * 0.992f; if (m > micMax) micMax = m; if (micMax < 1200) micMax = 1200;
  level = m / micMax; if (level > 1) level = 1; levelSmooth = levelSmooth * 0.65f + level * 0.35f;

#if USE_K10_BUTTONS
  // Best-effort: forward a button press as a dispatch hint (enable once API confirmed).
  // if (k10.buttonA->isPressed()) { /* POST /api/dispatch {command:"read"} */ }
#endif
#if USE_K10_ACCEL
  // Best-effort: read accelerometer into telemetry (enable once API confirmed).
  // float ax = k10.getAccelerometerX(); ...
#endif

  // display the SERVER's render
  phase += 0.16f; float breathe = 0.5f + 0.5f * sinf(phase);
  int r = gRadius + (int)(breathe * 7);
  k10.canvas->canvasRectangle(0, 0, SW, SH, BG, BG, true);
  k10.canvas->canvasText("IONITY  ORB", 10, 8, 0x00D2FF, k10.canvas->eCNAndENFont24, 40, true);
  k10.canvas->canvasCircle(CX, CY, r + 26, ((gOrb >> 1) & 0x7F7F7F), BG, false);
  k10.canvas->canvasCircle(CX, CY, r, gOrb, gOrb, true);
  k10.canvas->canvasCircle(CX - r / 3, CY - r / 3, (r / 5) > 3 ? r / 5 : 3, 0xFFFFFF, 0xFFFFFF, true);
  char ln[80];
  snprintf(ln, sizeof(ln), "MOOD  %s", gLabel); k10.canvas->canvasText(ln, 12, 230, gOrb, k10.canvas->eCNAndENFont16, 40, true);
  snprintf(ln, sizeof(ln), "TEMP %.1fC  LIGHT %u", gTemp, gAls); k10.canvas->canvasText(ln, 12, 252, 0x7FA6C9, k10.canvas->eCNAndENFont16, 40, true);
  int bars = (int)(gLevel * 18); char snd[26] = "SOUND "; for (int i = 0; i < 18; i++) snd[6 + i] = i < bars ? '|' : '.'; snd[24] = 0;
  k10.canvas->canvasText(snd, 12, 274, gOrb, k10.canvas->eCNAndENFont16, 30, true);
  // Claude readback segment (server streams the reply here)
  snprintf(ln, sizeof(ln), "CLAUDE: %s", gSay[0] ? gSay : "-");
  k10.canvas->canvasText(ln, 12, 298, 0x00D2FF, k10.canvas->eCNAndENFont16, 60, true);
  k10.canvas->updateCanvas();

  // LEDs from the server's render (brightness is server-tuned, live)
  k10.rgb->brightness(gBright);
  for (int i = 0; i < 3; i++) k10.rgb->write(i, gLeds[i]);

  if (!webUp && WiFi.status() == WL_CONNECTED) { web.on("/", handleRoot); web.on("/live", handleLive); web.begin(); webUp = true; Serial.printf("[web] http://%s/\n", WiFi.localIP().toString().c_str()); }

  maybeScan(now);   // periodic non-blocking WiFi scan -> aps for geolocation

  // upload sensors + get the server render ~3x/sec (colour + brightness live from the server)
  if (now - lastPost > 300 && WiFi.status() == WL_CONNECTED) { lastPost = now; syncWithServer(); }

  delay(gFps > 0 ? gFps : 35);   // server-tuned frame delay
}
