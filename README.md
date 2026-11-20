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

The results page is only available once a meeting is `completed`. **Analyze / Retry** runs the pipeline (`backend/app/services/pipeline.py`) in the background:

| Step | Tool |
|---|---|
| Transcribe | faster-whisper (`small` by default) |
| Read slides | python-pptx, PyMuPDF |
| Read diagrams | `qwen3-vl:4b` in Ollama |
| Write the minutes | `qwen2.5:3b` in Ollama |

Results are saved in the database, and the results page reads them from there. For working on the page without the pipeline, it can also read JSON result files from `backend/storage/meetings/<meeting_id>/` (details and the table list in [backend/README.md](backend/README.md)).

## Status

- **Done:** meeting upload, status tracking, results page (minutes and conflicts), retry for failed analyses, sharing the results (print/PDF, email through your own email app, copy as text), meetings search with status filters, dark mode, Android/iOS app projects.
- **Analysis pipeline:** merged from `feature/phase-2-llms`. The results page reads its database results, shows which decisions are only suggested, and shows the current step or why an analysis failed.
- **Not yet built:** speaker identification, conflict detection in the pipeline (the output format and the database tables exist), push notifications in the mobile app (needs a Firebase project), and running the native apps on a device.

## Keeping secrets and data out of Git

Don't commit `.venv/`, `node_modules/`, `.env`, the SQLite database, uploaded meeting media or `backend/storage/meetings/`. These are already in `.gitignore`.
