// IonityEdge · K10 — VOICE HOME-ASSISTANT NODE v9 (DFRobot UNIHIKER core)
// PURE node: the ESP does NO AI compute. It (1) continuously streams mic audio to the
// server (no push-to-talk), (2) DISPLAYS the full screen the server renders (IONITY logo
// + orb whose colour follows the AI's state/tone + AI glyph + Claude's words), and
// (3) plays the AI's spoken reply through the ESP speaker.
// The SERVER hears the wake word ("Hello"), thinks (Claude / gemma4:e2b), speaks, and
// renders the screen — all on the edge.  © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
#include "unihiker_k10.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
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

static const int FW = 240, FH = 320;
static const uint32_t FRAME_BYTES = (uint32_t)FW * FH * 2;   // 153600 RGB565
static uint8_t* frameBuf = nullptr;
static uint8_t* capBuf = nullptr;

static String urlOf(const char* path) { return String("http://") + EDGE_HOST + ":" + EDGE_PORT + path; }

static void wavHeader(uint8_t* h, uint32_t dataLen, uint32_t sr, uint16_t ch, uint16_t bps) {
  uint32_t byteRate = sr * ch * bps / 8; uint16_t blk = ch * bps / 8; uint32_t chunk = 36 + dataLen;
  memcpy(h, "RIFF", 4);   h[4]=chunk; h[5]=chunk>>8; h[6]=chunk>>16; h[7]=chunk>>24;
  memcpy(h+8, "WAVE", 4); memcpy(h+12, "fmt ", 4);
  h[16]=16; h[17]=0; h[18]=0; h[19]=0;  h[20]=1; h[21]=0;  h[22]=ch; h[23]=0;
  h[24]=sr; h[25]=sr>>8; h[26]=sr>>16; h[27]=sr>>24;
  h[28]=byteRate; h[29]=byteRate>>8; h[30]=byteRate>>16; h[31]=byteRate>>24;
  h[32]=blk; h[33]=0;  h[34]=bps; h[35]=0;
  memcpy(h+36, "data", 4); h[40]=dataLen; h[41]=dataLen>>8; h[42]=dataLen>>16; h[43]=dataLen>>24;
}

// Play the server's TTS reply (16 kHz mono WAV) through the ESP speaker (I2S TX, dup to stereo).
static void playSayWav() {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http; http.begin(urlOf("/api/say.wav")); http.setTimeout(8000);
  int code = http.GET();
  if (code == 200) {
    WiFiClient* st = http.getStreamPtr();
    uint8_t hdr[44]; size_t hn = 0;
    while (hn < 44 && http.connected()) { int r = st->readBytes(hdr + hn, 44 - hn); if (r <= 0) break; hn += r; }
    int16_t mono[256]; int16_t stereo[512]; size_t bw;
    while (http.connected()) {
      int r = st->readBytes((uint8_t*)mono, sizeof(mono));
      if (r <= 0) break;
      int n = r / 2;
      for (int i = 0; i < n; i++) { stereo[2*i] = mono[i]; stereo[2*i+1] = mono[i]; }
      i2s_write(I2S_NUM_0, stereo, n * 4, &bw, portMAX_DELAY);
    }
    i2s_zero_dma_buffer(I2S_NUM_0);
  }
  http.end();
}

// Continuously capture ~2.5 s of mic audio and POST it to the server (server detects wake word).
static void captureAndSend() {
  const uint32_t SR = 16000; const uint16_t CH = 2, BPS = 16; const float SECS = 2.5f;
  const uint32_t dataLen = (uint32_t)(SR * CH * (BPS/8) * SECS);   // 160000
  if (!capBuf) return;
  wavHeader(capBuf, dataLen, SR, CH, BPS);
  size_t got = 0, rd = 0;
  while (got < dataLen) {
    if (i2s_read(I2S_NUM_0, capBuf + 44 + got, (dataLen-got>4096?4096:dataLen-got), &rd, pdMS_TO_TICKS(1000)) != ESP_OK || rd == 0) break;
    got += rd;
  }
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http; http.begin(urlOf("/api/voice-raw"));
  http.addHeader("Content-Type", "audio/wav"); http.setTimeout(30000);
  int code = http.POST(capBuf, 44 + got);
  bool speak = false;
  if (code == 200) {
    String body = http.getString();
    JsonDocument d;
    if (!deserializeJson(d, body)) {
      bool ignored = d["ignored"] | false;
      const char* reply = d["reply"] | "";
      if (!ignored && strlen(reply) > 0) speak = true;
    }
  }
  http.end();
  if (speak) playSayWav();
}

// Audio task (own core): listen -> upload -> (maybe) speak, forever.
static void audioTask(void*) {
  for (;;) { captureAndSend(); vTaskDelay(pdMS_TO_TICKS(40)); }
}

static void showText(const char* t) {
  k10.canvas->canvasRectangle(0, 0, FW, FH, 0x03080F, 0x03080F, true);
  k10.canvas->canvasText("IONITY", 70, 40, 0x2E7DE1, k10.canvas->eCNAndENFont24, 40, true);
  k10.canvas->canvasText(t, 40, 150, 0x7FA6C9, k10.canvas->eCNAndENFont16, 40, true);
  k10.canvas->updateCanvas();
}

void setup() {
  Serial.begin(115200);
  k10.begin(); k10.initScreen(2); k10.creatCanvas(); k10.setScreenBackground(0x03080F);
  k10.rgb->brightness(6); k10.rgb->write(-1, 0x1E7BFF);
  frameBuf = (uint8_t*)heap_caps_malloc(FRAME_BYTES, MALLOC_CAP_SPIRAM);
  capBuf   = (uint8_t*)heap_caps_malloc(44 + 160000, MALLOC_CAP_SPIRAM);
  showText("connecting...");
  WiFi.mode(WIFI_STA); WiFi.begin(WIFI_SSID, WIFI_PASS);
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 15000) delay(200);
  showText(WiFi.status() == WL_CONNECTED ? "say: Hello" : "wifi failed");
  // start the always-on mic streamer on the other core
  xTaskCreatePinnedToCore(audioTask, "audio", 8192, nullptr, 1, nullptr, 0);
}

void loop() {
  // Pure display: pull the full server-rendered screen and blit it (device does no compute).
  if (WiFi.status() == WL_CONNECTED && frameBuf) {
    HTTPClient http; http.begin(urlOf("/api/screen565")); http.setTimeout(6000);
    int code = http.GET();
    if (code == 200) {
      WiFiClient* st = http.getStreamPtr();
      size_t got = 0;
      uint32_t t0 = millis();
      while (got < FRAME_BYTES && (http.connected() || st->available()) && millis() - t0 < 5000) {
        size_t av = st->available();
        if (av) { int r = st->readBytes(frameBuf + got, (FRAME_BYTES - got < av ? FRAME_BYTES - got : av)); if (r > 0) got += r; }
        else delay(1);
      }
      if (got == FRAME_BYTES) {
        k10.canvas->canvasDrawBitmap(0, 0, FW, FH, frameBuf);
        k10.canvas->updateCanvas();
      }
    }
    http.end();
  }
  delay(180);   // ~5 fps
}
