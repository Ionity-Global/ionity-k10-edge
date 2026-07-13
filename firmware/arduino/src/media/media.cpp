// © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
// Binds to the DFRobot K10 camera/mic/speaker + microSD. The streaming plumbing
// (frame headers, WS send, fps budget) is complete; capture calls are marked TODO.
#include "media.h"
#include "../../include/config.h"

void Media::begin(WsClient* ws) {
  _ws = ws;
  // TODO: camera.begin(320x240, JPEG, quality=CAM_JPEG_QUALITY);
  // TODO: i2s mic init @ AUDIO_SAMPLE_RATE; i2s speaker init; SD.begin();
}

void Media::setCamFps(int fps) { _camFps = max(1, min(fps, 15)); }

void Media::pumpCamera() {
  if (!_ws || !_ws->connected()) return;
  uint32_t interval = 1000 / max(1, _camFps);
  if (millis() - _lastCam < interval) return;
  _lastCam = millis();
  // TODO: camera_fb_t* fb = esp_camera_fb_get();
  //       _ws->sendMedia(MEDIA_JPEG, _seq++, fb->buf, fb->len);
  //       esp_camera_fb_return(fb);
  // Placeholder no-op frame so the loop timing is real:
  static const uint8_t stub[2] = {0xFF, 0xD8};
  _ws->sendMedia(MEDIA_JPEG, _seq++, stub, sizeof(stub));
}

bool Media::wakeWordDetected() {
  // TODO: on-device keyword/VAD (K10 TinyML). Return true on "Ionity…".
  return false;
}

void Media::streamMicWhileSpeech() {
  if (!_ws) return;
  // TODO: read I2S frames (AUDIO_FRAME_MS) and stream until trailing silence.
  //   while (speech) { i2s_read(buf); _ws->sendMedia(MEDIA_AUDIO, _seq++, buf, n); }
}

void Media::speak(const String& audioUrl) {
  if (audioUrl.isEmpty()) return;
  // TODO: fetch/stream TTS audio from the brain and play via I2S speaker.
}

void Media::startRecording() {
  _recording = true;
  // TODO: open a .wav/.mjpeg file on microSD, tee frames into it.
}

void Media::stopRecording() {
  _recording = false;
  // TODO: close file, notify brain of the artefact path for indexing.
}
