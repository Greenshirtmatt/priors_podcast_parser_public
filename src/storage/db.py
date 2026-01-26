from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

import duckdb

from src.storage import paths


def get_conn(db_file: Optional[Path] = None) -> duckdb.DuckDBPyConnection:
    if db_file is None:
        db_file = paths.db_path()
    return duckdb.connect(str(db_file))


def init_db(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS podcasts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            rss_url TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS episodes (
            id TEXT PRIMARY KEY,
            podcast_id TEXT NOT NULL REFERENCES podcasts(id),
            title TEXT,
            pub_date TIMESTAMP,
            audio_url TEXT,
            audio_path TEXT,
            transcript_raw_path TEXT,
            transcript_clean_path TEXT,
            duration_seconds DOUBLE,
            processed_at TIMESTAMP,
            summary_generated BOOLEAN DEFAULT FALSE,
            summary_doc_id TEXT
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_summaries (
            id TEXT PRIMARY KEY,
            date DATE NOT NULL,
            report_path TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL
        );
        """
    )


def upsert_podcasts_from_config(
    conn: duckdb.DuckDBPyConnection, podcasts: list[dict[str, Any]]
) -> None:
    for podcast in podcasts:
        conn.execute(
            """
            INSERT INTO podcasts (id, name, rss_url)
            VALUES (?, ?, ?)
            ON CONFLICT (id)
            DO UPDATE SET name = excluded.name, rss_url = excluded.rss_url;
            """,
            [podcast["id"], podcast["name"], podcast["rss_url"]],
        )


def episode_exists(conn: duckdb.DuckDBPyConnection, episode_id: str) -> bool:
    result = conn.execute(
        "SELECT 1 FROM episodes WHERE id = ? LIMIT 1;", [episode_id]
    ).fetchone()
    return result is not None


def insert_episode(conn: duckdb.DuckDBPyConnection, episode: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO episodes (
            id, podcast_id, title, pub_date, audio_url
        ) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (id) DO NOTHING;
        """,
        [
            episode["id"],
            episode["podcast_id"],
            episode.get("title"),
            episode.get("pub_date"),
            episode.get("audio_url"),
        ],
    )


def update_episode_audio(
    conn: duckdb.DuckDBPyConnection,
    episode_id: str,
    audio_path: str,
    duration_seconds: Optional[float],
) -> None:
    conn.execute(
        """
        UPDATE episodes
        SET audio_path = ?, duration_seconds = ?
        WHERE id = ?;
        """,
        [audio_path, duration_seconds, episode_id],
    )


def update_episode_transcript_raw(
    conn: duckdb.DuckDBPyConnection,
    episode_id: str,
    transcript_path: str,
    processed_at: datetime,
) -> None:
    conn.execute(
        """
        UPDATE episodes
        SET transcript_raw_path = ?, processed_at = ?
        WHERE id = ?;
        """,
        [transcript_path, processed_at, episode_id],
    )


def update_episode_transcript_clean(
    conn: duckdb.DuckDBPyConnection,
    episode_id: str,
    transcript_path: str,
) -> None:
    conn.execute(
        """
        UPDATE episodes
        SET transcript_clean_path = ?
        WHERE id = ?;
        """,
        [transcript_path, episode_id],
    )


def get_unsummarized_episodes_for_pub_date_range(
    conn: duckdb.DuckDBPyConnection,
    start_utc: datetime,
    end_utc: datetime,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT e.*, p.name AS podcast_name
        FROM episodes e
        JOIN podcasts p ON p.id = e.podcast_id
        WHERE e.pub_date >= ? AND e.pub_date < ?
          AND (e.summary_generated = FALSE OR e.summary_generated IS NULL)
        ORDER BY e.pub_date;
        """,
        [start_utc, end_utc],
    ).fetchall()

    columns = [desc[0] for desc in conn.description]
    return [dict(zip(columns, row)) for row in rows]


def get_unprocessed_episodes_for_date_range(
    conn: duckdb.DuckDBPyConnection,
    start_utc: datetime,
    end_utc: datetime,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT e.*, p.name AS podcast_name
        FROM episodes e
        JOIN podcasts p ON p.id = e.podcast_id
        WHERE e.pub_date >= ? AND e.pub_date < ?
          AND e.processed_at IS NULL
        ORDER BY e.pub_date;
        """,
        [start_utc, end_utc],
    ).fetchall()

    columns = [desc[0] for desc in conn.description]
    return [dict(zip(columns, row)) for row in rows]


def mark_episodes_as_summarized(
    conn: duckdb.DuckDBPyConnection,
    episode_ids: Iterable[str],
    summary_id: str,
) -> None:
    episode_ids = list(episode_ids)
    if not episode_ids:
        return
    placeholders = ",".join(["?"] * len(episode_ids))
    conn.execute(
        f"""
        UPDATE episodes
        SET summary_generated = TRUE, summary_doc_id = ?
        WHERE id IN ({placeholders});
        """,
        [summary_id] + episode_ids,
    )


def insert_daily_summary(
    conn: duckdb.DuckDBPyConnection,
    summary_id: str,
    report_date: str,
    report_path: str,
) -> None:
    conn.execute(
        """
        INSERT INTO daily_summaries (id, date, report_path, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (id) DO NOTHING;
        """,
        [summary_id, report_date, report_path, datetime.utcnow()],
    )
