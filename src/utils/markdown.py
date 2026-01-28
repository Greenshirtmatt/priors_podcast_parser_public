from __future__ import annotations

from datetime import datetime
from typing import Optional

import yaml


def _isoformat(value: Optional[object]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def build_front_matter(metadata: dict[str, Optional[object]]) -> str:
    ordered: dict[str, object] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if key == "date":
            value = _isoformat(value)
        ordered[key] = value

    if not ordered:
        return ""

    payload = yaml.safe_dump(
        ordered,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
    ).strip()

    return f"---\n{payload}\n---"


def build_transcript_markdown(
    *,
    title: str,
    publisher: Optional[str],
    date: Optional[object],
    url: Optional[str],
    language: str,
    podcast_id: Optional[str],
    episode_id: Optional[str],
    audio_url: Optional[str],
    transcript_text: str,
) -> str:
    front_matter = build_front_matter(
        {
            "title": title,
            "publisher": publisher,
            "date": date,
            "url": url,
            "language": language,
            "podcast_id": podcast_id,
            "episode_id": episode_id,
            "audio_url": audio_url,
        }
    )

    body = transcript_text.strip()
    if front_matter:
        return f"{front_matter}\n\n{body}\n"
    return f"{body}\n"


def strip_front_matter(text: str) -> str:
    if not text.startswith("---\n"):
        return text

    lines = text.split("\n")
    for idx, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            body = "\n".join(lines[idx + 1 :])
            return body.lstrip("\n")
    return text
