// © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
// The UNIHIKER K10 screen is driven by the DFRobot BSP. Calls below are wrapped
// so the app logic is complete; bind the drawXxx() helpers to the BSP display API
// (e.g. UNIHIKER K10 screen object) where marked TODO.
#include "screen.h"
#include "../../include/config.h"
#include "../../include/hardware_pins.h"

// The Ionity feature buttons shown on the 320x240 home grid (2 cols x 4 rows).
static const char* kButtons[] = {
  "Ask / Voice", "Scan / OCR", "Identify", "Sensors",
  "Record", "Locate", "Notices", "Settings"
};
static const int kButtonCount = sizeof(kButtons) / sizeof(kButtons[0]);

// ---- BSP drawing shims (TODO: bind to DFRobot K10 display) ----
static void drawFill(uint32_t rgb) { /* TODO screen.fillScreen(rgb565(rgb)); */ }
static void drawText(int x, int y, const String& s, uint32_t rgb, int size) {
  Serial.printf("[screen %d,%d] %s\n", x, y, s.c_str()); /* TODO screen.setCursor/print */
}
static void drawButton(int x, int y, int w, int h, const String& label, bool active) {
  Serial.printf("[btn] (%d,%d %dx%d) %s%s\n", x, y, w, h, label.c_str(), active?" *":"");
  /* TODO screen.fillRoundRect(...); border COL_PRIMARY; text COL_TEXT */
}

void Screen::begin() {
  // Configure the placeholder A/B button pins so digitalRead won't spam
  // "IO not set as GPIO". Real K10 buttons/touch come via the DFRobot BSP.
  pinMode(PIN_BTN_A, INPUT_PULLUP);
  pinMode(PIN_BTN_B, INPUT_PULLUP);
  /* TODO screen.begin(); rotation, backlight */
  drawFill(COL_BG);
}

void Screen::splash() {
  drawFill(COL_BG);
  drawText(40, 90, "IONITY", COL_PRIMARY, 4);
  drawText(48, 130, "Edge · K10", COL_TEXT, 2);
  drawText(30, 200, "Building Tomorrow, Today", COL_MUTED, 1);
  /* TODO draw /data/logo.png from LittleFS */
}

void Screen::homeGrid() {
  drawFill(COL_BG);
  drawText(10, 6, "IonityEdge", COL_PRIMARY, 2);
  drawText(230, 10, _status.length()?_status:"ready", COL_MUTED, 1);
  const int cols = 2, cw = 150, ch = 48, gx = 8, gy = 34, gap = 6;
  for (int i = 0; i < kButtonCount; i++) {
    int c = i % cols, r = i / cols;
    int x = gx + c * (cw + gap), y = gy + r * (ch + gap);
    drawButton(x, y, cw, ch, kButtons[i], false);
  }
}

void Screen::setStatus(const String& s) { _status = s; drawText(230, 10, s, COL_MUTED, 1); }

int Screen::pollButtons() {
  if (millis() - _lastPoll < 40) return -1;     // debounce
  _lastPoll = millis();
  bool a = digitalRead(PIN_BTN_A) == LOW;        // active-low assumption; verify BSP
  bool b = digitalRead(PIN_BTN_B) == LOW;
  int hit = -1;
  if (a && !_aPrev) hit = 0;                     // A -> "Ask / Voice"
  if (b && !_bPrev) hit = 1;                     // B -> "Scan / OCR"
  _aPrev = a; _bPrev = b;
  // TODO: add touch-point hit-testing across the 8 grid cells via BSP touch API
  return hit;
}

void Screen::showAnswer(const String& text) {
  drawFill(COL_BG);
  drawText(10, 8, "Ionity says", COL_PRIMARY, 2);
  drawText(10, 40, text, COL_TEXT, 2);
  /* TODO word-wrap to 320px; scroll for long answers */
}

void Screen::showNotice(const String& title, const String& body) {
  drawText(10, 210, title + ": " + body, COL_ACCENT, 1);   // bottom ticker
}

void Screen::applyLayout(JsonVariantConst layout) {
  // Brain-driven UI: [{label, x, y, w, h, active}]
  drawFill(COL_BG);
  for (JsonVariantConst el : layout["buttons"].as<JsonArrayConst>()) {
    drawButton(el["x"] | 8, el["y"] | 34, el["w"] | 150, el["h"] | 48,
               el["label"] | "", el["active"] | false);
  }
  if (layout["title"].is<const char*>()) drawText(10, 8, layout["title"], COL_PRIMARY, 2);
}
