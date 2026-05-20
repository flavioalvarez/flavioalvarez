"""Orquestador end-to-end: encadena las etapas de `studio` de corrido.

Modo automatico (cron / dry-run): genera todo y auto-aprueba la 1ra variante
de cada frame. El flujo con aprobacion humana usa las funciones de `studio`
una por una (ver README / sesion de chat).
"""

from __future__ import annotations

import logging
import re

from .config import Settings
from .generation import HiggsfieldClient
from .models import ContentPiece
from .publishing import get_publisher
from .storage import run_dir, write_manifest
from .studio import (
    auto_approve_first_variant,
    generate_storyboard,
    publish_draft,
    render_video,
    research_and_ideate,
)

log = logging.getLogger("agent.pipeline")


def _slug(text: str, idx: int) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]
    return f"piece_{idx}_{base or 'pieza'}"


def run(settings: Settings) -> list[ContentPiece]:
    n = settings.pieces_per_run
    log.info("== Okeybot content agent | %d piezas | dry_run=%s ==", n, settings.dry_run)

    ideas = research_and_ideate(settings, n)
    if not ideas:
        log.warning("Sin ideas que producir.")
        return []

    out = run_dir(settings.output_dir)
    client = None
    if not settings.dry_run and settings.higgsfield_api_key:
        client = HiggsfieldClient(settings)
    elif not settings.dry_run:
        log.warning("Sin HIGGSFIELD_API_KEY: activos simulados.")

    publisher = get_publisher(settings)
    pieces: list[ContentPiece] = []

    for idx, idea in enumerate(ideas, 1):
        piece = ContentPiece(idea=idea)
        slug = _slug(idea.title, idx)
        try:
            generate_storyboard(settings, idea, out, client=client, slug=slug)
            piece.status = "storyboard_ready"
            auto_approve_first_variant(idea)  # modo automatico
            piece.asset = render_video(settings, idea, out, client=client, slug=slug)
            piece.status = "rendered"
        except Exception as exc:  # noqa: BLE001
            log.error("Fallo produciendo la pieza %d: %s", idx, exc)
            piece.status = "failed"
            piece.notes.append(f"produccion fallida: {exc}")
            pieces.append(piece)
            continue

        try:
            piece.publish_ref = publish_draft(settings, piece, publisher)
            piece.status = "needs_approval"
        except Exception as exc:  # noqa: BLE001
            log.error("Fallo encolando la pieza %d: %s", idx, exc)
            piece.status = "failed"
            piece.notes.append(f"publicacion fallida: {exc}")
        pieces.append(piece)

    manifest = write_manifest(out, pieces)
    ok = sum(1 for p in pieces if p.status == "needs_approval")
    log.info("Listo. %d/%d piezas en '%s'. Manifest: %s", ok, len(pieces), publisher.name, manifest)
    return pieces
