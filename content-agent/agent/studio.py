"""Etapas individuales del flujo, pensadas para aprobacion humana paso a paso.

Cada funcion es un escalon que se puede ejecutar y revisar por separado:

    1. research_and_ideate()  -> ideas con guion + prompts (revisar/editar el prompt de video)
    2. generate_storyboard()  -> 2-3 variantes de imagen por frame (nano banana) para elegir
    3. approve_frame()         -> elegis la variante de cada frame
    4. render_video()          -> genera el video (seedance) con el/los frame(s) aprobados
    5. publish_draft()         -> encola el borrador para aprobacion final de publicacion

`pipeline.run()` encadena todo esto de corrido (modo automatico / dry-run).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .config import Settings
from .generation import HiggsfieldClient
from .ideation import generate_ideas
from .models import (
    ContentIdea,
    ContentPiece,
    GeneratedAsset,
    GeneratedImage,
)
from .publishing import Publisher, get_publisher
from .research import gather_trends

log = logging.getLogger("agent.studio")


def research_and_ideate(settings: Settings, n: Optional[int] = None) -> list[ContentIdea]:
    n = n or settings.pieces_per_run
    trends = gather_trends(settings)
    if not trends:
        return []
    return generate_ideas(settings, trends, n)


def _maybe_client(settings: Settings, client: Optional[HiggsfieldClient]) -> Optional[HiggsfieldClient]:
    if client is not None:
        return client
    if settings.dry_run or not settings.higgsfield_api_key:
        return None
    return HiggsfieldClient(settings)


def generate_storyboard(
    settings: Settings,
    idea: ContentIdea,
    out_dir: Path,
    variants: Optional[int] = None,
    client: Optional[HiggsfieldClient] = None,
    slug: str = "piece",
) -> ContentIdea:
    """Genera N variantes de imagen por cada frame del storyboard (nano banana)."""
    variants = variants or int(settings.content_cfg.get("storyboard_variants", 3))
    aspect = settings.content_cfg.get("aspect_ratio", "9:16")
    client = _maybe_client(settings, client)
    out_dir.mkdir(parents=True, exist_ok=True)

    for fr in idea.storyboard:
        if client is None:  # dry-run / sin credenciales
            fr.variants = [
                GeneratedImage(
                    variant=i,
                    url=f"https://example.com/{slug}_{fr.role}_v{i}.png",
                    path=None,
                )
                for i in range(variants)
            ]
            continue
        dest = out_dir / f"{slug}_{fr.role}.png"
        fr.variants = client.generate_image_variants(
            fr.prompt, dest, count=variants, aspect_ratio=aspect
        )
    return idea


def approve_frame(idea: ContentIdea, role: str, variant: int) -> None:
    fr = idea.frame(role)
    if fr is None:
        raise ValueError(f"La idea no tiene frame '{role}' (modo={idea.frame_mode})")
    if not any(v.variant == variant for v in fr.variants):
        raise ValueError(f"Variante {variant} inexistente para frame '{role}'")
    fr.approved_variant = variant


def auto_approve_first_variant(idea: ContentIdea) -> None:
    """Para modo automatico/dry-run: elige la variante 0 de cada frame."""
    for fr in idea.storyboard:
        if fr.variants and fr.approved_variant is None:
            fr.approved_variant = fr.variants[0].variant


def render_video(
    settings: Settings,
    idea: ContentIdea,
    out_dir: Path,
    client: Optional[HiggsfieldClient] = None,
    slug: str = "piece",
) -> GeneratedAsset:
    """Genera el video con seedance usando los frames aprobados."""
    missing = [fr.role for fr in idea.storyboard if fr.approved_image is None]
    if missing:
        raise ValueError(f"Faltan aprobar variantes de los frames: {missing}")

    first = idea.frame("first")
    last = idea.frame("last")
    first_url = first.approved_image.url if first else None
    last_url = last.approved_image.url if last else None

    client = _maybe_client(settings, client)
    if client is None:  # dry-run / sin credenciales
        return GeneratedAsset(video_url=f"https://example.com/{slug}_video.mp4")

    aspect = settings.content_cfg.get("aspect_ratio", "9:16")
    duration = int(settings.content_cfg.get("video_duration_seconds", 10))
    dest = out_dir / f"{slug}_video.mp4"
    url, path = client.generate_video(
        idea.video_prompt,
        dest=dest,
        first_frame_url=first_url,
        last_frame_url=last_url,
        aspect_ratio=aspect,
        duration=duration,
    )
    return GeneratedAsset(video_url=url, video_path=str(path))


def publish_draft(
    settings: Settings, piece: ContentPiece, publisher: Optional[Publisher] = None
) -> str:
    publisher = publisher or get_publisher(settings)
    return publisher.create_draft(piece)
