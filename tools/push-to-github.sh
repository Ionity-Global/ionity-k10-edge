#!/usr/bin/env bash
# IonityEdge · K10 — push this repo to GitHub (Ionity Global, public)
# Run on your native filesystem (Windows Git Bash / macOS / Linux) — NOT on a
# cloud-sync mount, which corrupts git internals.
# © Ionity (Pty) Ltd · Policy 986 AED
set -e
cd "$(dirname "$0")/.."
ORG="${IONITY_GH_ORG:-Ionity-Global}"
REPO="${IONITY_GH_REPO:-ionity-k10-edge}"

# Self-heal a broken .git (e.g. synced from a cloud mount)
if [ -d .git ] && ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "Broken .git detected — reinitialising"; rm -rf .git
fi
[ -d .git ] || { git init; git branch -M main; }
git config user.email "ai@ionity.today"
git config user.name  "Johan Wilhelm van Antwerp"

git add -A

# Secret guard (no literal password embedded)
if git ls-files | grep -E '(^|/)secrets\.h$|(^|/)\.env$'; then
  echo "✘ secrets.h/.env is tracked — aborting"; exit 1
fi
if git diff --cached --name-only | xargs -r grep -nE 'WIFI_PASS[[:space:]]+"[^"]+"' 2>/dev/null \
     | grep -v 'your-wifi-password-here'; then
  echo "✘ A real WIFI_PASS value is staged — aborting"; exit 1
fi

git commit -m "IonityEdge · K10 v0.1.0 — firmware + hybrid Edge Brain + installer (Policy 986 AED)" || true

if command -v gh >/dev/null 2>&1; then
  gh repo view "$ORG/$REPO" >/dev/null 2>&1 || \
    gh repo create "$ORG/$REPO" --public --source . --remote origin \
      --description "True Edge AI for the UNIHIKER K10 — Ionity Global, Policy 986 AED"
fi
git remote | grep -q origin || git remote add origin "https://github.com/$ORG/$REPO.git"
git push -u origin main
echo "✔ Pushed to https://github.com/$ORG/$REPO"
