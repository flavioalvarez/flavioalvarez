"""Carga de configuracion: variables de entorno + config/brand.yaml."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

try:  # carga .env si existe (opcional en CI, donde se usan secrets reales)
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv es opcional
    pass


ROOT = Path(__file__).resolve().parent.parent


def _bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "").strip())
    except (TypeError, ValueError):
        return default


@dataclass
class Settings:
    # LLM
    anthropic_api_key: str
    ideation_model: str

    # Higgsfield
    higgsfield_api_key: str
    higgsfield_secret: str
    higgsfield_base_url: str
    higgsfield_image_model: str
    higgsfield_video_model: str

    # Fuentes de investigacion
    reddit_client_id: str
    reddit_client_secret: str
    reddit_user_agent: str
    youtube_api_key: str
    twitter_bearer_token: str

    # Publicacion
    publisher: str
    buffer_access_token: str
    buffer_profile_ids: list[str]
    ayrshare_api_key: str

    # Comportamiento
    pieces_per_run: int
    output_dir: Path
    dry_run: bool

    # Marca (brand.yaml)
    brand: dict[str, Any]

    @property
    def research_cfg(self) -> dict[str, Any]:
        return self.brand.get("research", {})

    @property
    def content_cfg(self) -> dict[str, Any]:
        return self.brand.get("content", {})

    @property
    def brand_cfg(self) -> dict[str, Any]:
        return self.brand.get("brand", {})


def _load_brand(path: Path | None = None) -> dict[str, Any]:
    path = path or (ROOT / "config" / "brand.yaml")
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_settings(brand_path: Path | None = None) -> Settings:
    brand = _load_brand(brand_path)
    profile_ids = [
        p.strip() for p in os.getenv("BUFFER_PROFILE_IDS", "").split(",") if p.strip()
    ]
    out_dir = Path(os.getenv("OUTPUT_DIR", "output"))
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir

    return Settings(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        ideation_model=os.getenv("IDEATION_MODEL", "claude-sonnet-4-6"),
        higgsfield_api_key=os.getenv("HIGGSFIELD_API_KEY", ""),
        higgsfield_secret=os.getenv("HIGGSFIELD_SECRET", ""),
        higgsfield_base_url=os.getenv(
            "HIGGSFIELD_BASE_URL", "https://platform.higgsfield.ai"
        ).rstrip("/"),
        higgsfield_image_model=os.getenv("HIGGSFIELD_IMAGE_MODEL", "nano-banana-pro"),
        higgsfield_video_model=os.getenv("HIGGSFIELD_VIDEO_MODEL", "seedance2"),
        reddit_client_id=os.getenv("REDDIT_CLIENT_ID", ""),
        reddit_client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
        reddit_user_agent=os.getenv("REDDIT_USER_AGENT", "okeybot-content-agent/1.0"),
        youtube_api_key=os.getenv("YOUTUBE_API_KEY", ""),
        twitter_bearer_token=os.getenv("TWITTER_BEARER_TOKEN", ""),
        publisher=os.getenv("PUBLISHER", "local").strip().lower(),
        buffer_access_token=os.getenv("BUFFER_ACCESS_TOKEN", ""),
        buffer_profile_ids=profile_ids,
        ayrshare_api_key=os.getenv("AYRSHARE_API_KEY", ""),
        pieces_per_run=_int("PIECES_PER_RUN", 2),
        output_dir=out_dir,
        dry_run=_bool("DRY_RUN", False),
        brand=brand,
    )
