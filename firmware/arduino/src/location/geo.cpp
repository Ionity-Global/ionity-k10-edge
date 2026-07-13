// © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
#include "geo.h"
#include <WiFi.h>
#include <ArduinoJson.h>

void Geo::begin() {}

void Geo::scanAndSend(WsClient* ws, const String& deviceId, uint32_t seq) {
  if (!ws || !ws->connected()) return;
  int n = WiFi.scanNetworks(false, true);        // async=false, show hidden
  JsonDocument doc;
  doc["v"] = "1"; doc["type"] = "geo_scan"; doc["device_id"] = deviceId;
  doc["seq"] = seq; doc["ts"] = millis();
  auto aps = doc["payload"]["aps"].to<JsonArray>();
  for (int i = 0; i < n && i < 12; i++) {
    auto ap = aps.add<JsonObject>();
    ap["bssid"] = WiFi.BSSIDstr(i);
    ap["rssi"]  = WiFi.RSSI(i);
    ap["ssid"]  = WiFi.SSID(i);
  }
  WiFi.scanDelete();
  String out; serializeJson(doc, out); ws->sendText(out);
}
