@echo off
REM Ionity Claude Web Bridge — first run installs Playwright + Chromium, then opens
REM claude.ai. Sign in with Google ONCE; the session persists. Leave this window open.
REM (c) Ionity (Pty) Ltd - Policy 986 AED
cd /d "%~dp0"
if not exist node_modules (
  echo Installing bridge dependencies (first run)...
  call npm install
)
echo Starting Ionity Claude Web Bridge on http://127.0.0.1:8799 ...
node server.js
pause
