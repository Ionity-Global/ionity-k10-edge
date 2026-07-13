// WebSocket client to the Edge Brain. © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
#pragma once
#include <Arduino.h>
#include <functional>

// 12-byte binary media header: type(1) seq(4) ts(4) len(4) then payload
enum MediaType : uint8_t { MEDIA_JPEG = 1, MEDIA_AUDIO = 2, MEDIA_SCREEN = 3 };

class WsClient {
public:
  using MsgCb = std::function<void(const String&)>;
  void begin(const String& host, uint16_t port, const char* path);
  void loop();
  bool connected() const;
  void onMessage(MsgCb cb) { _cb = cb; }
  void sendText(const String& s);
  void sendMedia(MediaType t, uint32_t seq, const uint8_t* data, uint32_t len);
  void heartbeat(const String& deviceId, uint32_t seq);
  void onTextInternal(const String& s);   // called by the static WS event shim
private:
  MsgCb _cb;
  bool _connected = false;
};
