from src.storage import paths
from src.utils.strings import slugify


def test_slugify():
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("   ") == "untitled"


def test_report_path_for_episode(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "REPORTS_DIR", tmp_path)
    path = paths.report_path_for_episode("2026-01-26", "FSmi", "My Title!")
    assert path.name == "2026-01-26__fsmi__my-title.md"


def test_transcript_clean_path_extension(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "TRANSCRIPTS_DIR", tmp_path)
    path = paths.transcript_clean_path("fsmi", "episode-1")
    assert path.name == "episode-1.md"
