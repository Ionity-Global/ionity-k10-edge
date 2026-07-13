# IonityEdge · K10 — push this repo to GitHub (Ionity Global, public)
# Run on your Windows drive (NTFS) — NOT on a cloud-sync mount, which corrupts git.
# © Ionity (Pty) Ltd · Policy 986 AED
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$Org  = if ($env:IONITY_GH_ORG)  { $env:IONITY_GH_ORG }  else { "Ionity-Global" }
$Repo = if ($env:IONITY_GH_REPO) { $env:IONITY_GH_REPO } else { "ionity-k10-edge" }

# Self-heal a broken .git (e.g. synced from a cloud mount)
if ((Test-Path .git) -and -not (git rev-parse --git-dir 2>$null)) {
  Write-Host "Broken .git detected — reinitialising" -ForegroundColor Yellow
  Remove-Item -Recurse -Force .git
}
if (-not (Test-Path .git)) { git init; git branch -M main }
git config user.email "ai@ionity.today"
git config user.name  "Johan Wilhelm van Antwerp"

git add -A

# Secret guard (no literal password embedded)
$tracked = git ls-files
if ($tracked | Select-String -Pattern '(^|/)secrets\.h$|(^|/)\.env$') {
  Write-Host "✘ secrets.h/.env is tracked — aborting" -ForegroundColor Red; exit 1
}
$leak = git grep -nE 'WIFI_PASS[[:space:]]+"[^"]+"' -- '*.h' '*.cpp' '*.ino' 2>$null |
        Where-Object { $_ -notmatch 'your-wifi-password-here' }
if ($leak) { Write-Host "✘ A real WIFI_PASS value is tracked — aborting" -ForegroundColor Red; exit 1 }

git commit -m "IonityEdge · K10 v0.1.0 — firmware + hybrid Edge Brain + installer (Policy 986 AED)" 2>$null

if (Get-Command gh -ErrorAction SilentlyContinue) {
  gh repo view "$Org/$Repo" 2>$null; if ($LASTEXITCODE -ne 0) {
    gh repo create "$Org/$Repo" --public --source . --remote origin `
      --description "True Edge AI for the UNIHIKER K10 — Ionity Global, Policy 986 AED"
  }
}
if (-not (git remote | Select-String origin)) {
  git remote add origin "https://github.com/$Org/$Repo.git"
}
git push -u origin main
Write-Host "✔ Pushed to https://github.com/$Org/$Repo" -ForegroundColor Green
