# Podcast Parser

Local, terminal-first pipeline to fetch podcast episodes, transcribe audio, and
produce per-episode summary reports.

## Prereqs

- macOS
- Python 3.11 recommended (3.9+ should work)
- Homebrew
- ffmpeg (installed via preflight)

## Setup

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Or run the preflight script which creates the venv, installs dependencies,
and installs or upgrades ffmpeg:

```bash
bash scripts/preflight.sh
```

## Configuration

- `.env` (copy from `.env.example`)
- `config/podcasts.yaml` for RSS feeds
- `config/models.yaml` for transcription and LLM settings

## Run

Fetch, download, transcribe, and optionally clean transcripts:

```bash
python -m src.main fetch-and-transcribe
```

By default, fetch-and-transcribe refuses to process an entire back catalog. Set
`start_date` in `config/podcasts.yaml` (HST) or pass `--episode-id` or
`--episode-url` to define scope.

Fetch only specific episodes by GUID (repeatable):

```bash
python -m src.main fetch-and-transcribe \
  --episode-id 20c61048-f560-11f0-84f5-6f1bb3eae5e5 \
  --episode-id fca3a480-eda5-11f0-a112-bf33c8952bcc
```

Search feeds for an episode by keyword (title, link, or GUID):

```bash
python -m src.main list-episodes --query "mauboussin" --podcast-id fsmi
```

Fetch only specific episodes by URL (repeatable):

```bash
python -m src.main fetch-and-transcribe \
  --episode-url https://fs.blog/knowledge-project-podcast/morgan-housel-3/ \
  --episode-url https://fs.blog/knowledge-project-podcast/outliers-peter-d-kaufman/
```

Generate summaries by **publication date** (YYYY-MM-DD). Each episode is
summarized separately and written to its own report file:

```bash
python -m src.main summarize --date 2026-01-26
```

Summarize specific transcript files directly (repeatable):

```bash
python -m src.main summarize \
  --transcript-path data/transcripts/clean/fsmi/20c61048-f560-11f0-84f5-6f1bb3eae5e5.md \
  --transcript-path data/transcripts/clean/fsmi/fca3a480-eda5-11f0-a112-bf33c8952bcc.md
```

If `--date` is omitted, the pipeline uses today’s date in Hawaii–Aleutian
Standard Time (Pacific/Honolulu, UTC-10, no DST), unless `TIMEZONE` is set.
Publication dates are stored in UTC, and summaries convert the requested HST
date to a UTC range when querying.
Report filenames follow:
`data/reports/{date}__{podcast_id}__{safe_title}.md`

## Output

- `data/audio/` normalized audio
- `data/transcripts/` raw and cleaned transcripts (cleaned transcripts are Markdown with YAML front matter)
- `data/reports/` per-episode summaries
- `data/db/podcasts.duckdb`
