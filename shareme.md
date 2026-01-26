Here is a concise, updated build spec based on the current implementation.

# Podcast Pipeline Build Spec (Handoff)

## Goal
Build a local, terminal-first podcast pipeline that:
1) Pulls new episodes from RSS feeds.
2) Downloads and normalizes audio.
3) Transcribes with Whisper CLI.
4) Optionally cleans transcripts with OpenAI.
5) Stores metadata and paths in DuckDB.
6) Generates daily summaries by publication date (HST day, queried via UTC range).
7) Outputs a single daily Markdown report.

Design should remain modular for future blog or email outputs.

---

## Stack and Defaults
- Python 3.11 recommended (3.9+ works).
- Virtual environment in `.venv`.
- Dependencies in `requirements.txt`.
- Whisper CLI via `openai-whisper`.
- OpenAI API via Responses API.
- DuckDB for storage.
- HST (Pacific/Honolulu, UTC-10, no DST) for date grouping, stored as UTC.

---

## Prerequisites (choices and steps for the user)
**Choices to make**
- RSS feed list: provide the exact feed URL(s) and podcast IDs.
- Episode filtering: decide whether to run all new episodes or specify a list of GUIDs or URLs.
- LLM model: confirm the OpenAI model name to use.
- Date policy: confirm storing pub dates in UTC and summarizing by HST day.

**Steps to take**
- Create `.env` with `LLM_API_KEY` (and optional `OPENAI_MODEL`, `TIMEZONE`).
- Populate `config/podcasts.yaml` with the chosen feed(s).
- (Optional) Run fetch with `--episode-id` or `--episode-url` to target specific episodes.

---

## Repo Structure (implemented)
```
config/
  podcasts.yaml
  models.yaml
data/
  audio/
  transcripts/
  reports/
  db/podcasts.duckdb
scripts/
  preflight.sh
src/
  main.py
  pipelines/
    fetch_and_transcribe.py
    daily_summarize.py
  clients/
    rss_client.py
    audio_downloader.py
    transcriber.py
    llm_client.py
  storage/
    db.py
    paths.py
  prompts/
    clean_transcript.md
    daily_summarizer.md
  utils/
    logging.py
    time.py
tests/
  test_db.py
  test_time.py
  test_rss_client.py
```

---

## Config
**.env** (not committed):
```
LLM_API_KEY=...
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-5-mini
TIMEZONE=Pacific/Honolulu  # optional override
```

**config/podcasts.yaml**
```
podcasts:
  - id: fsmi
    name: "FSMI Feed"
    rss_url: "https://feeds.megaphone.fm/FSMI7575968096"
```

**config/models.yaml**
```
transcription:
  engine: "whisper"
  model_name: "base"
  language: "en"

llm:
  provider: "openai"
  model: "gpt-5-mini"
  cleanup: true
  max_output_tokens: 2048
```

---

## Storage (DuckDB)
Tables:
- `podcasts(id, name, rss_url)`
- `episodes(id, podcast_id, title, pub_date, audio_url, audio_path, transcript_raw_path, transcript_clean_path, duration_seconds, processed_at, summary_generated, summary_doc_id)`
- `daily_summaries(id, date, report_path, created_at)`

Publication dates are stored in UTC, and daily HST summaries query the UTC range
for the HST day using half-open bounds `[start, next_day)`.

---

## Pipelines
**Fetch + transcribe** (`python -m src.main fetch-and-transcribe`)
1) Read feeds, insert new episodes by GUID.
2) Download and normalize audio to 16k mono WAV via ffmpeg.
3) Transcribe using Whisper CLI.
4) Optional LLM cleanup (OpenAI).

**Daily summary** (`python -m src.main summarize --date YYYY-MM-DD`)
1) Find unsummarized episodes whose `pub_date` falls in HST day.
2) Build prompt with transcripts (cleaned preferred).
3) Save output to `data/reports/{date}.md`.
4) Mark episodes summarized in DB.

---

## CLI Filters
Limit the fetch/transcribe pipeline to specific episodes:
```
python -m src.main fetch-and-transcribe \
  --episode-id <GUID> \
  --episode-url <link or enclosure URL>
```

For Farnam Street, valid episode URLs are the `<link>` values:
- https://fs.blog/knowledge-project-podcast/morgan-housel-3/
- https://fs.blog/knowledge-project-podcast/outliers-peter-d-kaufman/

---

## Preflight
Run once to create venv, install deps, and ensure ffmpeg:
```
bash scripts/preflight.sh
```

---

## Notes
- Logs go to stdout. Whisper output is currently captured, not streamed.
- If needed, add `--log-file` or stream subprocess output for live progress.
- Current LLM client supports OpenAI only; other providers can be added later.
