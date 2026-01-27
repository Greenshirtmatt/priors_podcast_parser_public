from datetime import datetime
from types import SimpleNamespace

from src.clients import rss_client
from src.storage import db
from src.utils.time import hst_day_bounds_to_utc, parse_hst_date


def test_fetch_new_episodes_respects_start_date(monkeypatch, tmp_path):
    entries = [
        {
            "guid": "old",
            "title": "Old",
            "published": "Tue, 01 Jan 2025 10:00:00 -0000",
            "enclosures": [{"href": "a"}],
        },
        {
            "guid": "new",
            "title": "New",
            "published": "Tue, 21 Jan 2026 10:00:00 -0000",
            "enclosures": [{"href": "b"}],
        },
    ]

    monkeypatch.setattr(
        rss_client.feedparser,
        "parse",
        lambda url: SimpleNamespace(entries=entries),
    )

    conn = db.get_conn(tmp_path / "test.duckdb")
    db.init_db(conn)
    db.upsert_podcasts_from_config(
        conn, [{"id": "p1", "name": "P1", "rss_url": "url"}]
    )

    start_utc, _ = hst_day_bounds_to_utc(parse_hst_date("2026-01-01"))

    episodes = rss_client.fetch_new_episodes(
        {"id": "p1", "rss_url": "url"},
        conn,
        start_date=start_utc,
    )

    assert len(episodes) == 1
    assert episodes[0]["id"] == "new"
    conn.close()


def test_fetch_new_episodes_bypass_start_date_with_episode_filter(
    monkeypatch, tmp_path
):
    entries = [
        {
            "guid": "old",
            "title": "Old",
            "published": "Tue, 01 Jan 2025 10:00:00 -0000",
            "enclosures": [{"href": "a"}],
        }
    ]

    monkeypatch.setattr(
        rss_client.feedparser,
        "parse",
        lambda url: SimpleNamespace(entries=entries),
    )

    conn = db.get_conn(tmp_path / "test.duckdb")
    db.init_db(conn)
    db.upsert_podcasts_from_config(
        conn, [{"id": "p1", "name": "P1", "rss_url": "url"}]
    )

    start_utc, _ = hst_day_bounds_to_utc(parse_hst_date("2026-01-01"))

    episodes = rss_client.fetch_new_episodes(
        {"id": "p1", "rss_url": "url"},
        conn,
        episode_ids={"old"},
        start_date=start_utc,
    )

    assert len(episodes) == 1
    assert episodes[0]["id"] == "old"
    conn.close()
