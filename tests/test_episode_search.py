from types import SimpleNamespace

from src.clients import episode_search


def test_search_feed_matches_title(monkeypatch):
    entries = [
        {"title": "Foo Bar", "link": "https://example.com/foo", "guid": "id1"},
        {"title": "Baz", "link": "https://example.com/baz", "guid": "id2"},
    ]
    monkeypatch.setattr(
        episode_search.feedparser,
        "parse",
        lambda url: SimpleNamespace(entries=entries),
    )

    results = episode_search.search_feed("url", "pid", "Pod", "foo")
    assert len(results) == 1
    assert results[0].title == "Foo Bar"
    assert results[0].guid == "id1"
