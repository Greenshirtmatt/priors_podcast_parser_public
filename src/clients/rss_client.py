import hashlib
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any, Optional

import feedparser

from src.storage import db
from src.utils.logging import get_logger
from src.utils.time import normalize_to_utc

logger = get_logger(__name__)


def _parse_pub_date(entry: dict[str, Any]) -> Optional[datetime]:
    raw = entry.get("published") or entry.get("updated")
    if not raw:
        return None
    try:
        parsed = parsedate_to_datetime(raw)
        return normalize_to_utc(parsed)
    except (TypeError, ValueError):
        return None


def _extract_audio_url(entry: dict[str, Any]) -> Optional[str]:
    enclosures = entry.get("enclosures") or []
    if enclosures:
        return enclosures[0].get("href")

    for link in entry.get("links", []):
        if link.get("rel") == "enclosure" and link.get("href"):
            return link.get("href")
    return None


def _stable_episode_id(podcast_id: str, entry: dict[str, Any]) -> str:
    guid = entry.get("guid") or entry.get("id")
    if guid:
        return str(guid).strip()

    fallback_parts = [
        podcast_id,
        entry.get("title", ""),
        entry.get("link", ""),
        entry.get("published", ""),
    ]
    digest = hashlib.sha256("|".join(fallback_parts).encode("utf-8")).hexdigest()
    return digest


def _matches_episode_url(entry: dict[str, Any], episode_urls: set[str]) -> bool:
    link = entry.get("link")
    if link and link in episode_urls:
        return True
    enclosures = entry.get("enclosures") or []
    for enclosure in enclosures:
        href = enclosure.get("href")
        if href and href in episode_urls:
            return True
    return False


def fetch_new_episodes(
    podcast_config: dict[str, Any],
    conn,
    episode_ids: Optional[set[str]] = None,
    episode_urls: Optional[set[str]] = None,
    start_date: Optional[datetime] = None,
) -> list[dict[str, Any]]:
    feed = feedparser.parse(podcast_config["rss_url"])
    new_episodes: list[dict[str, Any]] = []

    for entry in feed.entries:
        episode_id = _stable_episode_id(podcast_config["id"], entry)
        if episode_ids and episode_id not in episode_ids:
            continue
        if episode_urls and not _matches_episode_url(entry, episode_urls):
            continue

        pub_date = _parse_pub_date(entry)
        if start_date and pub_date and pub_date < start_date:
            continue

        if db.episode_exists(conn, episode_id):
            continue

        episode = {
            "id": episode_id,
            "podcast_id": podcast_config["id"],
            "title": entry.get("title"),
            "pub_date": pub_date,
            "audio_url": _extract_audio_url(entry),
        }
        if not episode["audio_url"]:
            logger.warning(
                "No audio URL for episode %s (%s)",
                episode_id,
                episode.get("title"),
            )
            continue
        db.insert_episode(conn, episode)
        new_episodes.append(episode)

    return new_episodes
