// Onboard sensor HAL. © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
#pragma once
#include <Arduino.h>

struct SensorReading {
  float tempC = 0, humidity = 0, light = 0;
  float ax = 0, ay = 0, az = 0;   // accelerometer g
  int   battery = 100;            // %
};

class Sensors {
public:
  void begin();
  SensorReading read();           // binds to DFRobot K10 sensor BSP
};
