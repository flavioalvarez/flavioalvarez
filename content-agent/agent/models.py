"""Estructuras de datos compartidas por todo el pipeline."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class TrendItem:
    """Una noticia/tema detectado por el agente investigador."""

    source: str                      # reddit | youtube | twitter | rss
    title: str
    url: str
    summary: str = ""
    score: float = 0.0               # popularidad cruda (upvotes, views, likes...)
    created_at: Optional[datetime] = None
    extra: dict[str, Any] = field(default_factory=dict)

    def age_hours(self) -> Optional[float]:
        if not self.created_at:
            return None
        delta = _now() - self.created_at
        return delta.total_seconds() / 3600.0


@dataclass
class ContentIdea:
    """Idea de contenido lista para producir."""

    title: str                       # titulo interno de la pieza
    hook: str                         # frase de apertura (corta el scroll)
    script: str                       # guion completo (voz en off)
    image_prompt: str                 # prompt para nano banana pro
    video_prompt: str                 # prompt para seedance 2.0
    caption: str                      # texto del post
    hashtags: list[str] = field(default_factory=list)
    based_on: list[str] = field(default_factory=list)  # urls de las fuentes


@dataclass
class GeneratedAsset:
    image_url: Optional[str] = None
    image_path: Optional[str] = None
    video_url: Optional[str] = None
    video_path: Optional[str] = None


@dataclass
class ContentPiece:
    """Idea + activos generados + estado de publicacion."""

    idea: ContentIdea
    asset: GeneratedAsset = field(default_factory=GeneratedAsset)
    status: str = "draft"            # draft | needs_approval | scheduled | failed
    publish_ref: Optional[str] = None  # id del borrador en la plataforma
    created_at: datetime = field(default_factory=_now)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        def _enc(value: Any) -> Any:
            if isinstance(value, datetime):
                return value.isoformat()
            if dataclasses.is_dataclass(value):
                return {k: _enc(v) for k, v in dataclasses.asdict(value).items()}
            if isinstance(value, list):
                return [_enc(v) for v in value]
            if isinstance(value, dict):
                return {k: _enc(v) for k, v in value.items()}
            return value

        return _enc(self)
