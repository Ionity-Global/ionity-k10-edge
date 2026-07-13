"""Runtime configuration. © Ionity (Pty) Ltd · Policy 986 AED · CC BY-SA 4.0"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    edge_host: str = "0.0.0.0"
    edge_port: int = 8765

    feat_vision: bool = True
    feat_ocr: bool = True
    feat_voice: bool = True
    feat_mood: bool = True
    feat_geo: bool = True
    feat_recording: bool = True
    feat_ads: bool = True

    cache_threshold: float = 0.92
    cache_max: int = 5000

    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "gemma4:e2b"   # local brain via Ollama (installed); fallback below gemma4:e4b
    vision_model: str = "gemma3:4b"    # multimodal model for camera OCR/vision (reads text reliably)
    stt_model: str = "tiny"            # whisper size: tiny (fastest, default) | base | small

    bridge_mode: str = "http"          # off | http  — primary brain = Claude via the web bridge
    bridge_url: str = "http://127.0.0.1:8799/ask"
    bridge_min_confidence: float = 0.55

    # ---- Voice home-assistant ----
    assist_enabled: bool = True
    wake_word: str = "peper"           # primary wake word (server-side, on the edge)
    wake_words: str = "peper,pepper,piet,peet,hi pepper,hey pepper,hi piet,hey piet,hi peper,peppa,pepa,pete"  # custom wake words (CSV, learnable)
    temp_alert_c: float = 38.0         # speak + tint orange when the room passes this temperature
    assistant_name: str = "Ionity"
    orb_stream_fps: int = 10           # server->device orb frame rate
    orb_frame_size: int = 150          # px square RGB565 region streamed to the K10
    idle_sleep_s: float = 30.0         # go to SLEEPING after this much silence
    tts_voice: str = ""                # path to a Piper .onnx voice (else browser/edge TTS)

    # ---- Smart home (all optional — configure what you actually have; everything degrades gracefully) ----
    ha_url: str = ""                   # Home Assistant base URL, e.g. http://homeassistant.local:8123
    ha_token: str = ""                 # HA long-lived access token
    hue_bridge: str = ""               # Philips Hue bridge IP (press the bridge button on first use)
    chromecast_name: str = ""          # default Google Cast / Android TV device name
    mqtt_host: str = ""                # MQTT broker host (for ESP32/IoT sensors & devices)
    mqtt_port: int = 1883

    # Optional local integrations (all off by default — LOCAL SAVED, no cloud):
    dispatch_webhook_url: str = ""     # e.g. a Home Assistant webhook; /api/dispatch forwards commands here
    image_api_url: str = ""            # e.g. local A1111/ComfyUI; /api/generate-image relays prompts here
    piper_voice: str = ""              # path to a Piper .onnx voice; enables server-side /api/speak (WAV)

    data_dir: Path = Path("./data")
    recordings_dir: Path = Path("./recordings")
    models_dir: Path = Path("./models")

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.recordings_dir, self.models_dir):
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
