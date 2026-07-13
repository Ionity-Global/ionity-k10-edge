@echo off
REM IonityEdge · K10 — start the Edge Brain (double-click me)
REM Serves the dashboard at http://localhost:8765/  ·  Policy 986 AED
cd /d "%~dp0"
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
echo.
echo   IonityEdge Edge Brain starting...
echo   Open in your browser:  http://localhost:8765/
echo   (LAN / device view:     http://192.168.124.5:8765/ )
echo.
py -3.12 -m app.main
echo.
echo Server stopped. Press any key to close.
pause >nul
