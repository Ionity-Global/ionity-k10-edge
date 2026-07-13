// WiFi + provisioning (NVS). © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
#pragma once
#include <Arduino.h>

class WifiManager {
public:
  void begin();                 // load provisioned creds from NVS
  void connect();               // join network (blocks with timeout, shows retries)
  void tick();                  // auto-reconnect
  bool isConnected() const;

  String edgeHost();            // provisioned Edge Brain host (NVS) or default
  uint16_t edgePort();

  static String macSuffix();    // last 3 bytes of MAC, hex

  // Called by the installer bridge (serial/BLE) to store credentials.
  static void provision(const String& ssid, const String& pass,
                        const String& host, uint16_t port);
private:
  String _ssid, _pass, _host;
  uint16_t _port = 0;
  uint32_t _lastTry = 0;
};
