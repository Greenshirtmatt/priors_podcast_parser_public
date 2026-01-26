import subprocess
import tempfile
from typing import Optional

import requests

from src.storage import db, paths
from src.utils.logging import get_logger

logger = get_logger(__name__)


def _probe_duration(path: str) -> Optional[float]:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return float(result.stdout.strip())
    except Exception:
        return None


def download_and_normalize(episode: dict, conn) -> None:
    audio_url = episode.get("audio_url")
    if not audio_url:
        raise ValueError("Missing audio_url for episode")

    target_path = paths.audio_path(episode["podcast_id"], episode["id"])
    logger.info("Downloading audio for %s", episode.get("title") or episode["id"])

    with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as temp_file:
        with requests.get(audio_url, stream=True, timeout=60) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    temp_file.write(chunk)
        temp_file.flush()
        temp_path = temp_file.name

    logger.info("Normalizing audio for %s", episode.get("title") or episode["id"])
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            temp_path,
            "-ac",
            "1",
            "-ar",
            "16000",
            "-vn",
            str(target_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    episode["audio_path"] = str(target_path)
    duration = _probe_duration(str(target_path))
    db.update_episode_audio(conn, episode["id"], str(target_path), duration)
    logger.info("Audio saved for %s", episode.get("title") or episode["id"])
