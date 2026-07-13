// © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
#include "wifi_manager.h"
#include <WiFi.h>
#include <Preferences.h>
#include "config.h"

static Preferences prefs;

void WifiManager::begin() {
  prefs.begin("ionity", true); // read-only
  _ssid = prefs.getString("ssid", WIFI_SSID);
  _pass = prefs.getString("pass", WIFI_PASS);
  _host = prefs.getString("edge_host", EDGE_HOST_DEFAULT);
  _port = prefs.getUShort("edge_port", EDGE_PORT_DEFAULT);
  prefs.end();
  WiFi.mode(WIFI_STA);
  WiFi.setHostname((String(IONITY_DEVICE_PREFIX) + "-" + macSuffix()).c_str());
}

void WifiManager::connect() {
  if (_ssid.isEmpty()) { Serial.println("[wifi] no SSID; awaiting provisioning"); return; }
  Serial.printf("[wifi] joining %s\n", _ssid.c_str());
  WiFi.begin(_ssid.c_str(), _pass.c_str());
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 20000) { delay(250); Serial.print('.'); }
  Serial.println();
  if (isConnected()) Serial.printf("[wifi] up: %s\n", WiFi.localIP().toString().c_str());
  else Serial.println("[wifi] failed; will retry");
}

void WifiManager::tick() {
  if (!isConnected() && millis() - _lastTry > 10000) { _lastTry = millis(); WiFi.reconnect(); }
}

bool WifiManager::isConnected() const { return WiFi.status() == WL_CONNECTED; }
String WifiManager::edgeHost() { return _host.isEmpty() ? String(EDGE_HOST_DEFAULT) : _host; }
uint16_t WifiManager::edgePort() { return _port ? _port : EDGE_PORT_DEFAULT; }

String WifiManager::macSuffix() {
  uint8_t mac[6]; WiFi.macAddress(mac);
  char buf[7]; snprintf(buf, sizeof(buf), "%02X%02X%02X", mac[3], mac[4], mac[5]);
  return String(buf);
}

void WifiManager::provision(const String& ssid, const String& pass,
                            const String& host, uint16_t port) {
  Preferences p; p.begin("ionity", false);
  p.putString("ssid", ssid); p.putString("pass", pass);
  if (host.length()) p.putString("edge_host", host);
  if (port) p.putUShort("edge_port", port);
  p.end();
  Serial.println("[wifi] provisioned; rebooting");
  delay(300); ESP.restart();
}
