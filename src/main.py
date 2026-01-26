from typing import Optional

import click
from dotenv import load_dotenv

from src.pipelines.daily_summarize import run as summarize_run
from src.pipelines.fetch_and_transcribe import run as fetch_run
from src.storage import paths


@click.group()
def cli() -> None:
    """Podcast pipeline CLI."""
    load_dotenv()


@cli.command("fetch-and-transcribe")
@click.option("--date", type=str, help="YYYY-MM-DD (reserved for future use)")
@click.option(
    "--episode-id",
    multiple=True,
    help="Episode GUID(s) to fetch, may be passed multiple times.",
)
@click.option(
    "--episode-url",
    multiple=True,
    help="Episode URL(s) to fetch, may be passed multiple times.",
)
def fetch_and_transcribe(
    date: Optional[str],
    episode_id: tuple[str, ...],
    episode_url: tuple[str, ...],
) -> None:
    """Fetch new episodes, download, normalize, transcribe, clean."""
    config_dir = paths.PROJECT_ROOT / "config"
    fetch_run(
        config_dir=config_dir,
        episode_ids=list(episode_id),
        episode_urls=list(episode_url),
    )


@cli.command()
@click.option("--date", type=str, help="YYYY-MM-DD, defaults to today")
def summarize(date: Optional[str]) -> None:
    """Generate daily summary for episodes by publication date."""
    config_dir = paths.PROJECT_ROOT / "config"
    summarize_run(config_dir=config_dir, date_str=date)


if __name__ == "__main__":
    cli()
