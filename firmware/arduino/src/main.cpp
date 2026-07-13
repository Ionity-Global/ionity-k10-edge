// IonityEdge · K10 — thin-client firmware entrypoint
// The K10 senses, renders and streams; the Edge Brain does the thinking.
// © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
#include <Arduino.h>
#include <ArduinoJson.h>
#include "config.h"
#include "net/wifi_manager.h"
#include "net/ws_client.h"
#include "ui/screen.h"
#include "sensors/sensors.h"
#include "media/media.h"
#include "location/geo.h"

static WifiManager  wifiMgr;
static WsClient      ws;
static Screen        screen;
static Sensors       sensors;
static Media         media;
static Geo           geo;

static uint32_t lastTelemetry = 0, lastHeartbeat = 0, lastScan = 0, seq = 0;
String deviceId;

// ---- Incoming messages from the Edge Brain ----
static void onBrainMessage(const String& text) {
  JsonDocument doc;
  if (deserializeJson(doc, text)) return;
  const char* type = doc["type"] | "";

  if (!strcmp(type, "hello_ack")) {
    screen.setStatus("Brain linked");
  } else if (!strcmp(type, "answer")) {
    screen.showAnswer(doc["payload"]["text"] | "");
    media.speak(doc["payload"]["audio_url"] | "");   // TTS playback (BSP)
  } else if (!strcmp(type, "layout")) {
    screen.applyLayout(doc["payload"]);               // buttons/labels from brain
  } else if (!strcmp(type, "ad") || !strcmp(type, "notify")) {
    screen.showNotice(doc["payload"]["title"] | "", doc["payload"]["body"] | "");
  } else if (!strcmp(type, "cmd")) {
    const char* c = doc["payload"]["cmd"] | "";
    if (!strcmp(c, "record_start")) media.startRecording();
    else if (!strcmp(c, "record_stop")) media.stopRecording();
    else if (!strcmp(c, "cam_fps")) media.setCamFps(doc["payload"]["fps"] | CAM_TARGET_FPS);
  }
}

// ---- Send the capability handshake ----
static void sendHello() {
  JsonDocument doc;
  doc["v"] = "1"; doc["type"] = "hello"; doc["device_id"] = deviceId;
  doc["seq"] = seq++; doc["ts"] = millis();
  auto p = doc["payload"].to<JsonObject>();
  p["fw"] = IONITY_FW_VERSION; p["project"] = IONITY_PROJECT;
  p["screen_w"] = 320; p["screen_h"] = 240;
  auto caps = p["caps"].to<JsonArray>();
  if (FEAT_SENSORS) caps.add("sensors");
  if (FEAT_CAMERA) caps.add("camera");
  if (FEAT_MIC) caps.add("mic");
  if (FEAT_WAKEWORD) caps.add("wakeword");
  if (FEAT_SD_RECORDING) caps.add("sdrec");
  if (FEAT_GEOLOCATION) caps.add("geo");
  String out; serializeJson(doc, out); ws.sendText(out);
}

static void sendTelemetry() {
  JsonDocument doc;
  doc["v"] = "1"; doc["type"] = "telemetry"; doc["device_id"] = deviceId;
  doc["seq"] = seq++; doc["ts"] = millis();
  auto p = doc["payload"].to<JsonObject>();
  SensorReading r = sensors.read();
  p["temp_c"] = r.tempC; p["humidity"] = r.humidity;
  p["light"] = r.light; p["ax"] = r.ax; p["ay"] = r.ay; p["az"] = r.az;
  p["batt"] = r.battery;
  String out; serializeJson(doc, out); ws.sendText(out);
}

// Accept installer provisioning over USB serial: a line "PROV {json}".
static void checkSerialProvision() {
  if (!Serial.available()) return;
  String line = Serial.readStringUntil('\n');
  if (!line.startsWith("PROV ")) return;
  JsonDocument doc;
  if (deserializeJson(doc, line.substring(5))) return;
  WifiManager::provision(doc["ssid"] | "", doc["pass"] | "",
                         doc["host"] | "", (uint16_t)(doc["port"] | 0));  // reboots
}

void setup() {
  Serial.begin(115200);
  delay(200);
  deviceId = String(IONITY_DEVICE_PREFIX) + "-" + WifiManager::macSuffix();

  screen.begin();
  screen.splash();                 // Ionity logo + "Building Tomorrow, Today"

  // WiFi: prefer NVS-provisioned creds (from installer), else compile-time default.
  screen.setStatus("WiFi…");
  wifiMgr.begin();
  wifiMgr.connect();

  screen.setStatus("Linking Brain…");
  ws.onMessage(onBrainMessage);
  ws.begin(wifiMgr.edgeHost(), wifiMgr.edgePort(), EDGE_WS_PATH);

  if (FEAT_SENSORS) sensors.begin();
  if (FEAT_CAMERA || FEAT_MIC) media.begin(&ws);
  if (FEAT_GEOLOCATION) geo.begin();

  screen.homeGrid();               // draw the Ionity button grid
  sendHello();
}

void loop() {
  ws.loop();
  wifiMgr.tick();
  checkSerialProvision();

  uint32_t now = millis();

  // Button handling -> forward intents to the brain
  int btn = screen.pollButtons();
  if (btn >= 0) {
    JsonDocument doc; doc["v"]="1"; doc["type"]="cmd"; doc["device_id"]=deviceId;
    doc["seq"]=seq++; doc["ts"]=now; doc["payload"]["button"]=btn;
    String out; serializeJson(doc,out); ws.sendText(out);
  }

  if (FEAT_MIC && media.wakeWordDetected()) {
    screen.setStatus("Listening…");
    media.streamMicWhileSpeech();   // pushes audio frames to brain until silence
    screen.setStatus("Thinking…");
  }

  if (FEAT_CAMERA) media.pumpCamera();          // adaptive JPEG frames

  if (now - lastTelemetry >= TELEMETRY_PERIOD_MS) { lastTelemetry = now; if (ws.connected()) sendTelemetry(); }
  if (now - lastHeartbeat >= HEARTBEAT_PERIOD_MS) { lastHeartbeat = now; ws.heartbeat(deviceId, seq++); }
  if (FEAT_GEOLOCATION && now - lastScan >= WIFI_SCAN_PERIOD_MS) { lastScan = now; geo.scanAndSend(&ws, deviceId, seq++); }
}
