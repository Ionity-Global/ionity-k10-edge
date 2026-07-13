// Screen + button grid (Ionity theme). Binds to the DFRobot K10 display BSP.
// © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>

class Screen {
public:
  void begin();
  void splash();                          // Ionity logo + tagline
  void homeGrid();                        // draw the feature button grid
  void setStatus(const String& s);        // status line
  int  pollButtons();                     // returns tapped button index, or -1
  void showAnswer(const String& text);    // brain answer bubble
  void showNotice(const String& title, const String& body);  // ad / smart-notify
  void applyLayout(JsonVariantConst layout);                 // brain-driven UI
private:
  String _status;
  uint32_t _lastPoll = 0;
  bool _aPrev = false, _bPrev = false;
};
