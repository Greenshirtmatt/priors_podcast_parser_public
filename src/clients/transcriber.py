import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.storage import db, paths
from src.utils.logging import get_logger
from src.utils.markdown import build_transcript_markdown

logger = get_logger(__name__)


def transcribe_audio(episode: dict, model_cfg: dict, conn) -> None:
    audio_path = episode.get("audio_path") or paths.audio_path(
        episode["podcast_id"], episode["id"]
    )
    output_path = paths.transcript_raw_path(episode["podcast_id"], episode["id"])
    output_dir = output_path.parent

    args = [
        "whisper",
        str(audio_path),
        "--model",
        model_cfg.get("model_name", "base"),
        "--output_format",
        "txt",
        "--output_dir",
        str(output_dir),
    ]
    language = model_cfg.get("language")
    if language:
        args.extend(["--language", language])

    logger.info("Transcribing %s", episode.get("title") or episode["id"])
    subprocess.run(args, check=True, capture_output=True, text=True)

    if not output_path.exists():
        raise FileNotFoundError(f"Expected transcript at {output_path}")

    episode["transcript_raw_path"] = str(output_path)
    db.update_episode_transcript_raw(
        conn,
        episode["id"],
        str(output_path),
        datetime.utcnow(),
    )
    logger.info("Transcription complete for %s", episode.get("title") or episode["id"])


def clean_transcript(
    episode: dict,
    llm_client,
    prompt_path: Path,
    conn,
) -> Optional[Path]:
    raw_path = episode.get("transcript_raw_path")
    if not raw_path:
        return None

    raw_path = Path(raw_path)
    prompt_text = prompt_path.read_text(encoding="utf-8")
    transcript_text = raw_path.read_text(encoding="utf-8")

    full_prompt = f"{prompt_text}\n\n{transcript_text}"
    logger.info("Cleaning transcript for %s", episode.get("title") or episode["id"])
    cleaned_text = llm_client.complete(full_prompt)

    clean_path = paths.transcript_clean_path(episode["podcast_id"], episode["id"])
    markdown_text = build_transcript_markdown(
        title=episode.get("title") or episode["id"],
        publisher=episode.get("podcast_name") or episode.get("podcast_id"),
        date=episode.get("pub_date"),
        url=episode.get("url"),
        language=episode.get("language") or "en",
        podcast_id=episode.get("podcast_id"),
        episode_id=episode.get("id"),
        audio_url=episode.get("audio_url"),
        transcript_text=cleaned_text,
    )
    clean_path.write_text(markdown_text, encoding="utf-8")

    db.update_episode_transcript_clean(conn, episode["id"], str(clean_path))
    logger.info("Transcript cleaned for %s", episode.get("title") or episode["id"])
    return clean_path
