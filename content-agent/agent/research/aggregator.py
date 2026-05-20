"""Agrega, filtra, deduplica y rankea las tendencias de todas las fuentes."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from ..config import Settings
from ..models import TrendItem
from .reddit import RedditCollector
from .rss_hn import RSSCollector
from .twitter import TwitterCollector
from .youtube import YouTubeCollector

log = logging.getLogger("agent.research")

COLLECTORS = [RedditCollector, YouTubeCollector, TwitterCollector, RSSCollector]


def _normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", title.lower()).strip()


def _dedupe(items: list[TrendItem]) -> list[TrendItem]:
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    out: list[TrendItem] = []
    for it in items:
        norm = _normalize_title(it.title)
        if it.url and it.url in seen_urls:
            continue
        if norm and norm in seen_titles:
            continue
        seen_urls.add(it.url)
        seen_titles.add(norm)
        out.append(it)
    return out


def _filter_fresh(items: list[TrendItem], hours: int) -> list[TrendItem]:
    out = []
    for it in items:
        age = it.age_hours()
        if age is None or age <= hours:
            out.append(it)
    return out


def _rank(items: list[TrendItem]) -> list[TrendItem]:
    """Rankea combinando popularidad relativa por fuente + recencia.

    Las metricas crudas (upvotes vs views) no son comparables entre fuentes,
    asi que normalizamos por el maximo de cada fuente y sumamos un boost de
    frescura (1.0 = recien salido, 0.0 = en el limite de la ventana).
    """
    by_source: dict[str, float] = {}
    for it in items:
        by_source[it.source] = max(by_source.get(it.source, 0.0), it.score)

    def key(it: TrendItem) -> float:
        max_score = by_source.get(it.source, 0.0) or 1.0
        popularity = it.score / max_score
        age = it.age_hours()
        recency = 1.0 if age is None else max(0.0, 1.0 - age / 72.0)
        return 0.65 * popularity + 0.35 * recency

    return sorted(items, key=key, reverse=True)


def _mock_trends() -> list[TrendItem]:
    now = datetime.now(timezone.utc)
    return [
        TrendItem(
            source="reddit",
            title="Nuevo modelo de IA agentica supera benchmarks de razonamiento",
            url="https://reddit.com/r/artificial/mock1",
            summary="La comunidad discute un modelo que planifica y ejecuta tareas multi-paso.",
            score=4200,
            created_at=now,
            extra={"subreddit": "artificial"},
        ),
        TrendItem(
            source="youtube",
            title="Como las PyMEs estan automatizando atencion al cliente con IA",
            url="https://youtube.com/watch?v=mock2",
            summary="Casos reales de agentes de IA respondiendo tickets y vendiendo.",
            score=180000,
            created_at=now,
            extra={"channel": "AI Business"},
        ),
        TrendItem(
            source="rss",
            title="Empresas reportan ROI de IA generativa en procesos internos",
            url="https://example.com/mock3",
            summary="Estudio muestra ahorros de tiempo en tareas administrativas.",
            score=0,
            created_at=now,
            extra={"feed": "MIT Tech Review"},
        ),
    ]


def gather_trends(settings: Settings, top_k: int = 25) -> list[TrendItem]:
    if settings.dry_run:
        log.info("DRY_RUN: usando tendencias simuladas")
        return _mock_trends()

    raw: list[TrendItem] = []
    for cls in COLLECTORS:
        raw.extend(cls(settings).collect())

    hours = int(settings.research_cfg.get("freshness_hours", 48))
    fresh = _filter_fresh(raw, hours)
    deduped = _dedupe(fresh)
    ranked = _rank(deduped)
    log.info(
        "Tendencias: %d crudas -> %d frescas -> %d unicas",
        len(raw),
        len(fresh),
        len(deduped),
    )
    return ranked[:top_k]
