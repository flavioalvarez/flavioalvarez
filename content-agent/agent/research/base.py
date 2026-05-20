"""Contrato comun para los colectores de tendencias."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from ..config import Settings
from ..models import TrendItem

log = logging.getLogger("agent.research")


class Collector(ABC):
    """Una fuente de tendencias (Reddit, YouTube, etc.).

    Cada colector decide si esta `enabled()` (segun credenciales disponibles).
    `collect()` nunca debe propagar excepciones de red: ante un error, loguea
    y devuelve lista vacia para no romper el pipeline.
    """

    name: str = "base"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.cfg = settings.research_cfg

    @abstractmethod
    def enabled(self) -> bool:
        ...

    @abstractmethod
    def _collect(self) -> list[TrendItem]:
        ...

    def collect(self) -> list[TrendItem]:
        if not self.enabled():
            log.info("[%s] desactivado (faltan credenciales/config)", self.name)
            return []
        try:
            items = self._collect()
            log.info("[%s] %d items", self.name, len(items))
            return items
        except Exception as exc:  # noqa: BLE001 - aislamos fallos por fuente
            log.warning("[%s] fallo la coleccion: %s", self.name, exc)
            return []
