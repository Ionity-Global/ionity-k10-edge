#!/usr/bin/env python3
"""Seed the local WiFi-geolocation DB from a WiGLE CSV export.

The Edge Brain resolves the moving K10's position fully locally: it looks up the
BSSIDs the device scans in edge-server/data/bssid_db.json ({BSSID: [lat, lon]}).
This tool builds that file from a WiGLE "networks" CSV you already have — no cloud,
no API calls (LOCAL SAVED, Policy 986 AED).

Usage:
    python tools/import-wigle.py path/to/wigle_export.csv \
        --out edge-server/data/bssid_db.json

WiGLE CSV columns used: MAC (BSSID), CurrentLatitude, CurrentLongitude.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Import a WiGLE CSV into bssid_db.json")
    ap.add_argument("csv", help="WiGLE networks CSV export")
    ap.add_argument("--out", default="edge-server/data/bssid_db.json",
                    help="output JSON (default: edge-server/data/bssid_db.json)")
    args = ap.parse_args()

    src = Path(args.csv)
    if not src.exists():
        print(f"! not found: {src}", file=sys.stderr)
        return 2

    db: dict[str, list[float]] = {}
    with src.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        # WiGLE files sometimes carry a pre-header line; find the real header row.
        reader = csv.reader(f)
        header = None
        for row in reader:
            if row and any(c.strip().lower() == "mac" for c in row):
                header = [c.strip() for c in row]
                break
        if not header:
            print("! could not find a WiGLE header row (expected a 'MAC' column)", file=sys.stderr)
            return 3
        idx = {c.lower(): i for i, c in enumerate(header)}
        try:
            mi, la, lo = idx["mac"], idx["currentlatitude"], idx["currentlongitude"]
        except KeyError:
            print("! CSV missing MAC/CurrentLatitude/CurrentLongitude columns", file=sys.stderr)
            return 3
        for row in reader:
            if len(row) <= max(mi, la, lo):
                continue
            bssid = (row[mi] or "").strip().upper()
            try:
                lat, lon = float(row[la]), float(row[lo])
            except ValueError:
                continue
            if bssid and lat and lon:
                db[bssid] = [round(lat, 6), round(lon, 6)]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(db, indent=0))
    print(f"wrote {len(db)} BSSIDs -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
