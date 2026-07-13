# K10 on-device firmware (DFRobot UNIHIKER core)

This build drives the **physical LCD, sensors, RGB LED and speaker** using DFRobot's official
`unihiker_k10` library, and streams telemetry to the Edge Brain over WiFi. It complements the
thin-client build in [`../arduino`](../arduino) (which streams camera/mic to the brain but stubs
the display).

## Why a separate build?
The screen/camera drivers live in DFRobot's `unihiker_k10` library, which comes from their
**PlatformIO platform** (`platform-unihiker`) or the Arduino board package — not from stock
`espressif32`. This env pulls that platform so the LCD lights up with the correct pins.

```bash
cd firmware/arduino-unihiker
cp src/secrets.h.example src/secrets.h   # if needed; set your WiFi
pio run -t upload --upload-port COM10
```

> If PlatformIO flashing leaves the board unresponsive on an early DFRobot core, recover by
> flashing via **Mind+** ("Restore device initial settings"), then retry. The thin-client build
> in `../arduino` always flashes cleanly via PlatformIO.

Shows: Ionity title, live Temp/Humidity/Light, WiFi/IP, Policy 986 — RGB glows Ionity cyan.

© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
