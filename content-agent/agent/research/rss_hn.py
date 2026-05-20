"""Colector RSS / Hacker News. No requiere credenciales."""

from __future__ import annotations

from datetime import datetime, timezone
from time import mktime

import feedparser

from ..models import TrendItem
from .base import Collector


class RSSCollector(Collector):
    name = "rss"

    def enabled(self) -> bool:
        return bool(self.cfg.get("rss_feeds"))

    def _collect(self) -> list[TrendItem]:
        limit = int(self.cfg.get("per_source_limit", 15))
        items: list[TrendItem] = []
        for url in self.cfg.get("rss_feeds", []):
            feed = feedparser.parse(url)
            source_name = feed.feed.get("title", url)
            for entry in feed.entries[:limit]:
                created = None
                if getattr(entry, "published_parsed", None):
                    created = datetime.fromtimestamp(
                        mktime(entry.published_parsed), tz=timezone.utc
                    )
                summary = getattr(entry, "summary", "") or ""
                # HN comment counts viajan en el campo 'points'/'comments' a veces
                items.append(
                    TrendItem(
                        source="rss",
                        title=getattr(entry, "title", "").strip(),
                        url=getattr(entry, "link", ""),
                        summary=summary[:600],
                        score=0.0,
                        created_at=created,
                        extra={"feed": source_name},
                    )
                )
        return items
