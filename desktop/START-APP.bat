@echo off
REM Ionity Home Assistant desktop app. First run installs Electron (a few minutes).
cd /d "%~dp0"
if not exist node_modules ( echo Installing desktop app (first run)... & call npm install )
call npx electron .
