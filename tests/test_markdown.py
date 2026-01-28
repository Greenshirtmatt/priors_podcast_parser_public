from datetime import datetime, timezone

from src.utils.markdown import build_transcript_markdown, strip_front_matter


def test_build_transcript_markdown_includes_front_matter():
    text = build_transcript_markdown(
        title="Episode 1",
        publisher="Test Podcast",
        date=datetime(2026, 1, 26, tzinfo=timezone.utc),
        url="https://example.com/ep1",
        language="en",
        podcast_id="p1",
        episode_id="e1",
        audio_url="https://cdn.example.com/ep1.mp3",
        transcript_text="hello world",
    )

    assert text.startswith("---\n")
    assert "title: Episode 1" in text
    assert "publisher: Test Podcast" in text
    assert "url: https://example.com/ep1" in text
    assert text.rstrip().endswith("hello world")


def test_strip_front_matter_removes_header():
    raw = "---\ntitle: T1\n---\n\ncontent"
    assert strip_front_matter(raw) == "content"
