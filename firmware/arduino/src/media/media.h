// Camera + mic + SD recording. © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
#pragma once
#include <Arduino.h>
#include "../net/ws_client.h"

class Media {
public:
  void begin(WsClient* ws);
  void pumpCamera();                 // grab + stream a JPEG frame at target fps
  void setCamFps(int fps);
  bool wakeWordDetected();           // on-device VAD/keyword
  void streamMicWhileSpeech();       // push audio frames until silence
  void speak(const String& audioUrl);   // TTS playback from the brain
  void startRecording();             // to microSD
  void stopRecording();
private:
  WsClient* _ws = nullptr;
  int _camFps = 8;
  uint32_t _lastCam = 0, _seq = 0;
  bool _recording = false;
};
