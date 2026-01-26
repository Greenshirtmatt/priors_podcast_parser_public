from datetime import datetime

from src.storage import db


def test_init_db_creates_tables(tmp_path):
    conn = db.get_conn(tmp_path / "test.duckdb")
    db.init_db(conn)
    tables = {
        row[0] for row in conn.execute("SHOW TABLES;").fetchall()
    }
    assert "podcasts" in tables
    assert "episodes" in tables
    assert "daily_summaries" in tables
    conn.close()


def test_upsert_podcasts_idempotent(tmp_path):
    conn = db.get_conn(tmp_path / "test.duckdb")
    db.init_db(conn)

    podcasts = [{"id": "a", "name": "A", "rss_url": "url-a"}]
    db.upsert_podcasts_from_config(conn, podcasts)

    updated = [{"id": "a", "name": "A2", "rss_url": "url-a2"}]
    db.upsert_podcasts_from_config(conn, updated)

    row = conn.execute(
        "SELECT name, rss_url FROM podcasts WHERE id = 'a';"
    ).fetchone()
    assert row == ("A2", "url-a2")
    conn.close()


def test_mark_episodes_as_summarized(tmp_path):
    conn = db.get_conn(tmp_path / "test.duckdb")
    db.init_db(conn)

    db.upsert_podcasts_from_config(
        conn, [{"id": "p1", "name": "P1", "rss_url": "url"}]
    )

    db.insert_episode(
        conn,
        {
            "id": "e1",
            "podcast_id": "p1",
            "title": "t",
            "pub_date": datetime.utcnow(),
            "audio_url": "a",
        },
    )

    db.mark_episodes_as_summarized(conn, ["e1"], "2026-01-26")
    row = conn.execute(
        "SELECT summary_generated, summary_doc_id FROM episodes WHERE id='e1'"
    ).fetchone()
    assert row == (True, "2026-01-26")
    conn.close()
