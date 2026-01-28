from pathlib import Path
from typing import Optional

from src.clients.audio_downloader import download_and_normalize
from src.clients.llm_client import build_llm_client
from src.clients.rss_client import fetch_new_episodes
from src.clients.transcriber import clean_transcript, transcribe_audio
from src.storage import db, paths
from src.utils.config import load_yaml
from src.utils.logging import get_logger
from src.utils.time import hst_day_bounds_to_utc, parse_hst_date

logger = get_logger(__name__)


def run(
    config_dir: Path,
    episode_ids: Optional[list[str]] = None,
    episode_urls: Optional[list[str]] = None,
) -> None:
    paths.ensure_dirs()
    conn = db.get_conn()
    db.init_db(conn)

    podcasts_config = load_yaml(config_dir / "podcasts.yaml")
    podcast_cfg = podcasts_config.get("podcasts", [])
    start_date = podcasts_config.get("start_date")
    model_cfg = load_yaml(config_dir / "models.yaml")

    db.upsert_podcasts_from_config(conn, podcast_cfg)

    llm_cfg = model_cfg.get("llm", {})
    cleanup_enabled = llm_cfg.get("cleanup", False)
    llm_client = None
    if cleanup_enabled:
        llm_client = build_llm_client(llm_cfg)

    episode_id_set = set(episode_ids or [])
    episode_url_set = set(episode_urls or [])
    start_utc = None
    if start_date and not episode_id_set and not episode_url_set:
        start_utc, _ = hst_day_bounds_to_utc(parse_hst_date(start_date))

    if not episode_id_set and not episode_url_set and not start_utc:
        logger.error(
            "Refusing to process all episodes without scope. "
            "Set start_date in config/podcasts.yaml or pass --episode-id/--episode-url."
        )
        conn.close()
        return

    for podcast in podcast_cfg:
        logger.info("Checking feed %s", podcast.get("name"))
        new_episodes = fetch_new_episodes(
            podcast,
            conn,
            episode_ids=episode_id_set,
            episode_urls=episode_url_set,
            start_date=start_utc,
        )
        logger.info("Found %s new episodes", len(new_episodes))

        for episode in new_episodes:
            try:
                if model_cfg.get("transcription", {}).get("language"):
                    episode["language"] = model_cfg["transcription"]["language"]
                download_and_normalize(episode, conn)
                transcribe_audio(episode, model_cfg.get("transcription", {}), conn)
                if cleanup_enabled and llm_client:
                    clean_transcript(
                        episode,
                        llm_client,
                        paths.PROJECT_ROOT / "src" / "prompts" / "clean_transcript.md",
                        conn,
                    )
            except Exception as exc:
                logger.exception(
                    "Failed processing episode %s: %s", episode.get("id"), exc
                )

    conn.close()
