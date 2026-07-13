// IonityEdge · K10 — VOICE HOME-ASSISTANT NODE v8 (DFRobot UNIHIKER core)
// The node is a far-field mic + display. The SERVER (Edge Brain) is the brain:
//   - The node UPLOADS sensors (/ingest) and DISPLAYS the server's render — the orb
//     colour/LEDs follow the AI's STATE + TONE, and Claude's words show on-screen.
//   - Press BUTTON A to talk: the node captures ~3 s of 16 kHz PCM from the mic (I2S,
//     already initialised by the BSP — no SD card) and POSTs it to /api/voice-raw.
//     The server does STT -> Claude (Google login, no API key) / gemma4:e2b -> reply,
//     and the reply appears on the next /ingest poll (text + tone colour).
// Everything else is centrally tunable at localhost with no reflash.
// © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
#include "unihiker_k10.h"
#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <math.h>
#include "driver/i2s.h"
#include "esp_heap_caps.h"

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

UNIHIKER_K10 k10;
AHT20 aht20;
WebServer web(80);

static const int SW = 240, SH = 320, CX = 120, CY = 132;
static const uint32_t BG = 0x03080F;

// ---- server-computed render (device just displays these) ----
static uint32_t gOrb = 0x1E7BFF, gLeds[3] = {0, 0, 0};
static float gLevel = 0; static int gRadius = 40; static char gLabel[16] = "CALM";
static uint8_t gBright = 6; static uint32_t gFps = 35;
static char gSay[120] = "";
// ---- local sensor state (uploaded to the server) ----
static float gTemp = 0, gHum = 0, micMax = 2000, level = 0, levelSmooth = 0, phase = 0;
static uint16_t gAls = 0; static uint32_t gSound = 0;
static uint32_t lastPost = 0; static bool webUp = false; static bool lastBtn = false;
static String gAps = ""; static uint32_t lastScan = 0; static bool scanRunning = false;

static uint32_t hex2u32(const char* s) { return s ? (uint32_t)strtol(s, nullptr, 16) : 0; }

// ---- WAV header (44 bytes, PCM) ----
static void wavHeader(uint8_t* h, uint32_t dataLen, uint32_t sr, uint16_t ch, uint16_t bps) {
  uint32_t byteRate = sr * ch * bps / 8; uint16_t blockAlign = ch * bps / 8; uint32_t chunk = 36 + dataLen;
  memcpy(h, "RIFF", 4);   h[4]=chunk; h[5]=chunk>>8; h[6]=chunk>>16; h[7]=chunk>>24;
  memcpy(h+8, "WAVE", 4); memcpy(h+12, "fmt ", 4);
  h[16]=16; h[17]=0; h[18]=0; h[19]=0;  h[20]=1; h[21]=0;  h[22]=ch; h[23]=0;
  h[24]=sr; h[25]=sr>>8; h[26]=sr>>16; h[27]=sr>>24;
  h[28]=byteRate; h[29]=byteRate>>8; h[30]=byteRate>>16; h[31]=byteRate>>24;
  h[32]=blockAlign; h[33]=0;  h[34]=bps; h[35]=0;
  memcpy(h+36, "data", 4); h[40]=dataLen; h[41]=dataLen>>8; h[42]=dataLen>>16; h[43]=dataLen>>24;
}

// ---- push-to-talk: capture ~3s from the mic (I2S, already running) -> POST /api/voice-raw ----
static void captureAndSend() {
  const uint32_t SR = 16000; const uint16_t CH = 2, BPS = 16; const uint32_t SECS = 3;
  const uint32_t dataLen = SR * CH * (BPS / 8) * SECS;   // 192000 bytes
  uint8_t* buf = (uint8_t*)heap_caps_malloc(44 + dataLen, MALLOC_CAP_SPIRAM);
  if (!buf) buf = (uint8_t*)malloc(44 + dataLen);
  if (!buf) return;                                      // out of memory — bail, display unaffected
  wavHeader(buf, dataLen, SR, CH, BPS);

  k10.canvas->canvasRectangle(0, 0, SW, SH, BG, BG, true);
  k10.canvas->canvasText("LISTENING", 12, 130, 0x00D2FF, k10.canvas->eCNAndENFont24, 40, true);
  k10.canvas->canvasText("talk now...", 12, 164, 0x7FA6C9, k10.canvas->eCNAndENFont16, 40, true);
  k10.canvas->updateCanvas();

  size_t got = 0, rd = 0;
  while (got < dataLen) {
    esp_err_t e = i2s_read(I2S_NUM_0, buf + 44 + got,
                           (dataLen - got > 4096 ? 4096 : dataLen - got), &rd, pdMS_TO_TICKS(1000));
    if (e != ESP_OK || rd == 0) break;
    got += rd;
  }

  k10.canvas->canvasText("thinking...", 12, 196, 0xB06CF0, k10.canvas->eCNAndENFont16, 40, true);
  k10.canvas->updateCanvas();

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(String("http://") + EDGE_HOST + ":" + EDGE_PORT + "/api/voice-raw");
    http.addHeader("Content-Type", "audio/wav");
    http.setTimeout(25000);
    http.POST(buf, 44 + got);
    http.end();
  }
  free(buf);
  lastPost = 0;   // force an immediate /ingest so the reply shows fast
}

static void maybeScan(uint32_t now) {
  if (WiFi.status() != WL_CONNECTED) return;
  if (!scanRunning && (lastScan == 0 || now - lastScan > 60000)) { WiFi.scanNetworks(true, false); scanRunning = true; return; }
  if (scanRunning) {
    int n = WiFi.scanComplete();
    if (n >= 0) {
      String s = "["; int lim = n < 6 ? n : 6;
      for (int i = 0; i < lim; i++) { if (i) s += ","; s += "{\"bssid\":\"" + WiFi.BSSIDstr(i) + "\",\"rssi\":" + String(WiFi.RSSI(i)) + "}"; }
      s += "]"; gAps = s; WiFi.scanDelete(); scanRunning = false; lastScan = now;
    } else if (n == WIFI_SCAN_FAILED) { scanRunning = false; lastScan = now; }
  }
}

static String liveJson() {
  char b[320];
  snprintf(b, sizeof(b),
    "{\"device\":\"ionity-k10\",\"ip\":\"%s\",\"temp_c\":%.1f,\"humidity\":%.0f,\"light\":%u,"
    "\"level\":%.3f,\"mood_label\":\"%s\",\"color\":\"%06X\",\"brightness\":%u,\"rssi\":%d}",
    WiFi.localIP().toString().c_str(), gTemp, gHum, gAls, gLevel, gLabel, gOrb & 0xFFFFFF, gBright, WiFi.RSSI());
  return String(b);
}
static void handleLive() { web.send(200, "application/json", liveJson()); }
static void handleRoot() {
  String h = "<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
    "<title>IonityEdge K10</title><style>body{margin:0;background:#03080f;color:#eaf6ff;font-family:system-ui;text-align:center}"
    ".orb{width:150px;height:150px;border-radius:50%;margin:26px auto;transition:.4s}h1{color:#00d2ff;letter-spacing:1px}.k{color:#7fa6c9}</style>"
    "</head><body><h1>IONITY &middot; ORB</h1><div id=o class=orb></div><div id=t></div>"
    "<p class=k>voice node &middot; press A to talk &middot; colour from the Edge Brain &middot; Policy 986 AED</p>"
    "<script>async function u(){let d=await (await fetch('/live')).json();let o=document.getElementById('o');"
    "let s=80+d.level*130;o.style.width=o.style.height=s+'px';let c='#'+d.color;o.style.background=c;o.style.boxShadow='0 0 44px '+c;"
    "document.getElementById('t').innerHTML='MOOD '+d.mood_label+'<br>Temp '+d.temp_c+'C &middot; Light '+d.light+' &middot; Sound '+Math.round(d.level*100)+'%';}"
    "setInterval(u,400);u();</script></body></html>";
  web.send(200, "text/html", h);
}

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

  // push-to-talk on Button A (edge-triggered)
  bool btn = false;
  if (k10.buttonA) btn = k10.buttonA->isPressed();
  if (btn && !lastBtn) captureAndSend();
  lastBtn = btn;

  // sensory frontend: read + compute upload level (NOT colour)
  uint64_t mic = k10.readMICData();
  gTemp = aht20.getData(AHT20::eAHT20TempC);
  gHum  = aht20.getData(AHT20::eAHT20HumiRH);
  gAls  = k10.readALS();
  gSound = (uint32_t)mic;
  float m = (float)mic; micMax = micMax * 0.992f; if (m > micMax) micMax = m; if (micMax < 1200) micMax = 1200;
  level = m / micMax; if (level > 1) level = 1; levelSmooth = levelSmooth * 0.65f + level * 0.35f;

  // display the SERVER's render (orb colour/LEDs follow the AI state + tone)
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
  k10.canvas->canvasText("[A] talk to Ionity", 12, 274, 0x00D2FF, k10.canvas->eCNAndENFont16, 40, true);
  snprintf(ln, sizeof(ln), "CLAUDE: %s", gSay[0] ? gSay : "-");
  k10.canvas->canvasText(ln, 12, 298, 0x00D2FF, k10.canvas->eCNAndENFont16, 60, true);
  k10.canvas->updateCanvas();

  k10.rgb->brightness(gBright);
  for (int i = 0; i < 3; i++) k10.rgb->write(i, gLeds[i]);

  if (!webUp && WiFi.status() == WL_CONNECTED) { web.on("/", handleRoot); web.on("/live", handleLive); web.begin(); webUp = true; Serial.printf("[web] http://%s/\n", WiFi.localIP().toString().c_str()); }

  maybeScan(now);
  if (now - lastPost > 300 && WiFi.status() == WL_CONNECTED) { lastPost = now; syncWithServer(); }
  delay(gFps > 0 ? gFps : 35);
}
