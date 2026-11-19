# MeetingIQ backend — Phase 1

FastAPI + MySQL backend for meeting creation and file uploads (SQLite works as a fallback).

## 1. Create the MySQL database (once)

Requires MySQL 8.0.16 or newer, running locally. Edit the password in `setup_mysql.sql`, then:

```powershell
cd meetingiq\backend
Get-Content setup_mysql.sql | mysql -u root -p
```

(Or paste the contents of `setup_mysql.sql` into MySQL Workbench and run it.)

## 2. Configure

```powershell
Copy-Item .env.example .env
notepad .env   # set the same password you used in setup_mysql.sql
```

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

## Endpoints (Phase 1)

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /api/health | Health check |
| POST | /api/meetings | Create meeting |
| GET | /api/meetings | List meetings (newest first) |
| GET | /api/meetings/{id} | Meeting details with files |
| POST | /api/meetings/{id}/files | Upload one or more files |
| GET | /api/meetings/{id}/analysis | Analysis result (only when status is `completed`, otherwise 409) |
| PUT | /api/meetings/{id}/status | Set the analysis status (used by the pipeline) |

## Limits

Audio (.mp3 .wav .m4a .ogg .flac) 200 MB; video (.mp4 .mov .mkv .webm) 1 GB; presentations (.pptx .pdf) 100 MB. Change these in `app/config.py`.

## Analysis status

Each meeting moves through these statuses. The results page is only available at `completed`:

| Status | Set by | Meaning |
|---|---|---|
| `created` | Creating the meeting | No files yet |
| `uploaded` | Uploading files | Ready to analyze |
| `processing` | The pipeline, when it starts | Being analyzed |
| `completed` | The pipeline, after writing its result files | Results available |
| `failed` | The pipeline, on error | No results |

The pipeline sets the status with:

```powershell
curl.exe -X PUT http://localhost:8000/api/meetings/MEETING_ID/status -H "Content-Type: application/json" -d '{\"status\": \"completed\"}'
```

Write the result files **before** setting `completed`. `processing` and `completed` are refused until the meeting has files. While a meeting is `processing`, the meeting and results pages check every 5 seconds and show the results as soon as it completes.

## Analysis results

`GET /api/meetings/{id}/analysis` returns what the results page (`/meetings/{id}/results`) displays. The format is defined in `app/analysis_schemas.py`. The endpoint reads the first of these that exists in `storage/meetings/<meeting_id>/`:

1. **`analysis.json`**, already in that format.
2. **The pipeline's raw files**, converted by `app/services/pipeline_adapter.py`. Any subset works:

   | File | Contents |
   |---|---|
   | `transcript.json` | Whisper/Groq transcription (`text`, `duration`, `segments`) |
   | `slides_text.json` | Text and speaker notes per slide |
   | `vision_results.json` | Diagram components, relationships and workflow per slide |
   | `meeting_minutes.json` | Overview, discussion summary, decisions, action items, pending items |

   Anything these files don't provide is listed in the response's `missing` field, and the page shows it as not available. Currently that's speaker labels, slide timing, conflict detection, and links from decisions to the transcript.
3. **Sample data** from `app/sample_data/sample_analysis.json` (`"is_sample": true`), only if `SERVE_SAMPLE_ANALYSIS=true` is set in `.env` (useful for UI work). Otherwise a completed meeting without result files returns 404.

Invalid files return 500, with the reason in the server log. `analysis.json` is also checked so that every speaker, transcript line and slide it points to exists.

### Tests

```powershell
pip install -r requirements-dev.txt
python -m pytest
```

`tests/fixtures/sprint14/` holds a real set of pipeline output files. Copy them into `storage/meetings/<meeting_id>/` to see them on the results page.
