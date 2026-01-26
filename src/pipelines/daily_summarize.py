from pathlib import Path

from src.clients.llm_client import build_llm_client
from src.storage import db, paths
from src.utils.config import load_yaml
from src.utils.logging import get_logger
from typing import Iterable, Optional

from src.utils.time import hst_day_bounds_to_utc, parse_date_arg

logger = get_logger(__name__)


def _load_transcript(episode: dict) -> Optional[str]:
    clean_path = episode.get("transcript_clean_path")
    raw_path = episode.get("transcript_raw_path")

    if clean_path and Path(clean_path).exists():
        return Path(clean_path).read_text(encoding="utf-8")
    if raw_path and Path(raw_path).exists():
        return Path(raw_path).read_text(encoding="utf-8")
    return None


def _load_transcripts_from_paths(paths_list: Iterable[str]) -> list[dict]:
    episodes = []
    for path_str in paths_list:
        path = Path(path_str)
        if not path.exists():
            logger.warning("Transcript path missing: %s", path)
            continue
        episodes.append(
            {
                "id": path.stem,
                "title": path.stem,
                "podcast_name": "Manual Selection",
                "podcast_id": "manual",
                "pub_date": None,
                "transcript_text": path.read_text(encoding="utf-8"),
                "transcript_path": str(path),
            }
        )
    return episodes


def run(
    config_dir: Path,
    date_str: Optional[str] = None,
    transcript_paths: Optional[list[str]] = None,
) -> None:
    report_date = parse_date_arg(date_str)
    report_date_str = report_date.isoformat()
    start_utc, end_utc = hst_day_bounds_to_utc(report_date)

    conn = db.get_conn()
    db.init_db(conn)

    model_cfg = load_yaml(config_dir / "models.yaml")
    llm_cfg = model_cfg.get("llm", {})
    llm_client = build_llm_client(llm_cfg)

    episodes = []
    manual_mode = bool(transcript_paths)
    if manual_mode:
        episodes = _load_transcripts_from_paths(transcript_paths or [])
        if not episodes:
            logger.info("No transcripts found for manual summarization.")
            conn.close()
            return
    else:
        episodes = db.get_unsummarized_episodes_for_pub_date_range(
            conn, start_utc, end_utc
        )
        if not episodes:
            logger.info("No episodes to summarize for %s", report_date_str)
            conn.close()
            return

    prompt_template = (
        paths.PROJECT_ROOT / "src" / "prompts" / "daily_summarizer.md"
    ).read_text(encoding="utf-8")
    prompt = prompt_template.replace("{DATE}", report_date_str)

    episode_blocks = []
    summarized_ids = []
    for episode in episodes:
        transcript_text = episode.get("transcript_text") or _load_transcript(episode)
        if not transcript_text:
            logger.warning("Missing transcript for %s", episode.get("id"))
            continue

        episode_block = (
            "=== EPISODE START ===\n"
            f"Podcast ID: {episode.get('podcast_id')}\n"
            f"Podcast Name: {episode.get('podcast_name')}\n"
            f"Episode ID: {episode.get('id')}\n"
            f"Episode Title: {episode.get('title')}\n"
            f"Publication Date: {episode.get('pub_date')}\n\n"
            f"TRANSCRIPT:\n{transcript_text}\n"
            "=== EPISODE END ===\n"
        )
        episode_blocks.append(episode_block)
        summarized_ids.append(episode["id"])

    if not episode_blocks:
        logger.info("No transcripts available to summarize for %s", report_date_str)
        conn.close()
        return

    full_prompt = f"{prompt}\n\n" + "\n".join(episode_blocks)
    response = llm_client.complete(
        full_prompt, max_output_tokens=llm_cfg.get("max_output_tokens")
    )

    report_path = paths.daily_report_path(report_date_str)
    report_path.write_text(response, encoding="utf-8")

    if not manual_mode:
        summary_id = report_date_str
        db.insert_daily_summary(conn, summary_id, report_date_str, str(report_path))
        db.mark_episodes_as_summarized(conn, summarized_ids, summary_id)

    logger.info("Summary written to %s", report_path)
    conn.close()
