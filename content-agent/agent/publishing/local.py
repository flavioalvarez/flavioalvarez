"""Publisher local: deja los borradores en una cola de revision en disco.

Es el default y siempre funciona (sin credenciales). Genera un archivo
markdown por pieza para revisar comodo + entradas en una cola JSON.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from ..models import ContentPiece
from .base import Publisher

log = logging.getLogger("agent.publishing")


class LocalPublisher(Publisher):
    name = "local"

    def create_draft(self, piece: ContentPiece) -> str:
        out_dir = self.settings.output_dir / "review_queue"
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        slug = "".join(
            c for c in piece.idea.title.lower().replace(" ", "-") if c.isalnum() or c == "-"
        )[:40]
        ref = f"{stamp}-{slug}"

        text = self.compose_text(piece)
        idea = piece.idea

        sb_lines = [f"**Frame mode:** {idea.frame_mode}\n"]
        for fr in idea.storyboard:
            chosen = fr.approved_image
            chosen_ref = (chosen.path or chosen.url) if chosen else "(sin elegir)"
            sb_lines.append(
                f"- **Frame {fr.role}** — {fr.description}\n"
                f"  - prompt: {fr.prompt}\n"
                f"  - variantes: {len(fr.variants)} | elegida: {chosen_ref}\n"
            )
        storyboard_md = "\n".join(sb_lines)

        md = out_dir / f"{ref}.md"
        md.write_text(
            f"# {idea.title}\n\n"
            f"**Estado:** PENDIENTE DE APROBACION\n\n"
            f"**Hook:** {idea.hook}\n\n"
            f"**Guion:**\n{idea.script}\n\n"
            f"**Prompt de video (seedance):**\n{idea.video_prompt}\n\n"
            f"## Storyboard\n{storyboard_md}\n"
            f"**Caption + hashtags:**\n{text}\n\n"
            f"**Video:** {piece.asset.video_path or piece.asset.video_url or '-'}\n\n"
            f"**Basado en:** {', '.join(idea.based_on)}\n",
            encoding="utf-8",
        )

        queue = out_dir / "queue.jsonl"
        with open(queue, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ref": ref, **piece.to_dict()}, ensure_ascii=False) + "\n")

        log.info("Borrador local creado: %s", md)
        return ref
