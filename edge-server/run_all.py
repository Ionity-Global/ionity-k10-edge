"""IonityEdge · K10 — one-click launcher.
Starts the Edge Brain (server = the brain) and opens the dashboard in the browser.
Bundled to IonityEdge.exe with PyInstaller; place the exe in this edge-server/ folder.
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
"""
import os
import sys
import time
import threading
import webbrowser
import subprocess

# Where the server package lives: next to the exe when frozen, else this file's dir.
BASE = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
URL = "http://localhost:8765/"


def _open():
    time.sleep(4.0)
    try:
        webbrowser.open(URL)
    except Exception:
        pass


def main():
    print("=" * 60)
    print("  IonityEdge · K10 — Edge Brain")
    print("  Dashboard:  " + URL)
    print("  LAN/device: http://192.168.124.5:8765/")
    print("  (leave this window open) · Policy 986 AED")
    print("=" * 60)
    env = os.environ.copy()
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    threading.Thread(target=_open, daemon=True).start()
    for cmd in (["py", "-3.12", "-m", "app.main"], ["py", "-m", "app.main"], ["python", "-m", "app.main"]):
        try:
            return subprocess.call(cmd, cwd=BASE, env=env)
        except FileNotFoundError:
            continue
    print("Python not found. Install Python 3.12 and the deps in requirements.txt.")
    input("Press Enter to exit.")


if __name__ == "__main__":
    main()
