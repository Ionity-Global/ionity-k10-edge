// IonityEdge · K10 — pin map (PLACEHOLDERS — verify against your K10 revision/BSP!)
// The UNIHIKER K10 exposes most peripherals through the DFRobot BSP; prefer the
// BSP API over raw pins where possible. These constants exist so raw-access code
// has a single source of truth.
// © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
#pragma once

// Onboard buttons (A/B). Confirm with DFRobot pinout.
#define PIN_BTN_A        1
#define PIN_BTN_B        2

// RGB status LED (if exposed as GPIO; else driven via BSP).
// Named _K10 to avoid clashing with the ESP32-S3 core's built-in PIN_RGB_LED.
#define PIN_RGB_LED_K10  45

// microSD (SPI). Many K10 revisions use SDMMC via BSP instead — adjust.
#define PIN_SD_CS        10
#define PIN_SD_MOSI      11
#define PIN_SD_CLK       12
#define PIN_SD_MISO      13

// I2S microphone array (confirm with BSP)
#define PIN_I2S_MIC_WS   4
#define PIN_I2S_MIC_SCK  5
#define PIN_I2S_MIC_SD   6

// I2S speaker/DAC (confirm with BSP)
#define PIN_I2S_SPK_WS   7
#define PIN_I2S_SPK_SCK  15
#define PIN_I2S_SPK_SD   16

// Camera: on the K10 the 2MP camera is wired to the module and driven by the BSP.
// Leave camera pin config to the DFRobot/esp32-camera driver.
