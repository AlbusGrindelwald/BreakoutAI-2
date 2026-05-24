from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> bool:
        return False


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SOP_PATH = ROOT_DIR / "data" / "sop.json"


@dataclass(frozen=True)
class Settings:
    openrouter_api_key: str | None
    use_openrouter_api: bool
    openrouter_model: str
    openrouter_fallback_models: list[str]
    openrouter_base_url: str
    app_name: str | None
    site_url: str | None
    sop_path: Path

    @property
    def has_openrouter_key(self) -> bool:
        missing_values = {"", "your_key_here", "your_openrouter_key_here"}
        return bool(self.openrouter_api_key and self.openrouter_api_key not in missing_values)


def load_settings() -> Settings:
    load_dotenv()
    fallback_models = [
        model.strip()
        for model in os.getenv(
            "OPENROUTER_FALLBACK_MODELS",
            "meta-llama/llama-3.3-70b-instruct:free,qwen/qwen3-coder:free,openrouter/free",
        ).split(",")
        if model.strip()
    ]
    return Settings(
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
        use_openrouter_api=os.getenv("USE_OPENROUTER_API", "false").strip().lower()
        in {"1", "true", "yes", "y"},
        openrouter_model=os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b:free"),
        openrouter_fallback_models=fallback_models,
        openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        app_name=os.getenv("OPENROUTER_APP_NAME"),
        site_url=os.getenv("OPENROUTER_SITE_URL"),
        sop_path=Path(os.getenv("SOP_PATH", DEFAULT_SOP_PATH)),
    )
