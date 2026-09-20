"""
config.py
=========
CrackXNet backend configuration.

All values are read from environment variables (or the .env file).
Never hard-code credentials or paths here.
"""

import os
import torch
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── AI Model ─────────────────────────────────────────────────────────────
    model_path: str = "checkpoints/crackxnet_final.pth"
    confidence_threshold: float = 0.50
    iou_threshold: float = 0.45
    input_width: int = 640
    input_height: int = 640

    # ── Image Upload ──────────────────────────────────────────────────────────
    max_upload_size_mb: int = 20
    upload_dir: str = "uploads"
    results_dir: str = "results"

    # ── MongoDB ───────────────────────────────────────────────────────────────
    mongodb_uri: str = "mongodb://localhost:27017"
    database_name: str = "crackxnet"

    # ── Server ────────────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # ── Derived (not from env) ────────────────────────────────────────────────
    @property
    def device(self) -> str:
        return "cuda" if torch.cuda.is_available() else "cpu"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def allowed_extensions(self) -> set:
        return {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}

    def ensure_dirs(self) -> None:
        """Create upload/results directories if they don't exist."""
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()
