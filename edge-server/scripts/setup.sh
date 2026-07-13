#!/usr/bin/env bash
# IonityEdge · K10 — Edge Brain setup (Linux/macOS)
# © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
set -e
cd "$(dirname "$0")/.."

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

[ -f .env ] || cp .env.example .env
echo "✔ Core Edge Brain installed."

if [ "${EDGE_INSTALL_MODELS:-0}" = "1" ]; then
  echo "Installing optional model backends (this is large)…"
  pip install faster-whisper piper-tts sentence-transformers opencv-python pytesseract Pillow ollama || true
fi

echo
echo "Next:"
echo "  source .venv/bin/activate && python -m app.main"
echo "  (optional local LLM)  ollama serve  &&  ollama pull \${OLLAMA_MODEL:-llama3.2}"
