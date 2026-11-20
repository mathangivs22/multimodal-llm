# MeetingIQ backend — Phase 1

FastAPI + MySQL backend for meeting creation and file uploads (SQLite works as a fallback).

## 1. Create the MySQL database (once)

Requires MySQL 8.0.16 or newer, running locally. Edit the password in `setup_mysql.sql`, then:

```powershell
cd backend
Get-Content setup_mysql.sql | mysql -u root -p
```

(Or paste the contents of `setup_mysql.sql` into MySQL Workbench and run it.)

## 2. Configure

Create a file named `.env` in `backend/` with the database address, using the same password as in `setup_mysql.sql`:

```
DATABASE_URL=mysql+pymysql://meetingiq:YOUR_PASSWORD@localhost:3306/meetingiq?charset=utf8mb4
```

URL-encode the password if it contains `@ : / # %`. Never commit `.env`.

If `DATABASE_URL` is missing, the app falls back to a local SQLite file `meetingiq.db`.

## 3. Install and run (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

If activation is blocked, run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

On first start, the tables and `storage/meetings/` are created automatically. Check in MySQL with `USE meetingiq; SHOW TABLES;` and you should see `meetings` and `meeting_files`.

For the phone app, start the backend with `--host 0.0.0.0` so other devices on the network can reach it (see `frontend/MOBILE.md`). `CORS_EXTRA_ORIGINS` in `.env` adds allowed origins, e.g. a hosted website.

## Verify

Open http://localhost:8000/docs (Swagger UI), or in a second PowerShell window:

```powershell
# 1. Health check
curl.exe http://localhost:8000/api/health

# 2. Create a meeting (copy the "id" from the response)
curl.exe -X POST http://localhost:8000/api/meetings -H "Content-Type: application/json" -d '{\"title\": \"Architecture review\"}'

# 3. Upload files (replace MEETING_ID and paths)
curl.exe -X POST http://localhost:8000/api/meetings/MEETING_ID/files -F "files=@C:\path\to\meeting.mp3" -F "files=@C:\path\to\slides.pptx"

# 4. Check the meeting and its files
curl.exe http://localhost:8000/api/meetings/MEETING_ID
```

Expected: files appear in `storage/meetings/<meeting_id>/` with unique names, and the meeting status becomes `uploaded`.

Error checks: uploading a `.txt` returns 415, an unknown meeting ID returns 404, an empty file returns 400.

## Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /api/health | Health check |
| POST | /api/meetings | Create meeting |
| GET | /api/meetings | List meetings (newest first) |
| GET | /api/meetings/{id} | Meeting details with files and `latest_job` (current analysis step, or why it failed) |
| POST | /api/meetings/{id}/files | Upload one or more files |
| POST | /api/meetings/{id}/analyze | Start or retry the analysis pipeline in the background (202; 409 if already running, 400 without files) |
| GET | /api/meetings/{id}/analysis | What the results page shows (only when status is `completed`, otherwise 409) |
| GET | /api/meetings/{id}/results | The pipeline's raw results from the database |
| GET | /api/meetings/{id}/slides/{slide_id}/image | A rendered slide image |
| PUT | /api/meetings/{id}/status | **Testing only**: set a meeting's status by hand (see below) |
| GET | /api/action-items?status=open\|done\|all&owner= | Action items of every completed meeting, soonest deadline first |
| PATCH | /api/action-items/{id} | Tick an action item as done or open again: `{"status": "done"}` |

## Limits

Audio (.mp3 .wav .m4a .ogg .flac) 200 MB; video (.mp4 .mov .mkv .webm) 1 GB; presentations (.pptx .pdf) 100 MB. Change these in `app/config.py`.

## Action items across meetings

`routers/action_items.py` lists the action items of all **completed** meetings (with each meeting's title and when the cited transcript line was said) and ticks them. It uses the existing `action_items` table, with no schema changes. Ticking is refused (409) while the meeting is being analyzed, and an unknown id gives 404.

- **Ticks survive re-analysis**: before a run clears the old results, the pipeline remembers which tasks were done and marks the same task (matched by its text, ignoring case and punctuation) done again.
- **Deadlines without a year** ("November 20", "Nov 20th") get the next such date on or after the day the meeting was created, so they can go into a calendar. Relative ones ("next Friday") stay text only (`deadline_text`).
- Meetings whose results come from JSON files have no rows in `action_items`, so they don't appear and can't be ticked.

## Analysis pipeline

`POST /api/meetings/{id}/analyze` (also the **Retry analysis** button) runs `app/services/pipeline.py` in the background:

1. **Transcribe** recordings with faster-whisper (`WHISPER_MODEL`, default `small`).
2. **Read slides**: python-pptx for .pptx text and notes, PyMuPDF for PDFs. Slide images come from PDFs, or from .pptx through PowerPoint on Windows.
3. **Read diagrams** on slide images with a vision model in Ollama (`OLLAMA_VISION_MODEL`, default `qwen3-vl:4b`).
4. **Write the minutes** with a text model in Ollama (`OLLAMA_MINUTES_MODEL`, default `qwen2.5:3b`).

It needs Ollama running locally with both models pulled. Each run is recorded in `analysis_jobs` with its current step (`stage`) and, on failure, the reason (`error_message`); the meeting and results pages show both.

## Analysis status

Each meeting moves through these statuses. The results page is only available at `completed`:

| Status | Set by | Meaning |
|---|---|---|
| `created` | Creating the meeting | No files yet |
| `uploaded` | Uploading files | Ready to analyze |
| `processing` | `POST /analyze` / the pipeline | Being analyzed |
| `completed` | The pipeline, after saving the minutes | Results available |
| `failed` | The pipeline, on error | No results; Retry is offered |

While a meeting is `processing`, the meeting and results pages check every 5 seconds and show the results as soon as it completes.

## Analysis results

`GET /api/meetings/{id}/analysis` returns what the results page (`/meetings/{id}/results`) displays, in the format defined in `app/analysis_schemas.py`. It reads the **first** of these sources that has results for the meeting:

1. **The database** (`app/services/db_results.py`): the tables the pipeline writes. This is the normal source.
2. **`analysis.json`** in `storage/meetings/<meeting_id>/`, already in that format.
3. **JSON result files** in that folder, converted by `app/services/pipeline_adapter.py`: `transcript.json`, `slides_text.json`, `vision_results.json`, `meeting_minutes.json` and `conflicts.json` ([format](formats/README.md)). Any subset works.
4. **Sample data** (`app/sample_data/sample_analysis.json`), only with `SERVE_SAMPLE_ANALYSIS=true` in `.env`.

Sources 2-4 are for working on the results page without running the pipeline. To use them, copy the files into the meeting's storage folder and mark it completed by hand:

```powershell
curl.exe -X PUT http://localhost:8000/api/meetings/MEETING_ID/status -H "Content-Type: application/json" -d '{\"status\": \"completed\"}'
```

Whatever the source, the response's `missing` field lists what it couldn't provide (for example speaker labels, or conflicts when detection hasn't run), and the page says so instead of implying there was nothing to find.

### Database tables

Created automatically at startup (`create_all`; new tables only, existing ones are never altered).

| Table | One row per | Read for |
|---|---|---|
| `meetings` | meeting | title, `duration`, `status` |
| `meeting_files` | uploaded file | recording names when a meeting has several (their timestamps each start at 0:00) |
| `analysis_jobs` | analysis run | current `stage`, `error_message` (newest by `started_at`) |
| `transcript_segments` | Whisper segment | `seq` (1, 2, … across the meeting), `start_sec`, `end_sec`, `text` |
| `slides` | slide | `slide_number` (per deck), `title`, `body_text`, `speaker_notes`, `image_path` |
| `slide_visuals` | slide with a diagram reading | `components`, `relationships`, `workflow_steps`, `uncertain_relationships` |
| `meeting_minutes` | completed meeting | `overview` (`title`, `date`, `participants`), `discussion_summary`, `pending_items`, `next_meeting` |
| `decisions` | decision | `text`, `kind` (`finalized`/`suggested`), `source_seq` |
| `action_items` | action item | `task`, `owner`, `deadline_date`/`deadline_text`, `status` (`open`/`done`), `source_seq` |
| `conflict_checks` | meeting where conflict detection ran | marks "checked", even when nothing was found |
| `conflicts` | conflict | `kind`, `severity`, `status`, `title`, `description`, `resolution`, `sort_order` |
| `conflict_positions` | side of a conflict | `speaker`, `statement`, `source_seqs` (transcript `seq`s), `slide_ids` |

`source_seq`/`source_seqs` point at `transcript_segments.seq`; the results page turns them into source timestamps. A meeting has database results once its `meeting_minutes` row exists. No pipeline step fills the conflict tables yet.

### Tests

```powershell
pip install -r requirements-dev.txt
python -m pytest
```

`tests/test_db_results.py` fills an in-memory database the way the pipeline does and checks what the results page receives. `tests/fixtures/sprint14/` holds a set of JSON result files (an earlier format, with a transcript from Whisper on Groq); copy them into `storage/meetings/<meeting_id>/` to see them on the results page without the pipeline.
