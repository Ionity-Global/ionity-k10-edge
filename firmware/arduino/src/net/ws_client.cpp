// © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
#include "ws_client.h"
#include <WebSocketsClient.h>
#include <ArduinoJson.h>

static WebSocketsClient wsock;
static WsClient* self = nullptr;

static void evt(WStype_t type, uint8_t* payload, size_t len) {
  switch (type) {
    case WStype_CONNECTED:    Serial.println("[ws] connected"); break;
    case WStype_DISCONNECTED: Serial.println("[ws] disconnected"); break;
    case WStype_TEXT:
      if (self) { String s; s.reserve(len); for (size_t i=0;i<len;i++) s += (char)payload[i]; self->onTextInternal(s); }
      break;
    default: break;
  }
}

void WsClient::begin(const String& host, uint16_t port, const char* path) {
  self = this;
  wsock.begin(host.c_str(), port, path);
  wsock.onEvent(evt);
  wsock.setReconnectInterval(3000);
  wsock.enableHeartbeat(15000, 3000, 2);
}

void WsClient::loop() { wsock.loop(); _connected = wsock.isConnected(); }
bool WsClient::connected() const { return _connected; }

void WsClient::sendText(const String& s) {
  if (!wsock.isConnected()) return;
  String tmp(s);                     // WebSocketsClient::sendTXT takes a non-const String&
  wsock.sendTXT(tmp);
}

void WsClient::sendMedia(MediaType t, uint32_t seq, const uint8_t* data, uint32_t len) {
  if (!wsock.isConnected()) return;
  // header + payload in one buffer
  uint32_t total = 12 + len;
  uint8_t* buf = (uint8_t*)malloc(total);
  if (!buf) return;
  buf[0] = (uint8_t)t;
  memcpy(buf + 1, &seq, 4);
  uint32_t ts = millis(); memcpy(buf + 5, &ts, 4);
  memcpy(buf + 9, &len, 3);           // 24-bit length is plenty for a frame
  buf[11] = 0;
  memcpy(buf + 12, data, len);
  wsock.sendBIN(buf, total);
  free(buf);
}

void WsClient::heartbeat(const String& deviceId, uint32_t seq) {
  JsonDocument d; d["v"]="1"; d["type"]="hb"; d["device_id"]=deviceId; d["seq"]=seq; d["ts"]=millis();
  String out; serializeJson(d, out); sendText(out);
}

// bridge from static evt() to instance callback
void WsClient::onTextInternal(const String& s) { if (_cb) _cb(s); }
