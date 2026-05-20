"""Contrato de publicacion.

REGLA DE ORO: ningun publisher publica directamente. Siempre se crea un
BORRADOR que requiere aprobacion humana en la herramienta antes de salir.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import Settings
from ..models import ContentPiece


class Publisher(ABC):
    name = "base"

    def __init__(self, settings: Settings):
        self.settings = settings

    @abstractmethod
    def create_draft(self, piece: ContentPiece) -> str:
        """Crea un borrador (pendiente de aprobacion) y devuelve su referencia."""
        ...

    @staticmethod
    def compose_text(piece: ContentPiece) -> str:
        idea = piece.idea
        tags = " ".join(idea.hashtags)
        return f"{idea.caption}\n\n{tags}".strip()
