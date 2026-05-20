from datetime import datetime, timedelta, timezone

from agent.models import TrendItem
from agent.research.aggregator import _dedupe, _filter_fresh, _rank


def _now():
    return datetime.now(timezone.utc)


def test_dedupe_by_url_and_title():
    items = [
        TrendItem(source="reddit", title="GPT nuevo modelo", url="http://a"),
        TrendItem(source="rss", title="GPT nuevo modelo!", url="http://b"),  # mismo titulo norm.
        TrendItem(source="rss", title="Otro tema", url="http://a"),  # misma url
        TrendItem(source="youtube", title="Distinto", url="http://c"),
    ]
    out = _dedupe(items)
    assert len(out) == 2
    assert {i.url for i in out} == {"http://a", "http://c"}


def test_filter_fresh_keeps_undated_and_recent():
    items = [
        TrendItem(source="reddit", title="viejo", url="x", created_at=_now() - timedelta(hours=100)),
        TrendItem(source="reddit", title="nuevo", url="y", created_at=_now() - timedelta(hours=2)),
        TrendItem(source="reddit", title="sin fecha", url="z", created_at=None),
    ]
    out = _filter_fresh(items, hours=48)
    titles = {i.title for i in out}
    assert "viejo" not in titles
    assert {"nuevo", "sin fecha"} <= titles


def test_rank_prefers_popular_and_recent():
    items = [
        TrendItem(source="reddit", title="poco", url="a", score=10, created_at=_now() - timedelta(hours=70)),
        TrendItem(source="reddit", title="mucho", url="b", score=1000, created_at=_now()),
    ]
    ranked = _rank(items)
    assert ranked[0].title == "mucho"
