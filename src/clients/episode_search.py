from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import feedparser


def _normalize(text: Optional[str]) -> str:
    return (text or "").strip().lower()


@dataclass
class EpisodeMatch:
    podcast_id: str
    podcast_name: str
    title: str
    link: str
    guid: str
    pub_date: Optional[str]


def search_feed(
    rss_url: str,
    podcast_id: str,
    podcast_name: str,
    query: str,
) -> list[EpisodeMatch]:
    parsed = feedparser.parse(rss_url)
    needle = _normalize(query)
    matches: list[EpisodeMatch] = []

    for entry in parsed.entries:
        title = entry.get("title", "")
        link = entry.get("link", "")
        guid = entry.get("guid") or entry.get("id") or ""
        pub_date = entry.get("published") or entry.get("updated")

        haystacks = [_normalize(title), _normalize(link), _normalize(guid)]
        if any(needle in h for h in haystacks):
            matches.append(
                EpisodeMatch(
                    podcast_id=podcast_id,
                    podcast_name=podcast_name,
                    title=title,
                    link=link,
                    guid=str(guid).strip(),
                    pub_date=pub_date,
                )
            )

    return matches


def search_feeds(
    feeds: Iterable[dict], query: str
) -> list[EpisodeMatch]:
    results: list[EpisodeMatch] = []
    for feed in feeds:
        results.extend(
            search_feed(
                feed["rss_url"],
                feed["id"],
                feed.get("name", feed["id"]),
                query,
            )
        )
    return results
