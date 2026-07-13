# K10 Firmware (MicroPython demos) — education / tinkering

The **easy path** for learning and tinkering. These scripts run on the K10's MicroPython BSP and
post telemetry to the Edge Brain over simple HTTP. For the real on-device experience use the live
C++ build in [`../arduino-unihiker`](../arduino-unihiker) (server-computed render over HTTP `/ingest`).

## Load onto the board

Use [Thonny](https://thonny.org/) or `mpremote`:

```bash
mpremote connect auto fs cp boot.py :boot.py
mpremote connect auto fs cp main.py :main.py
mpremote connect auto fs cp lib/edge_client.py :lib/edge_client.py
mpremote connect auto fs cp lib/demos.py :lib/demos.py
mpremote connect auto run main.py
```

## Notes
- Set `EDGE_HOST` in `main.py` to your PC's LAN IP running the Edge Brain.
- The Edge Brain exposes `POST /ingest` for these demos (see `edge-server`).
- `unihiker_k10` module name is a placeholder — match it to your installed DFRobot K10 BSP.

© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
