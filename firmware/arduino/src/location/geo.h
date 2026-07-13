// WiFi-based geolocation (moving device, no GPS).
// © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
#pragma once
#include <Arduino.h>
#include "../net/ws_client.h"

class Geo {
public:
  void begin();
  // Scan nearby APs and send BSSID+RSSI list; the Edge Brain resolves coordinates.
  void scanAndSend(WsClient* ws, const String& deviceId, uint32_t seq);
};
