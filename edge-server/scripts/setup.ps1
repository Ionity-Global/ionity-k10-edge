# IonityEdge · K10 — Edge Brain setup (Windows PowerShell)
# © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

python -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

if (-not (Test-Path .env)) { Copy-Item .env.example .env }
Write-Host "OK Core Edge Brain installed." -ForegroundColor Green

if ($env:EDGE_INSTALL_MODELS -eq "1") {
  Write-Host "Installing optional model backends (large)..." -ForegroundColor Yellow
  pip install faster-whisper piper-tts sentence-transformers opencv-python pytesseract Pillow ollama
}

Write-Host ""
Write-Host "Next:"
Write-Host "  .\.venv\Scripts\Activate.ps1 ; python -m app.main"
Write-Host "  (optional local LLM)  ollama serve ; ollama pull llama3.2"
