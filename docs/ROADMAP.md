<!-- INTERNAL · IonityEdge · K10 · POL 986 AED -->

# Roadmap

> **Doc ID:** DOC-2026-07-K10-005 · Policy 986 AED

## v1 — Foundation (this repo)
- Thin-client firmware (C++ + MicroPython demos), hybrid Edge Brain, React installer.
- All feature bundles scaffolded: vision+OCR, voice+wake-word+mood, sensors, geolocation,
  SD recording, semantic cache, ads, provenance.
- Open-source repo under Ionity Global, CC BY-SA 4.0 / Policy 986; local flash + provisioning.

## v2 — Hardening
- Real model weights wired (Whisper, PaddleOCR, vision, Ollama LLM, Piper TTS).
- Adaptive media streaming controller; Opus audio; 5 GHz brain uplink option.
- OTA firmware updates; encrypted device↔brain sessions; recording indexer + search.
- Semantic-cache tuning, eviction policy, offline answer packs.

## v3 — Ecosystem
- **Fleet view**: many K10 nodes to one Edge Brain (AEDI ecosystem console).
- Port Edge Brain to Jetson and the Ionity **AI-M** board (5 V / 20 W True Edge AI).
- Smart Notify gateways; PdM/DAQ hooks for industrial telemetry.
- PWA installable; mobile companion; multi-language (Afrikaans, English, Hebrew).

## Backlog / ideas
- On-device TinyML fallback when the brain is unreachable.
- Digital-twin view of the moving device on a live map.
- Voice personas + gospel/ambient audio packs from the Ionity asset library.

_© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0 · Building Tomorrow, Today._
