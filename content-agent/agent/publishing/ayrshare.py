"""Publisher de Ayrshare: alternativa API-first a Buffer.

Crea el post con `approvalRequired: true` para que NO salga sin aprobacion
manual desde el panel de Ayrshare. Soporta IG, TikTok y YouTube en un solo POST.
Doc: https://docs.ayrshare.com/rest-api/endpoints/post
"""

from __future__ import annotations

import logging

import requests

from ..config import Settings
from ..models import ContentPiece
from .base import Publisher

log = logging.getLogger("agent.publishing")

API_URL = "https://api.ayrshare.com/api/post"

# mapeo de nuestras plataformas internas a las de Ayrshare
PLATFORM_MAP = {
    "instagram_reels": "instagram",
    "tiktok": "tiktok",
    "youtube_shorts": "youtube",
}


class AyrsharePublisher(Publisher):
    name = "ayrshare"

    def __init__(self, settings: Settings):
        super().__init__(settings)
        if not settings.ayrshare_api_key:
            raise ValueError("PUBLISHER=ayrshare pero falta AYRSHARE_API_KEY")

    def create_draft(self, piece: ContentPiece) -> str:
        platforms = [
            PLATFORM_MAP[p]
            for p in self.settings.content_cfg.get("platforms", [])
            if p in PLATFORM_MAP
        ]
        media_url = piece.asset.video_url
        payload = {
            "post": self.compose_text(piece),
            "platforms": platforms or ["instagram", "tiktok", "youtube"],
            "mediaUrls": [media_url] if media_url else [],
            "approvalRequired": True,  # NO publica hasta aprobacion manual
            "youTubeOptions": {
                "title": piece.idea.title[:95],
                "shorts": True,
            },
        }
        headers = {
            "Authorization": f"Bearer {self.settings.ayrshare_api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(API_URL, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        body = resp.json()
        ref = body.get("id", "unknown")
        log.info("Borrador en Ayrshare creado (approvalRequired): %s", ref)
        return str(ref)
