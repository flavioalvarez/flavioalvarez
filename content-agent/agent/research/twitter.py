"""Colector de Twitter/X via API v2 (busqueda reciente). Opcional."""

from __future__ import annotations

from datetime import datetime

import requests

from ..models import TrendItem
from .base import Collector

SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"


class TwitterCollector(Collector):
    name = "twitter"

    def enabled(self) -> bool:
        return bool(self.settings.twitter_bearer_token)

    def _collect(self) -> list[TrendItem]:
        headers = {"Authorization": f"Bearer {self.settings.twitter_bearer_token}"}
        limit = min(int(self.cfg.get("per_source_limit", 15)), 100)
        items: list[TrendItem] = []

        for query in self.cfg.get("twitter_queries", []):
            full_query = f"({query}) -is:retweet lang:es"
            resp = requests.get(
                SEARCH_URL,
                headers=headers,
                params={
                    "query": full_query,
                    "max_results": max(10, limit),
                    "tweet.fields": "created_at,public_metrics,lang",
                    "sort_order": "relevancy",
                },
                timeout=30,
            )
            resp.raise_for_status()
            for t in resp.json().get("data", []):
                metrics = t.get("public_metrics", {})
                score = (
                    metrics.get("like_count", 0)
                    + 2 * metrics.get("retweet_count", 0)
                    + metrics.get("quote_count", 0)
                )
                created = t.get("created_at")
                items.append(
                    TrendItem(
                        source="twitter",
                        title=t.get("text", "").strip()[:120],
                        url=f"https://twitter.com/i/web/status/{t['id']}",
                        summary=t.get("text", "").strip(),
                        score=float(score),
                        created_at=datetime.fromisoformat(
                            created.replace("Z", "+00:00")
                        )
                        if created
                        else None,
                        extra={"metrics": metrics, "query": query},
                    )
                )
        return items
