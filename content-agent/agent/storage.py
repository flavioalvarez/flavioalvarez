"""Persistencia de la corrida: carpeta por dia + manifest JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import ContentPiece


def run_dir(base: Path) -> Path:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    d = base / day
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_manifest(directory: Path, pieces: list[ContentPiece]) -> Path:
    manifest = directory / "manifest.json"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(pieces),
        "pieces": [p.to_dict() for p in pieces],
    }
    manifest.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest
