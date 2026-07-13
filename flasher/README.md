# Flasher

Three ways to flash the K10:

1. **Browser (easiest)** — the [Installer](../installer) → *Flash & WiFi* page (Web Serial, Chromium).
2. **One-click script** — `flash.ps1` (Windows) or `flash.sh` (Linux/macOS). Prefers PlatformIO,
   falls back to `esptool`.
3. **Manual** — `cd ../firmware/arduino && pio run -t upload`.

After flashing, provision WiFi (`Antwerp Ionity`) + your Edge Brain IP via the Installer.

© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
