from types import SimpleNamespace

from src.clients import rss_client
from src.storage import db


def test_fetch_new_episodes_filters_by_episode_id(monkeypatch, tmp_path):
    feed_entries = [
        {"guid": "id-1", "title": "Ep1", "enclosures": [{"href": "a"}]},
        {"guid": "id-2", "title": "Ep2", "enclosures": [{"href": "b"}]},
    ]

    monkeypatch.setattr(
        rss_client.feedparser,
        "parse",
        lambda url: SimpleNamespace(entries=feed_entries),
    )

    conn = db.get_conn(tmp_path / "test.duckdb")
    db.init_db(conn)
    db.upsert_podcasts_from_config(
        conn, [{"id": "p1", "name": "P1", "rss_url": "url"}]
    )

    episodes = rss_client.fetch_new_episodes(
        {"id": "p1", "rss_url": "url"},
        conn,
        episode_ids={"id-2"},
    )

    assert len(episodes) == 1
    assert episodes[0]["id"] == "id-2"
    conn.close()


def test_fetch_new_episodes_filters_by_episode_url(monkeypatch, tmp_path):
    feed_entries = [
        {
            "guid": "id-1",
            "title": "Ep1",
            "link": "https://example.com/ep1",
            "enclosures": [{"href": "https://cdn.example.com/ep1.mp3"}],
        },
        {
            "guid": "id-2",
            "title": "Ep2",
            "link": "https://example.com/ep2",
            "enclosures": [{"href": "https://cdn.example.com/ep2.mp3"}],
        },
    ]

    monkeypatch.setattr(
        rss_client.feedparser,
        "parse",
        lambda url: SimpleNamespace(entries=feed_entries),
    )

    conn = db.get_conn(tmp_path / "test.duckdb")
    db.init_db(conn)
    db.upsert_podcasts_from_config(
        conn, [{"id": "p1", "name": "P1", "rss_url": "url"}]
    )

    episodes = rss_client.fetch_new_episodes(
        {"id": "p1", "rss_url": "url"},
        conn,
        episode_urls={"https://example.com/ep2"},
    )

    assert len(episodes) == 1
    assert episodes[0]["id"] == "id-2"
    conn.close()
