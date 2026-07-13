# Installer (React + Vite PWA)

The control app for IonityEdge · K10: **one-click flashing**, **WiFi provisioning**, and a live
**dashboard** for the Edge Brain — devices, models, semantic cache, recordings, vision/OCR, and
voice queries. Ionity-themed, installable as a PWA.

## Run

```bash
cd installer
npm install
npm run dev        # http://localhost:5173
```

Point it at your Edge Brain under **Settings** (default `http://127.0.0.1:8765`).

## Flashing (browser)

Use a **Chromium** browser (Web Serial). On the **Flash & WiFi** page:
1. **Connect** the K10 over USB.
2. Choose the merged firmware `.bin` (from `cd firmware/arduino && pio run`) and **Flash @ 0x0**.
3. Enter WiFi (`Antwerp Ionity`) + your PC's LAN IP and **Send provisioning** — credentials go to
   the board's NVS, never to disk or the repo.

Prefer the CLI? Use [`../flasher/flash.ps1`](../flasher/flash.ps1) / `flash.sh`.

## Build (served by the Edge Brain)

```bash
npm run build      # outputs dist/ ; the Edge Brain serves it at /app if present
```

© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
