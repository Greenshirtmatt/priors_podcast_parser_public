from pathlib import Path

from src.pipelines import daily_summarize


def test_load_transcripts_from_paths(tmp_path):
    transcript = tmp_path / "t1.txt"
    transcript.write_text("hello", encoding="utf-8")

    episodes = daily_summarize._load_transcripts_from_paths([str(transcript)])
    assert len(episodes) == 1
    assert episodes[0]["transcript_text"] == "hello"
    assert episodes[0]["id"] == "t1"
