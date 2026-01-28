from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import yaml

from src.utils.markdown import build_transcript_markdown, strip_front_matter


def _load_episode_metadata(db_path: Path) -> dict[tuple[str, str], dict]:
    if not db_path.exists():
        return {}

    conn = duckdb.connect(str(db_path))
    rows = conn.execute(
        """
        SELECT e.id,
               e.podcast_id,
               e.title,
               e.pub_date,
               e.audio_url,
               p.name AS podcast_name
        FROM episodes e
        LEFT JOIN podcasts p ON p.id = e.podcast_id;
        """
    ).fetchall()
    conn.close()

    metadata: dict[tuple[str, str], dict] = {}
    for row in rows:
        episode_id, podcast_id, title, pub_date, audio_url, podcast_name = row
        metadata[(podcast_id, episode_id)] = {
            "title": title,
            "pub_date": pub_date,
            "audio_url": audio_url,
            "podcast_name": podcast_name,
        }
    return metadata


def _load_language(config_path: Path) -> str:
    if not config_path.exists():
        return "en"
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    lang = (
        cfg.get("transcription", {}).get("language")
        or cfg.get("models", {}).get("transcription", {}).get("language")
    )
    return lang or "en"


def migrate(
    root: Path, db_path: Path, language: str, dry_run: bool
) -> tuple[int, int, int]:
    created = 0
    skipped = 0
    updated = 0
    metadata = _load_episode_metadata(db_path)

    for txt_path in sorted(root.rglob("*.txt")):
        md_path = txt_path.with_suffix(".md")
        if md_path.exists():
            skipped += 1
            continue
        podcast_id = txt_path.parent.name
        episode_id = txt_path.stem
        episode_meta = metadata.get((podcast_id, episode_id), {})
        transcript_text = txt_path.read_text(encoding="utf-8")

        markdown_text = build_transcript_markdown(
            title=episode_meta.get("title") or episode_id,
            publisher=episode_meta.get("podcast_name") or podcast_id,
            date=episode_meta.get("pub_date"),
            url=None,
            language=language,
            podcast_id=podcast_id,
            episode_id=episode_id,
            audio_url=episode_meta.get("audio_url"),
            transcript_text=strip_front_matter(transcript_text),
        )

        if not dry_run:
            md_path.write_text(markdown_text, encoding="utf-8")
        created += 1

    for md_path in sorted(root.rglob("*.md")):
        raw_text = md_path.read_text(encoding="utf-8")
        if raw_text.lstrip().startswith("---\n"):
            continue

        podcast_id = md_path.parent.name
        episode_id = md_path.stem
        episode_meta = metadata.get((podcast_id, episode_id), {})
        markdown_text = build_transcript_markdown(
            title=episode_meta.get("title") or episode_id,
            publisher=episode_meta.get("podcast_name") or podcast_id,
            date=episode_meta.get("pub_date"),
            url=None,
            language=language,
            podcast_id=podcast_id,
            episode_id=episode_id,
            audio_url=episode_meta.get("audio_url"),
            transcript_text=strip_front_matter(raw_text),
        )
        if not dry_run:
            md_path.write_text(markdown_text, encoding="utf-8")
        updated += 1
    return created, skipped, updated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-time migration from .txt to .md for clean transcripts."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("data/transcripts/clean"),
        help="Root directory containing clean transcript .txt files.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/db/podcasts.duckdb"),
        help="DuckDB path for episode metadata.",
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Override language for front matter (defaults to config or 'en').",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing .md files.",
    )
    args = parser.parse_args()

    if not args.root.exists():
        raise SystemExit(f"Root path does not exist: {args.root}")

    language = args.language or _load_language(Path("config/models.yaml"))
    created, skipped, updated = migrate(args.root, args.db, language, args.dry_run)
    action = "Would create" if args.dry_run else "Created"
    updated_action = "Would update" if args.dry_run else "Updated"
    print(
        f"{action} {created} .md files, skipped {skipped} existing, "
        f"{updated_action} {updated} without front matter."
    )


if __name__ == "__main__":
    main()
