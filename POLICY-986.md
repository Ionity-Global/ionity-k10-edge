# Policy 986 AED — Governance Notice

**Project:** IonityEdge · K10
**Author:** Johan Wilhelm van Antwerp
**Entity:** Ionity (Pty) Ltd / Antwerp Designs (AEDI — Antwerp Ecosystem Designs Ionity)
**Effective:** 2026-07-12 · **Jurisdiction of intent:** Global · Centurion, South Africa (UTC+2)

---

## 1. Governance

All artefacts in this repository — source, documentation, assets, and generated
output — are governed by **Policy 986 AED** by default during development. Where a
file, folder, or release explicitly declares an open-source license (here:
**CC BY-SA 4.0**), that declared license applies to reuse, while Policy 986 AED
remains the overarching governance framework for authorship, provenance, and
attribution.

## 2. Attribution & provenance

Every capture, export, and generated document produced by the Edge Brain is stamped
with an AEDI provenance block (see `edge-server/app/meta/provenance.py` and
`metadata.json`): author, entity, timestamp (ISO-8601, UTC+2), version, and a
content hash. This provides a forensic chain of custody consistent with the AEDI
"Forensic Output Standards" principle.

## 3. Open-source intent

This project is released **publicly and open-source under Ionity Global**. Reuse of
the *code* is granted under CC BY-SA 4.0 with attribution. Ionity **brand marks**
(logos, wordmarks, favicons) remain Ionity property (TM²) and are excluded from the
open grant — see `LICENSE`.

## 4. Data sovereignty

The Edge Brain runs locally. Sensor data, recordings, and semantic-cache entries are
**stored locally by default** (LOCAL SAVED). No cloud API calls are required for core
operation. Optional backups to the author's OneDrive and Google Drive are mirrored
manually or via the provided tooling; no third-party telemetry is emitted.

## 5. Contact & reporting

info@ionity.today · www.ionity.today · www.ionity.co.za

_"I do not innovate. I create." — Anything is Possible with God._
