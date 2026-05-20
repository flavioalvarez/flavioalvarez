"""Colector de YouTube via Data API v3 (busqueda + estadisticas de videos)."""

from __future__ import annotations

from datetime import datetime

import requests

from ..models import TrendItem
from .base import Collector

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


class YouTubeCollector(Collector):
    name = "youtube"

    def enabled(self) -> bool:
        return bool(self.settings.youtube_api_key)

    def _collect(self) -> list[TrendItem]:
        key = self.settings.youtube_api_key
        limit = int(self.cfg.get("per_source_limit", 15))
        items: list[TrendItem] = []

        for query in self.cfg.get("youtube_queries", []):
            resp = requests.get(
                SEARCH_URL,
                params={
                    "key": key,
                    "q": query,
                    "part": "snippet",
                    "type": "video",
                    "order": "viewCount",
                    "publishedAfter": _published_after(self.cfg),
                    "maxResults": min(limit, 25),
                    "relevanceLanguage": "es",
                },
                timeout=30,
            )
            resp.raise_for_status()
            video_ids = [
                it["id"]["videoId"]
                for it in resp.json().get("items", [])
                if it.get("id", {}).get("videoId")
            ]
            if not video_ids:
                continue

            stats = requests.get(
                VIDEOS_URL,
                params={
                    "key": key,
                    "id": ",".join(video_ids),
                    "part": "snippet,statistics",
                },
                timeout=30,
            )
            stats.raise_for_status()
            for v in stats.json().get("items", []):
                sn = v.get("snippet", {})
                st = v.get("statistics", {})
                items.append(
                    TrendItem(
                        source="youtube",
                        title=sn.get("title", "").strip(),
                        url=f"https://youtube.com/watch?v={v['id']}",
                        summary=(sn.get("description", "") or "")[:600],
                        score=float(st.get("viewCount", 0)),
                        created_at=_parse_dt(sn.get("publishedAt", "")),
                        extra={
                            "channel": sn.get("channelTitle"),
                            "likes": st.get("likeCount"),
                            "query": query,
                        },
                    )
                )
        return items


def _published_after(cfg: dict) -> str:
    from datetime import timedelta, timezone

    hours = int(cfg.get("freshness_hours", 48))
    dt = datetime.now(timezone.utc) - timedelta(hours=hours)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
