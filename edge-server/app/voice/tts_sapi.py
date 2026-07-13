"""Windows SAPI text-to-speech — gives the assistant a real voice with no extra install.

Produces a 16 kHz / 16-bit / mono WAV (matches the K10 I2S so the ESP can play it straight
through its speaker). Used when Piper isn't configured. Server-side only (edge compute).
© Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

_PS = r"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, `
  [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, `
  [System.Speech.AudioFormat.AudioChannel]::Mono)
$s.SetOutputToWaveFile("%OUT%", $fmt)
$s.Rate = 1
$s.Speak([Console]::In.ReadToEnd())
$s.Dispose()
"""

available = sys.platform.startswith("win")


def synth(text: str, out_wav: str) -> str | None:
    if not available or not text.strip():
        return None
    try:
        script = _PS.replace("%OUT%", str(Path(out_wav)))
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                       input=text.encode("utf-8"), timeout=30, capture_output=True)
        return out_wav if Path(out_wav).exists() and Path(out_wav).stat().st_size > 44 else None
    except Exception:
        return None
