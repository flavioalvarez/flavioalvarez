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
class GeneratedImage:
    """Una variante de imagen generada con nano banana pro."""

    variant: int
    url: Optional[str] = None
    path: Optional[str] = None


@dataclass
class StoryboardFrame:
    """Un frame clave del storyboard (primero o ultimo de la escena).

    Se generan varias `variants` con nano banana para que el humano elija.
    `approved_variant` queda en None hasta que se aprueba una.
    """

    role: str                        # "first" | "last"
    description: str                 # que muestra (en espanol, para entender)
    prompt: str                      # prompt nano banana (ingles)
    variants: list[GeneratedImage] = field(default_factory=list)
    approved_variant: Optional[int] = None

    @property
    def approved_image(self) -> Optional[GeneratedImage]:
        if self.approved_variant is None:
            return None
        for img in self.variants:
            if img.variant == self.approved_variant:
                return img
        return None


@dataclass
class ContentIdea:
    """Idea de contenido lista para producir."""

    title: str                       # titulo interno de la pieza
    hook: str                         # frase de apertura (corta el scroll)
    script: str                       # guion completo (voz en off)
    caption: str                      # texto del post
    video_prompt: str = ""            # prompt para seedance (REQUIERE aprobacion)
    frame_mode: str = "first"         # "first" | "last" | "both"
    storyboard: list[StoryboardFrame] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)
    based_on: list[str] = field(default_factory=list)  # urls de las fuentes

    def frame(self, role: str) -> Optional[StoryboardFrame]:
        for fr in self.storyboard:
            if fr.role == role:
                return fr
        return None


@dataclass
class GeneratedAsset:
    video_url: Optional[str] = None
    video_path: Optional[str] = None


@dataclass
class ContentPiece:
    """Idea + activos generados + estado de publicacion.

    Etapas del estado:
      proposed        -> idea + prompts listos, falta aprobar el prompt de video
      storyboard_ready-> variantes de frames generadas, falta elegir variante
      rendered        -> video generado a partir de los frames aprobados
      needs_approval  -> borrador encolado, falta aprobacion final para publicar
      scheduled / failed
    """

    idea: ContentIdea
    asset: GeneratedAsset = field(default_factory=GeneratedAsset)
    status: str = "proposed"
    publish_ref: Optional[str] = None
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
