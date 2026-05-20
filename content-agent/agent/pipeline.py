"""Orquestador end-to-end: investigar -> idear -> generar -> encolar borrador."""

from __future__ import annotations

import logging

from .config import Settings
from .generation import HiggsfieldClient
from .ideation import generate_ideas
from .models import ContentPiece, GeneratedAsset
from .publishing import get_publisher
from .research import gather_trends
from .storage import run_dir, write_manifest

log = logging.getLogger("agent.pipeline")


def _generate_assets(
    client: HiggsfieldClient | None,
    settings: Settings,
    piece: ContentPiece,
    out_dir,
    idx: int,
) -> None:
    """Genera imagen (nano banana pro) y luego video (seedance 2.0)."""
    aspect = settings.content_cfg.get("aspect_ratio", "9:16")
    duration = int(settings.content_cfg.get("video_duration_seconds", 10))

    if settings.dry_run or client is None:
        piece.asset = GeneratedAsset(
            image_url="https://example.com/mock-image.png",
            video_url="https://example.com/mock-video.mp4",
        )
        piece.notes.append("DRY_RUN: activos simulados")
        return

    img_dest = out_dir / f"piece_{idx}_image.png"
    img_url, img_path = client.generate_image(
        piece.idea.image_prompt, img_dest, aspect_ratio=aspect
    )
    piece.asset.image_url = img_url
    piece.asset.image_path = str(img_path)

    vid_dest = out_dir / f"piece_{idx}_video.mp4"
    vid_url, vid_path = client.generate_video(
        piece.idea.video_prompt,
        image_url=img_url,
        dest=vid_dest,
        aspect_ratio=aspect,
        duration=duration,
    )
    piece.asset.video_url = vid_url
    piece.asset.video_path = str(vid_path)


def run(settings: Settings) -> list[ContentPiece]:
    n = settings.pieces_per_run
    log.info("== Okeybot content agent | %d piezas | dry_run=%s ==", n, settings.dry_run)

    # 1) investigar
    trends = gather_trends(settings)
    if not trends:
        log.warning("No se encontraron tendencias; nada que generar.")
        return []

    # 2) idear
    ideas = generate_ideas(settings, trends, n)
    if not ideas:
        log.warning("El ideador no devolvio ideas.")
        return []

    out = run_dir(settings.output_dir)
    client = None
    if not settings.dry_run:
        if settings.higgsfield_api_key:
            client = HiggsfieldClient(settings)
        else:
            log.warning("Sin HIGGSFIELD_API_KEY: se omite la generacion de activos.")

    publisher = get_publisher(settings)
    pieces: list[ContentPiece] = []

    # 3) generar activos + 4) encolar borrador (con aprobacion)
    for idx, idea in enumerate(ideas, 1):
        piece = ContentPiece(idea=idea)
        try:
            _generate_assets(client, settings, piece, out, idx)
        except Exception as exc:  # noqa: BLE001
            log.error("Fallo la generacion de la pieza %d: %s", idx, exc)
            piece.status = "failed"
            piece.notes.append(f"generacion fallida: {exc}")
            pieces.append(piece)
            continue

        try:
            piece.publish_ref = publisher.create_draft(piece)
            piece.status = "needs_approval"
        except Exception as exc:  # noqa: BLE001
            log.error("Fallo al crear el borrador de la pieza %d: %s", idx, exc)
            piece.status = "failed"
            piece.notes.append(f"publicacion fallida: {exc}")
        pieces.append(piece)

    manifest = write_manifest(out, pieces)
    log.info("Listo. Manifest: %s", manifest)
    ok = sum(1 for p in pieces if p.status == "needs_approval")
    log.info("%d/%d piezas listas para aprobacion en '%s'", ok, len(pieces), publisher.name)
    return pieces
