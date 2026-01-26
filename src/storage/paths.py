from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
AUDIO_DIR = DATA_DIR / "audio"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
REPORTS_DIR = DATA_DIR / "reports"
DB_DIR = DATA_DIR / "db"


def ensure_dirs() -> None:
    for path in [AUDIO_DIR, TRANSCRIPTS_DIR, REPORTS_DIR, DB_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def audio_path(podcast_id: str, episode_id: str) -> Path:
    path = AUDIO_DIR / podcast_id / f"{episode_id}.wav"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def transcript_raw_path(podcast_id: str, episode_id: str) -> Path:
    path = TRANSCRIPTS_DIR / "raw" / podcast_id / f"{episode_id}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def transcript_clean_path(podcast_id: str, episode_id: str) -> Path:
    path = TRANSCRIPTS_DIR / "clean" / podcast_id / f"{episode_id}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def daily_report_path(report_date: str) -> Path:
    path = REPORTS_DIR / f"{report_date}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    return DB_DIR / "podcasts.duckdb"
