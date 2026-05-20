"""Colector de Reddit via OAuth (app tipo 'script')."""

from __future__ import annotations

from datetime import datetime, timezone

import requests

from ..models import TrendItem
from .base import Collector

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API_BASE = "https://oauth.reddit.com"


class RedditCollector(Collector):
    name = "reddit"

    def enabled(self) -> bool:
        return bool(
            self.settings.reddit_client_id and self.settings.reddit_client_secret
        )

    def _token(self) -> str:
        auth = (self.settings.reddit_client_id, self.settings.reddit_client_secret)
        resp = requests.post(
            TOKEN_URL,
            auth=auth,
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": self.settings.reddit_user_agent},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _collect(self) -> list[TrendItem]:
        token = self._token()
        headers = {
            "Authorization": f"bearer {token}",
            "User-Agent": self.settings.reddit_user_agent,
        }
        limit = int(self.cfg.get("per_source_limit", 15))
        items: list[TrendItem] = []
        for sub in self.cfg.get("subreddits", []):
            resp = requests.get(
                f"{API_BASE}/r/{sub}/hot",
                headers=headers,
                params={"limit": limit},
                timeout=30,
            )
            resp.raise_for_status()
            for child in resp.json().get("data", {}).get("children", []):
                d = child.get("data", {})
                if d.get("stickied"):
                    continue
                created = d.get("created_utc")
                items.append(
                    TrendItem(
                        source="reddit",
                        title=d.get("title", "").strip(),
                        url=f"https://reddit.com{d.get('permalink', '')}",
                        summary=(d.get("selftext", "") or "")[:600],
                        score=float(d.get("score", 0)),
                        created_at=datetime.fromtimestamp(created, tz=timezone.utc)
                        if created
                        else None,
                        extra={"subreddit": sub, "num_comments": d.get("num_comments", 0)},
                    )
                )
        return items
