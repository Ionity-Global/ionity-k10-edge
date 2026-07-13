// © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
// Bind read() to the DFRobot UNIHIKER K10 sensor API. Until the BSP is added,
// this returns representative values so the pipeline (stream -> brain -> UI) runs.
#include "sensors.h"

void Sensors::begin() {
  // TODO: k10.begin() / init temp-hum, light, accelerometer via BSP
}

SensorReading Sensors::read() {
  SensorReading r;
  // TODO replace with BSP reads:
  //   r.tempC    = k10.readTemperature();
  //   r.humidity = k10.readHumidity();
  //   r.light    = k10.readAmbientLight();
  //   k10.readAccel(&r.ax,&r.ay,&r.az);
  r.tempC = 24.0f + (float)(millis() % 3000) / 3000.0f;   // placeholder telemetry
  r.humidity = 45.0f;
  r.light = 320.0f;
  r.ax = 0.01f; r.ay = -0.02f; r.az = 0.99f;
  r.battery = 100;
  return r;
}
