Here’s an implementation plan you can paste into Claude Code as a “build this”
spec. It’s written assuming a local, terminal-first workflow on macOS, with
Parakeet or Whisper, DuckDB, and an LLM API (Claude/OpenAI/Gemini) available.

---

### Goal

Build a **podcast extraction pipeline** that:

1. Pulls new episodes from a fixed list of podcast RSS feeds.
2. Downloads and normalizes audio.
3. Transcribes audio to text (locally, via Parakeet or Whisper).
4. Optionally “cleans up” transcripts with an LLM.
5. Stores episodes and transcripts in **DuckDB** with processing metadata.
6. Runs a **daily summarizer** that:
   - Produces per-podcast summaries (host, guest, key topics, key themes).
   - Extracts **notable quotes**.
   - Extracts **companies / startups mentioned**.
   - Suggests **investment theses**.
   - Proposes **tweet ideas**.
7. Outputs a single **daily markdown/HTML document** per day.

Keep the design **modular** so we can later plug in a blog-post generator on
top.

---

### 1. Project structure

Create a small repo with a structure like:

```
podcast_pipeline/
	pyproject.toml or requirements.txt
	README.md
	.env.example
	config/
		podcasts.yaml
		models.yaml
	src/
		__init__.py
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
	data/
		audio/          # raw + normalized audio
		transcripts/    # raw + cleaned transcripts
		reports/        # daily summary docs
		db/
			podcasts.duckdb
```

Key principles:

- All configuration is **outside code** (`config/`).
- Pipeline entrypoints are in `src/pipelines/`.
- All disk paths and DB access go through `storage/`.

---

### 2. Configuration and environment

1. **Environment variables** (via `.env`):
   - `LLM_API_KEY`
   - `LLM_PROVIDER` (e.g. `anthropic`, `openai`, `gemini`, `local`)
   - Optional: `OPENAI_MODEL`, `ANTHROPIC_MODEL`, etc.
2. **Podcast config**: `config/podcasts.yaml`

   ```yaml
   podcasts:
       - id: lennys_podcast
         name: "Lenny's Podcast"
         rss_url: "https://example.com/lenny/feed"
       - id: how_i_ai
         name: "How I AI"
         rss_url: "https://example.com/howiai/feed"
   ```

3. **Model config**: `config/models.yaml`

   ```yaml
   transcription:
       engine: "parakeet" # or "whisper"
       model_name: "parakeet-large" # or whisper model id

   llm:
       provider: "anthropic"
       model: "claude-3-5-sonnet-latest"
   ```

4. `README.md` should describe:
   - Prereqs (Python version, ffmpeg installed, Parakeet/Whisper).
   - How to run the daily pipeline (single command / cron).

---

### 3. Storage: DuckDB schema and paths

Create `storage/db.py` to manage a DuckDB database at
`data/db/podcasts.duckdb`.

Tables:

1. **podcasts**

   ```sql
    CREATE TABLE IF NOT EXISTS podcasts (
   id TEXT PRIMARY KEY,           -- internal id, e.g. "how_i_ai"
   name TEXT NOT NULL,
   rss_url TEXT NOT NULL
    );
   ```

2. **episodes**

   ```sql
    CREATE TABLE IF NOT EXISTS episodes (
   id TEXT PRIMARY KEY,           -- stable episode GUID / hash
   podcast_id TEXT NOT NULL REFERENCES podcasts(id),
   title TEXT,
   pub_date TIMESTAMP,
   audio_url TEXT,
   audio_path TEXT,               -- local normalized audio file
   transcript_raw_path TEXT,      -- raw ASR
   transcript_clean_path TEXT,    -- LLM-cleaned
   duration_seconds DOUBLE,
   processed_at TIMESTAMP,        -- when transcription finished
   summary_generated BOOLEAN DEFAULT FALSE,
   summary_doc_id TEXT            -- foreign key to daily_summaries.id when included
    );
   ```

3. **daily_summaries**

   ```sql
    CREATE TABLE IF NOT EXISTS daily_summaries (
   id TEXT PRIMARY KEY,           -- e.g. "2025-06-13"
   date DATE NOT NULL,
   report_path TEXT NOT NULL,     -- markdown/HTML file path
   created_at TIMESTAMP NOT NULL
    );
   ```

Add helper methods:

- `init_db()`
- `upsert_podcasts_from_config(podcasts: list[dict])`
- `get_unprocessed_episodes_for_date(date)`
- `mark_episodes_as_summarized(episode_ids, summary_id)`

Paths utility `storage/paths.py`:

- `audio_path(podcast_id, episode_id) -> Path`
- `transcript_raw_path(podcast_id, episode_id) -> Path`
- `transcript_clean_path(podcast_id, episode_id) -> Path`
- `daily_report_path(date) -> Path`

---

### 4. RSS fetching and episode discovery

Create `clients/rss_client.py`:

- Use `feedparser` or `podcastparser` to read RSS.
- For each feed, determine **new episodes**:
  - Use stable episode ID: prefer RSS `guid`, fallback to `link` or hash of
    `(podcast_id, title, pub_date)`.

Pseudo-interface:

```python
def fetch_new_episodes(podcast_config, db_conn) -> list[Episode]:
	"""
	- Read RSS feed URL.
	- For each item, check if episode id exists in episodes table.
	- If not, insert with basic metadata (title, pub_date, audio_url).
	- Return list of new episode rows (with ids and audio_url).
	"""
```

---

### 5. Audio download and normalization (FFmpeg)

Create `clients/audio_downloader.py`:

1. Download file from `audio_url` → temporary path.
2. Normalize with `ffmpeg`:
   - Convert to `16kHz mono WAV` or whatever Parakeet/Whisper prefers.
   - Detect duration (for logging).

Pseudo-interface:

```python
def download_and_normalize(episode, db_conn, paths) -> None:
	"""
	- Download audio.
	- Run ffmpeg to produce normalized .wav.
	- Save to data/audio/{podcast_id}/{episode_id}.wav
	- Update episodes.audio_path and duration_seconds in DB.
	"""
```

Use `subprocess.run(["ffmpeg", ...])` with error handling.

---

### 6. Transcription (Parakeet or Whisper)

Create `clients/transcriber.py`:

- Wrap Parakeet or Whisper CLI / Python API.

Interface:

```python
def transcribe_audio(episode, model_cfg, db_conn, paths) -> None:
	"""
	- Given episodes.audio_path, run local ASR.
	- Write raw transcript text to data/transcripts/raw/{podcast_id}/{episode_id}.txt
	- Update episodes.transcript_raw_path and processed_at.
	"""
```

Implementation options:

- If Parakeet has CLI: call via `subprocess`.
- If using `openai` or `whisper` Python library, import directly.

---

### 7. Transcript cleanup via LLM (optional but supported)

Create `prompts/clean_transcript.md` with instructions similar to Tom’s:

```markdown
You are a transcript editor.

Goal:

- Clean up a podcast transcript while preserving _all_ content and length.
- Remove filler like "um", "uh", repeated stutters, obvious transcription
  artifacts.
- Preserve technical details, domain-specific terms, company names, numbers,
  URLs.
- Do NOT summarize, shorten, or reorder content.
- Keep speaker changes and Q/A structure clear, but you do not need explicit
  speaker tags.

Return only the cleaned transcript as plain text.
```

Create `clients/llm_client.py`:

- Abstract over providers (Anthropic, OpenAI, Gemini, local model).
- Basic `complete(prompt: str, max_tokens: int) -> str`.

Then implement `clean_transcript` in `transcriber.py` or a new module:

```python
def clean_transcript(episode, llm_client, db_conn, paths) -> None:
	"""
	- Load raw transcript text.
	- Build prompt from clean_transcript.md + transcript.
	- Call LLM.
	- Save cleaned text to transcript_clean_path.
	- Update episodes.transcript_clean_path in DB.
	"""
```

Make this step **configurable**: allow skipping cleanup if not needed.

---

### 8. Daily summarizer prompt

Create `prompts/daily_summarizer.md`.

This prompt should:

- Take **all transcripts for a single day** (cleaned if available, else raw).
- Produce a **structured markdown document**:
  - Header: date.
  - For each episode:

    ```markdown
    ## {Podcast Name}: {Episode Title}

    - **Host:** …
    - **Guest(s):** …
    - **Comprehensive Summary:**
      - …
    - **Key Topics:**
      - …
    - **Key Themes:**
      - …
    - **Notable Quotes:**
      - "Quote" — Speaker
    - **Companies / Startups Mentioned:**
      - Name — brief description (if available)
    - **Investment Theses (VC-oriented):**
      - Thesis statement → 1–3 sentence rationale.
    - **Tweet Suggestions:**
      - Tweet 1…
      - Tweet 2…
    ```

Draft something like:

```markdown
You are an expert analyst for a venture capital firm.

You receive one or more podcast transcripts from today. For each transcript,
produce the following sections in Markdown:

[...describe structure as above...]

Guidelines:

- Be concrete and specific.
- Preserve important technical details and context.
- Quotes should be verbatim or lightly cleaned; attribute them to the correct
  speaker where possible.
- Investment theses should be framed as potential areas for deeper research, not
  as recommendations.
- Tweets should be under 280 characters and self-contained; no hashtags unless
  they are widely used.
- If some fields cannot be inferred (e.g., guest name), leave them blank or mark
  as "Unknown".

At the top of the document, include:

# Podcast Summaries for {DATE}
```

---

### 9. Daily summarizer pipeline

Create `src/pipelines/daily_summarize.py`:

Workflow (for a given date, default = today in Honolulu TZ):

1. Find all **episodes processed** on that date that do **not yet** have
   `summary_generated = TRUE`.

   ```python
   episodes = db.get_episodes_for_date(date, only_unsummarized=True)
   if not episodes:
    return
   ```

2. For each episode:
   - Load transcript:
     - Prefer `transcript_clean_path` if present.
     - Fallback to `transcript_raw_path`.
3. Build a single **LLM prompt**:
   - System part: `daily_summarizer.md`.
   - User part: for each episode, include:

     ```markdown
     === EPISODE START === Podcast ID: {podcast_id} Podcast Name: {podcast_name}
     Episode ID: {episode_id} Episode Title: {title} Publication Date: {pub_date}

     TRANSCRIPT: {transcript_text} === EPISODE END ===
     ```

4. Call LLM (stream or regular).
5. Save full response to `data/reports/{date}.md`.
6. Insert a row into `daily_summaries`.
7. Update each episode:
   - `summary_generated = TRUE`
   - `summary_doc_id = daily_summaries.id`.

Provide a small CLI:

```python
# src/main.py
import click

@click.group()
def cli():
	pass

@cli.command()
@click.option("--date", type=str, help="YYYY-MM-DD, defaults to today")
def fetch_and_transcribe(date):
	"""Fetch new episodes, download, normalize, transcribe, clean."""
	# call pipelines.fetch_and_transcribe.run(date)

@cli.command()
@click.option("--date", type=str, help="YYYY-MM-DD, defaults to today")
def summarize(date):
	"""Generate daily summary for episodes processed on date."""
	# call pipelines.daily_summarize.run(date)

if __name__ == "__main__":
	cli()
```

---

### 10. Fetch + transcribe pipeline

Create `src/pipelines/fetch_and_transcribe.py`:

Steps:

1. `init_db()` and `upsert_podcasts_from_config()`.
2. For each podcast:
   - `fetch_new_episodes(...)` from RSS.
   - For each new episode:
     - `download_and_normalize(...)`
     - `transcribe_audio(...)`
     - Optionally `clean_transcript(...)`.
3. All episodes processed get `processed_at=now()`.

This pipeline can run:

- On a schedule (cron, launchd).
- Manually: `python -m src.main fetch-and-transcribe`.

---

### 11. Logging and error handling

- Implement a simple logger in `utils/logging.py` using
  `logging` module.
- Log per episode:
  - Started/finished download.
  - Started/finished transcription.
  - Started/finished cleanup.
  - Errors with stack traces.
- On failure, **do not** delete partial DB entries; mark episodes as partially
  processed so retries are idempotent.

---

### 12. “Email me the daily summary” (optional but ready)

Add a simple email sender later:

- For now, leave a stub in `daily_summarize.py`:

  ```python
  def maybe_send_email(report_path: Path):
   """
   TODO: integrate with SMTP or a service (SendGrid, SES, etc.).
   For now, just log the path so a human can open it.
   """
  ```

Design the daily summary markdown so it can be easily:

- Rendered to HTML (Pandoc or markdown library).
- Pasted into an email client.

---

### 13. What to ask Claude Code to do first

You can give Claude Code this plan and then ask it to implement in stages:

1. **Scaffold the repo and core modules**:
   - `storage/db.py`, `storage/paths.py`,
     `clients/rss_client.py`, `clients/audio_downloader.py`,
     `clients/transcriber.py`, `clients/llm_client.py`,
     `pipelines/fetch_and_transcribe.py`,
     `pipelines/daily_summarize.py`, `prompts/*.md`, CLI
     in `main.py`.
2. **Implement end-to-end for a single podcast**:
   - Hardcode one RSS feed in `podcasts.yaml`.
   - Run: fetch → download → transcribe → summarize for a single day.
3. **Generalize and harden**:
   - Support multiple podcasts.
   - Better error handling, logging, and config.
   - Add simple tests for DB operations and idempotence.

If you paste this into Claude Code and say “Implement this as Python code in
this repo, step by step, asking me before you make big design deviations,” it
should be able to build out the entire pipeline.
