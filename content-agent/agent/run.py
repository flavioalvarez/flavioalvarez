"""Entrypoint CLI:  python -m agent.run [--dry-run] [--pieces N]"""

from __future__ import annotations

import argparse
import logging
import sys

from .config import load_settings
from .pipeline import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Okeybot - agente de contenido vertical")
    parser.add_argument("--dry-run", action="store_true", help="Corre con datos simulados")
    parser.add_argument("--pieces", type=int, default=None, help="Cantidad de piezas")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )

    settings = load_settings()
    if args.dry_run:
        settings.dry_run = True
    if args.pieces is not None:
        settings.pieces_per_run = args.pieces

    pieces = run(settings)
    failed = [p for p in pieces if p.status == "failed"]
    return 1 if (pieces and len(failed) == len(pieces)) else 0


if __name__ == "__main__":
    raise SystemExit(main())
