# MeetingIQ (Multimodal LLM)

MeetingIQ analyzes meetings from what was **said** (the recording) and what was **shown** (the slides). You upload a recording and the deck; the analysis produces the minutes of the meeting (summary, decisions, action items, pending items) and flags **conflicts**: places where people disagreed, or where what was said contradicts the slides.

It runs as a website and as an Android/iOS app, both backed by the same FastAPI server.

## Project layout

```text
multimodal-llm/
|-- backend/                 FastAPI + SQLAlchemy API            -> backend/README.md
|   |-- app/
|   |   |-- routers/         meetings, files, status, analysis endpoints
|   |   |-- services/        storage, analysis loading, pipeline-output adapter
|   |   |-- analysis_schemas.py   format of the analysis the results page reads
|   |   `-- sample_data/     example analysis for UI work
|   |-- formats/             JSON format for conflicts.json        -> backend/formats/README.md
|   |-- tests/               pytest tests and real pipeline output as fixtures
|   `-- storage/meetings/    uploaded files and analysis output, per meeting (not committed)
|-- frontend/                React + Vite web app                  -> frontend/README.md
|   |-- src/                 pages, components, API calls, styles
|   |-- android/, ios/       Capacitor native app projects          -> frontend/MOBILE.md
|   `-- capacitor.config.json
`-- README.md
```

## Technology

- **Backend:** Python, FastAPI, SQLAlchemy; MySQL via `DATABASE_URL`, or SQLite if it isn't set
- **Frontend:** React 18, React Router, Vite
- **Mobile:** Capacitor 8 (Android and iOS) wrapping the same React app
- **Files:** stored on the local filesystem under `backend/storage/meetings/`

## Running it

Start the backend, then the frontend, in two terminals.

**Backend** (details, MySQL setup and endpoints in [backend/README.md](backend/README.md)):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Without a `.env` file the backend uses a local SQLite database, which is enough to try it out. API docs: http://localhost:8000/docs

**Frontend** ([frontend/README.md](frontend/README.md)):

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server forwards `/api` to the backend on port 8000.

**Mobile app** ([frontend/MOBILE.md](frontend/MOBILE.md)): start the backend with `--host 0.0.0.0`, then `npm run mobile:android` (Android Studio) or `npm run mobile:ios` (Xcode on a Mac). On first launch the app asks for the server address, e.g. `192.168.1.20:8000`.

**Tests:**

```powershell
cd backend
pip install -r requirements-dev.txt
python -m pytest
```

## How a meeting moves through the app

| Status | Shown as | What the user can do |
|---|---|---|
| `created` | Waiting for files | Upload a recording and slides |
| `uploaded` | Ready to analyze | Wait for analysis |
| `processing` | Analyzing | Pages refresh every 5 seconds until it finishes |
| `completed` | Analyzed | **View results**: minutes, then conflicts |
| `failed` | Analysis failed | **Retry analysis** |

The results page is only available once a meeting is `completed`. The analysis pipeline sets the status (`PUT /api/meetings/{id}/status`) and writes its output to `backend/storage/meetings/<meeting_id>/`:

| File | Produced by |
|---|---|
| `transcript.json` | Speech-to-text (Whisper) |
| `slides_text.json` | Slide text extraction |
| `vision_results.json` | Diagram reading on slides |
| `meeting_minutes.json` | LLM: minutes, decisions, action items |
| `conflicts.json` | LLM: conflicts ([format](backend/formats/README.md)) |

The backend combines whichever of these exist into what the results page shows, and tells the page which parts are missing (for example "conflict detection hasn't run").

## Status

- **Done:** meeting upload, status tracking, results page (minutes and conflicts), retry for failed analyses, sharing the results (print/PDF, email through your own email app, copy as text), meetings search with status filters, dark mode, Android/iOS app projects.
- **Analysis pipeline:** the speech-to-text, slide and LLM pipeline is on the `feature/phase-2-llms` branch and isn't merged here yet. On this branch, `POST /api/meetings/{id}/analyze` (the Retry button) is a placeholder that only checks for existing result files; see `backend/app/services/analysis_runner.py`.
- **Not yet built:** speaker identification, conflict detection in the pipeline (the format is defined), linking decisions back to transcript lines, push notifications in the mobile app (needs a Firebase project), and running the native apps on a device.

## Keeping secrets and data out of Git

Don't commit `.venv/`, `node_modules/`, `.env`, the SQLite database, uploaded meeting media or `backend/storage/meetings/`. These are already in `.gitignore`.
