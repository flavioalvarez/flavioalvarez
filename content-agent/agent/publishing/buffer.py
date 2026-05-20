"""Publisher de Buffer: crea actualizaciones como BORRADOR (requieren aprobacion).

Buffer crea el update con `shorten=false` y SIN programar, de modo que quede
en la cola pendiente de aprobacion/publicacion manual desde la app de Buffer.
Confirma el formato de tu token/endpoint en https://buffer.com/developers/api
(la API puede requerir acceso especial para cuentas nuevas).
"""

from __future__ import annotations

import logging

import requests

from ..config import Settings
from ..models import ContentPiece
from .base import Publisher

log = logging.getLogger("agent.publishing")

API_BASE = "https://api.bufferapp.com/1"


class BufferPublisher(Publisher):
    name = "buffer"

    def __init__(self, settings: Settings):
        super().__init__(settings)
        if not settings.buffer_access_token:
            raise ValueError("PUBLISHER=buffer pero falta BUFFER_ACCESS_TOKEN")
        if not settings.buffer_profile_ids:
            raise ValueError("PUBLISHER=buffer pero falta BUFFER_PROFILE_IDS")

    def create_draft(self, piece: ContentPiece) -> str:
        text = self.compose_text(piece)
        data = {
            "text": text,
            "profile_ids[]": self.settings.buffer_profile_ids,
            "shorten": "false",
            # sin "now" ni "scheduled_at": queda en la cola para aprobar manualmente
        }
        first = piece.idea.frame("first")
        thumb = first.approved_image.url if (first and first.approved_image) else None
        media_url = piece.asset.video_url or thumb
        if media_url:
            data["media[link]"] = media_url
            if thumb:
                data["media[thumbnail]"] = thumb

        resp = requests.post(
            f"{API_BASE}/updates/create.json",
            params={"access_token": self.settings.buffer_access_token},
            data=data,
            timeout=60,
        )
        resp.raise_for_status()
        body = resp.json()
        updates = body.get("updates", [])
        ref = updates[0]["id"] if updates else body.get("buffer_count", "unknown")
        log.info("Borrador en Buffer creado (pendiente de aprobacion): %s", ref)
        return str(ref)
