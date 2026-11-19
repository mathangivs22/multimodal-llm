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

## Limits

Audio (.mp3 .wav .m4a .ogg .flac) 200 MB; video (.mp4 .mov .mkv .webm) 1 GB; presentations (.pptx .pdf) 100 MB. Change these in `app/config.py`.
