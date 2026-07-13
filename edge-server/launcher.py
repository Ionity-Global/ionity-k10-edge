"""IonityAssistant — one-click launcher for the whole edge stack.

Double-click IonityAssistant.exe to:
  1. start Ollama (local brain gemma4:e2b) if it isn't already running,
  2. start the Edge Brain (STT + TTS + Claude/gemma + orb renderer) on :8765,
  3. open the dashboard, and (optionally) the Claude web bridge.
Everything — speech-to-AI, TTS, rendering — runs on THIS server; the K10 only streams
mic audio in and plays/display what the server sends back, over WiFi.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
"""
from __future__ import annotations
import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

PORT = 8765


def _base_dir() -> Path:
    here = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    for cand in (here, here / "edge-server", here.parent / "edge-server", Path.cwd(), Path.cwd() / "edge-server"):
        if (cand / "app" / "main.py").exists():
            return cand
    return here


def _port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.6)
        return s.connect_ex((host, port)) == 0


def _python() -> list[str]:
    for cmd in (["py", "-3.12"], ["py", "-3"], ["python"]):
        try:
            subprocess.run(cmd + ["--version"], capture_output=True, timeout=6)
            return cmd
        except Exception:
            continue
    return ["python"]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    base = _base_dir()
    print("=" * 60)
    print("  IONITY - Home Assistant - Edge launcher   (Policy 986 AED)")
    print("  edge-server:", base)
    print("=" * 60)

    # 1) Ollama (local fallback brain)
    if not _port_open(11434):
        print("[*] starting Ollama ...")
        try:
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print("    (Ollama not started:", e, "- gemma4:e2b fallback may be unavailable)")

    # 2) Edge Brain
    if _port_open(PORT):
        print(f"[*] Edge Brain already running on :{PORT}")
        server = None
    else:
        print("[*] starting Edge Brain ...")
        env = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
        server = subprocess.Popen(_python() + ["-m", "app.main"], cwd=str(base), env=env)

    # wait for it to bind
    for _ in range(120):
        if _port_open(PORT):
            break
        time.sleep(0.5)

    url = f"http://localhost:{PORT}/"
    if _port_open(PORT):
        print(f"[OK] Edge Brain live - {url}")
        try:
            webbrowser.open(url)
        except Exception:
            pass
    else:
        print("[!] Edge Brain did not start. Check Python 3.12 + deps in", base)

    # 3) Claude web bridge (optional — only if it's been set up)
    bridge = base.parent / "bridge" / "claude-web"
    if (bridge / "node_modules").exists():
        print("[*] starting Claude web bridge (sign in once in the browser it opens) ...")
        try:
            subprocess.Popen(["node", "server.js"], cwd=str(bridge))
        except Exception as e:
            print("    (bridge not started:", e, ")")
    else:
        print("[i] Claude bridge not installed — using local gemma4:e2b. To enable Claude,")
        print("    run bridge\\claude-web\\START-BRIDGE.bat once and sign in with Google.")

    print("\nLeave this window open. Close it to stop the assistant.\n")
    try:
        if server is not None:
            server.wait()
        else:
            while True:
                time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        if server is not None:
            try:
                server.terminate()
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
