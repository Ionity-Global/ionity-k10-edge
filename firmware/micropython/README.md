# K10 Firmware (MicroPython node) — education / second node

The **easy path**: a real thin node in ~100 lines. It uploads sensors to the Edge Brain and
**displays the server-computed render** (orb colour = AI state/tone, label, Claude's words) —
the same contract as the C++ firmware, minus audio. Load with Thonny or:

```bash
mpremote connect COMx fs cp -r lib :lib + fs cp boot.py main.py :
mpremote reset
```

Set `WIFI_PASS` and `EDGE_HOST` at the top of `main.py` first. For the full voice experience
(mic, speaker, camera OCR) use the C++ build in [`../arduino-unihiker`](../arduino-unihiker).
`lib/edge_client.py` also runs under CPython, so you can contract-test it against a live server.

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
