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
    ollama_model: str = "gemma2"      # local LLM via Ollama: `ollama pull gemma2`

    bridge_mode: str = "off"           # off | http
    bridge_url: str = "http://127.0.0.1:8799/ask"
    bridge_min_confidence: float = 0.55

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
