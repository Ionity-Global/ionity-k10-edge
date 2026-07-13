// IonityEdge · K10 — VOICE HOME-ASSISTANT NODE v11 (DFRobot UNIHIKER core)
// Fixes: (1) RESPONSIVE — the display loop is fully decoupled from the network (draws ~50 fps
// from shared state, never blocks on WiFi). (2) The orb/LEDs react LIVE to your voice (mic RMS).
// (3) The AI reply is SPOKEN through the speaker (amp enabled + 16 kHz). (4) The AI logo image
// is back in the orb centre. Continuous listening (no button); wake word "Peper" on the server.
// The device does NO AI compute — the server computes colour/tone and speaks. © Ionity · Policy 986 AED
#include "unihiker_k10.h"
#include "initBoard.h"          // digital_write(eAmp_Gain, ...) — speaker amplifier enable
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "driver/i2s.h"
#include "esp_heap_caps.h"
#include <math.h>
#include "ai_glyph.h"           // AI logo -> big-endian RGB565 (LV_COLOR_16_SWAP=1)
#include "ionity_glyph.h"       // IONITY wordmark -> big-endian RGB565

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
Music music;                    // vendor audio (proven speaker path)
static const int SW = 240, SH = 320, CX = 120, CY = 128;
static const uint32_t BG = 0x03080F;

// shared state (written by the net/audio task, read by the display loop)
static volatile uint32_t gOrb = 0x1E7BFF;
static volatile uint32_t gLeds[3] = {0, 0, 0};
static volatile float gVoice = 0;                 // LIVE mic level 0..1 -> orb reactivity
static volatile int gRadius = 40; static volatile uint8_t gBright = 6;
static char gLabel[16] = "IDLE"; static char gSay[120] = "";
static char gHeard[120] = "";                     // last thing STT transcribed (mic proof)
static uint8_t* capBuf = nullptr;

static uint32_t hex2u32(const char* s) { return s ? (uint32_t)strtol(s, nullptr, 16) : 0; }
static String urlOf(const char* p) { return String("http://") + EDGE_HOST + ":" + EDGE_PORT + p; }

static void wavHeader(uint8_t* h, uint32_t dl, uint32_t sr, uint16_t ch, uint16_t bps) {
  memset(h, 0, 44);              // <-- critical: buffer is not zeroed; unset header bytes were garbage
  uint32_t br = sr*ch*bps/8; uint16_t ba = ch*bps/8; uint32_t ck = 36+dl;
  memcpy(h,"RIFF",4); h[4]=ck;h[5]=ck>>8;h[6]=ck>>16;h[7]=ck>>24; memcpy(h+8,"WAVE",4);
  memcpy(h+12,"fmt ",4); h[16]=16; h[20]=1; h[22]=ch; h[24]=sr;h[25]=sr>>8;h[26]=sr>>16;h[27]=sr>>24;
  h[28]=br;h[29]=br>>8;h[30]=br>>16;h[31]=br>>24; h[32]=ba; h[34]=bps; memcpy(h+36,"data",4);
  h[40]=dl;h[41]=dl>>8;h[42]=dl>>16;h[43]=dl>>24;
}

// Speak the reply through the ESP speaker: enable amp, 16 kHz, dup mono->stereo, then restore.
static void playSay() {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http; http.begin(urlOf("/api/say.wav")); http.setTimeout(9000);
  if (http.GET() == 200) {
    WiFiClient* st = http.getStreamPtr();
    uint8_t hdr[44]; size_t hn = 0;
    while (hn < 44 && http.connected()) { int r = st->readBytes(hdr+hn, 44-hn); if (r<=0) break; hn+=r; }
    uint32_t clk = i2s_get_clk(I2S_NUM_0);
    i2s_set_sample_rates(I2S_NUM_0, 16000);      // same path the vendor playback uses
    int16_t mono[256], stereo[512]; size_t bw;
    while (http.connected()) {
      int r = st->readBytes((uint8_t*)mono, sizeof(mono)); if (r<=0) break;
      int n = r/2; for (int i=0;i<n;i++){ stereo[2*i]=mono[i]; stereo[2*i+1]=mono[i]; }
      i2s_write(I2S_NUM_0, stereo, n*4, &bw, portMAX_DELAY);
    }
    i2s_zero_dma_buffer(I2S_NUM_0);
    i2s_set_sample_rates(I2S_NUM_0, clk);
  }
  http.end();
}

// Startup chime via the VENDOR audio path — if you HEAR it, the speaker works (code-side).
static void bootBeep() {
  music.playTone(784, 1600);
  music.playTone(1046, 2200);
}

static void syncWithServer() {
  HTTPClient http; http.begin(urlOf("/ingest"));
  http.addHeader("Content-Type", "application/json"); http.setTimeout(1200);
  String body = String("{\"device_id\":\"ionity-k10\",\"telemetry\":{\"level\":") + gVoice +
    ",\"ip\":\"" + WiFi.localIP().toString() + "\"}}";
  if (http.POST(body) == 200) {
    JsonDocument d;
    if (!deserializeJson(d, http.getString())) {
      JsonObject s = d["state"];
      if (!s.isNull()) {
        gOrb = hex2u32(s["color"] | "1E7BFF");
        gRadius = s["radius"] | (int)gRadius;
        gBright = (uint8_t)(s["brightness"] | (int)gBright);
        strncpy(gLabel, s["label"] | "IDLE", sizeof(gLabel)-1);
        JsonArray leds = s["leds"]; for (int i=0;i<3 && i<(int)leds.size();i++) gLeds[i]=hex2u32(leds[i]|"000000");
        strncpy(gSay, s["say"] | "", sizeof(gSay)-1); gSay[sizeof(gSay)-1]=0;
      }
    }
  }
  http.end();
}

// Continuous mic: capture in small chunks (live RMS -> gVoice), then POST an utterance; speak reply.
static void netAudioTask(void*) {
  const uint32_t SR=16000; const uint16_t CH=2; const int CHUNK=3200*CH; // ~100 ms stereo bytes
  const int CHUNKS=16;                                                    // ~1.6 s utterance
  const uint32_t dl = (uint32_t)CHUNK*CHUNKS;
  float micMax = 1500;
  for (;;) {
    if (WiFi.status()!=WL_CONNECTED || !capBuf) { vTaskDelay(pdMS_TO_TICKS(300)); continue; }
    syncWithServer();                                  // refresh orb colour/label/say (~every cycle)
    size_t off=0, rd=0;
    for (int c=0;c<CHUNKS;c++){
      if (i2s_read(I2S_NUM_0, capBuf+44+off, CHUNK, &rd, pdMS_TO_TICKS(400))!=ESP_OK || rd==0) break;
      // live RMS of this chunk -> gVoice (drives the orb pulse & LED brightness)
      int16_t* s=(int16_t*)(capBuf+44+off); int ns=rd/2; double acc=0;
      for (int i=0;i<ns;i+=CH){ double v=s[i]; acc+=v*v; }
      double rms=sqrt(acc/(ns/CH>0?ns/CH:1));
      if (rms>micMax) micMax=rms; micMax*=0.999; if (micMax<1200) micMax=1200;
      float lv=(float)(rms/micMax); if(lv>1)lv=1; gVoice = gVoice*0.5f + lv*0.5f;
      off+=rd;
    }
    HTTPClient http; http.begin(urlOf("/api/voice-raw"));
    http.addHeader("Content-Type","audio/wav"); http.setTimeout(30000);
    int code=http.POST(capBuf, 44+off); bool speak=false;
    if (code==200){ JsonDocument d; if(!deserializeJson(d,http.getString())){
      bool ig=d["ignored"]|false; const char* rp=d["reply"]|""; if(!ig&&strlen(rp)>0) speak=true;
      const char* tr=d["transcript"]|""; if(strlen(tr)>0){ strncpy(gHeard,tr,sizeof(gHeard)-1); gHeard[sizeof(gHeard)-1]=0; } } }
    http.end();
    gVoice = 0;
    if (speak) playSay();
    vTaskDelay(pdMS_TO_TICKS(20));
  }
}

void setup() {
  Serial.begin(115200);
  k10.begin(); k10.initScreen(2); k10.creatCanvas(); k10.setScreenBackground(BG);
  k10.rgb->brightness(6); k10.rgb->write(-1, 0x1E7BFF);
  capBuf = (uint8_t*)heap_caps_malloc(44+160000, MALLOC_CAP_SPIRAM);
  if (!capBuf) capBuf = (uint8_t*)malloc(44+160000);
  digital_write(eAmp_Gain, 1);   // enable MIC input gain (needed for usable capture level)
  bootBeep();                    // audible speaker self-test on power-up
  WiFi.mode(WIFI_STA); WiFi.begin(WIFI_SSID, WIFI_PASS);
  xTaskCreatePinnedToCore(netAudioTask, "net", 10240, nullptr, 1, nullptr, 0);
}

void loop() {
  // DISPLAY ONLY — never blocks on WiFi/I2S, so it's always smooth.
  float vl = gVoice; uint32_t orb = gOrb;
  static float ph = 0; ph += 0.22f; float breathe = 0.5f + 0.5f*sinf(ph);
  int r = (int)gRadius + (int)(vl*34) + (int)(breathe*6);           // pulse reacts to your voice
  k10.canvas->canvasRectangle(0,0,SW,SH,BG,BG,true);
  // IONITY logo (image) at the top
  k10.canvas->canvasDrawBitmap(CX-ION_W/2, 6, ION_W, ION_H, ION_GLYPH);
  k10.canvas->canvasCircle(CX, CY, r+22, ((orb>>1)&0x7F7F7F), BG, false);
  k10.canvas->canvasCircle(CX, CY, r, orb, orb, true);
  // transparent AI logo (image) on a dark disc in the orb centre
  int dr = r*0.66 > AI_W/2 ? (int)(r*0.66) : AI_W/2;
  k10.canvas->canvasCircle(CX, CY, dr, BG, BG, true);
  k10.canvas->canvasDrawBitmap(CX-AI_W/2, CY-AI_H/2, AI_W, AI_H, AI_GLYPH);
  char ln[100];
  // status + WiFi dot
  bool wifi = WiFi.status() == WL_CONNECTED;
  k10.canvas->canvasCircle(224, 12, 5, wifi ? 0x26DE81 : 0xE23B4E, wifi ? 0x26DE81 : 0xE23B4E, true);
  snprintf(ln,sizeof(ln),"%s",gLabel); k10.canvas->canvasText(ln,12,210,orb,k10.canvas->eCNAndENFont16,40,true);
  // LIVE mic meter — moves when you talk (proves the mic is capturing)
  k10.canvas->canvasText("MIC",12,232,0x7FA6C9,k10.canvas->eCNAndENFont16,40,true);
  k10.canvas->canvasRectangle(52,234,170,10,0x0C1826,0x0C1826,true);
  int mw = (int)(vl*170); if(mw<1)mw=1;
  k10.canvas->canvasRectangle(52,234,mw,10,0x00D2FF,0x00D2FF,true);
  // what the server HEARD (proves mic -> WiFi -> STT)
  snprintf(ln,sizeof(ln),"heard: %s", gHeard[0]?gHeard:"(say Peper...)"); k10.canvas->canvasText(ln,12,252,0x7FA6C9,k10.canvas->eCNAndENFont16,60,true);
  // Claude's reply (spoken via the speaker)
  snprintf(ln,sizeof(ln),"%s",gSay[0]?gSay:""); k10.canvas->canvasText(ln,12,276,0xEAF6FF,k10.canvas->eCNAndENFont16,60,true);
  k10.canvas->canvasText("Policy 986 AED",12,304,0x2A4A5A,k10.canvas->eCNAndENFont16,40,true);
  k10.canvas->updateCanvas();
  // LEDs follow the server colour, brightness reacts to your voice
  k10.rgb->brightness((uint8_t)(3 + vl*6));
  for (int i=0;i<3;i++) k10.rgb->write(i, gLeds[i] ? gLeds[i] : orb);
  delay(18);
}
