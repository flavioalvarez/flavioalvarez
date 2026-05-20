"""Selector de publisher segun configuracion (PUBLISHER)."""

from __future__ import annotations

from ..config import Settings
from .ayrshare import AyrsharePublisher
from .base import Publisher
from .buffer import BufferPublisher
from .local import LocalPublisher

_REGISTRY = {
    "local": LocalPublisher,
    "buffer": BufferPublisher,
    "ayrshare": AyrsharePublisher,
}


def get_publisher(settings: Settings) -> Publisher:
    # en dry-run forzamos local para no tocar servicios externos
    name = "local" if settings.dry_run else settings.publisher
    cls = _REGISTRY.get(name)
    if cls is None:
        raise ValueError(
            f"PUBLISHER desconocido: {name!r}. Opciones: {', '.join(_REGISTRY)}"
        )
    return cls(settings)
