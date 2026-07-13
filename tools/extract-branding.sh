#!/usr/bin/env bash
# Re-extract curated Ionity branding from the master asset bundle into the repo.
# © Ionity (Pty) Ltd · Policy 986 AED
set -e
ZIP="${1:?usage: extract-branding.sh /path/to/assets12-6-2026.zip}"
DEST="$(dirname "$0")/../installer/public/brand"
mkdir -p "$DEST"; cd "$DEST"
unzip -j -o "$ZIP" \
  "assets/images/icon-192.png" "assets/images/icon-512.png" \
  "assets/images/apple-touch-icon.png" "assets/images/github.svg" \
  "assets/images/gravatar.svg" "assets/images/AEDI-LOGo.svg" \
  "assets/images/ionity-aedi-logo-computer-ai-986-pol.svg" \
  "assets/favicon/favicon.ico" "assets/favicon/ionity_logo.ico" \
  "assets/css/style.css" >/dev/null 2>&1 || true
[ -f "ionity-aedi-logo-computer-ai-986-pol.svg" ] && cp "ionity-aedi-logo-computer-ai-986-pol.svg" "ionity-logo.svg"
echo "✔ Branding refreshed in $DEST"
