from typing import Optional

import click
from dotenv import load_dotenv

from src.clients.episode_search import search_feeds
from src.pipelines.daily_summarize import run as summarize_run
from src.pipelines.fetch_and_transcribe import run as fetch_run
from src.storage import paths
from src.utils.config import load_yaml


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
@click.option(
    "--transcript-path",
    multiple=True,
    help="Transcript file path(s) to summarize, may be passed multiple times.",
)
def summarize(date: Optional[str], transcript_path: tuple[str, ...]) -> None:
    """Generate daily summary for episodes by publication date."""
    config_dir = paths.PROJECT_ROOT / "config"
    summarize_run(
        config_dir=config_dir,
        date_str=date,
        transcript_paths=list(transcript_path),
    )


@cli.command("list-episodes")
@click.option(
    "--query",
    required=True,
    help="Search term for episode title, link, or GUID.",
)
@click.option(
    "--podcast-id",
    type=str,
    help="Restrict search to a single podcast id.",
)
def list_episodes(query: str, podcast_id: Optional[str]) -> None:
    """List matching episodes from configured RSS feeds."""
    config_dir = paths.PROJECT_ROOT / "config"
    config = load_yaml(config_dir / "podcasts.yaml")
    feeds = config.get("podcasts", [])
    if podcast_id:
        feeds = [feed for feed in feeds if feed.get("id") == podcast_id]
    results = search_feeds(feeds, query)
    if not results:
        click.echo("No matches found.")
        return

    for match in results:
        click.echo(f"- {match.title}")
        click.echo(f"  podcast_id: {match.podcast_id}")
        if match.pub_date:
            click.echo(f"  pub_date: {match.pub_date}")
        if match.guid:
            click.echo(f"  guid: {match.guid}")
        if match.link:
            click.echo(f"  link: {match.link}")


if __name__ == "__main__":
    cli()
