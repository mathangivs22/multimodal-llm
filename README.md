# MeetingIQ (Multimodal LLM)

MeetingIQ is a full-stack project for organizing meeting information and uploaded media. The Phase 1 backend is designed to store meeting metadata and associated audio, video, or presentation files, while preparing the data for future transcription, slide analysis, decision extraction, and evidence linking.

## Current project layout

```text
multimodal-llm/
|-- backend/
|   |-- app/
|   |   |-- routers/       # API routes, including meeting and file endpoints
|   |   |-- services/      # Storage and file-handling services
|   |   |-- config.py      # Environment and storage configuration
|   |   |-- database.py    # SQLAlchemy setup
|   |   |-- models.py      # Meeting and MeetingFile models
|   |   |-- schemas.py     # API request and response schemas
|   |   `-- main.py        # FastAPI application entry point
|   |-- storage/
|   |   `-- meetings/      # Uploaded meeting files, organized by meeting ID
|   |-- .env               # Local database configuration (not committed)
|   |-- .env.example       # Environment variable template
|   `-- .venv/             # Optional local Python virtual environment
|-- frontend/
|   `-- node_modules/      # Local installed frontend dependencies
`-- README.md
```

> **Repository status:** At present, the source tree contains backend metadata/cache and local dependency directories, but the tracked project currently has no committed backend or frontend application source files. The structure and API details below describe the intended Phase 1 implementation and should be updated when the source files are restored or committed.

## Technology stack

- **Backend:** Python, FastAPI, SQLAlchemy
- **Database:** MySQL by default through `DATABASE_URL`; SQLite is supported as a fallback
- **File storage:** Local filesystem under `backend/storage/meetings/`
- **Frontend:** Intended React application with Vite
- **Development platforms:** Windows PowerShell and standard Python/Node tooling

## Backend overview

The backend exposes a FastAPI application named **MeetingIQ API**. Startup creates the storage directory and initializes the database.

### API routes

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/health` | Basic API health check |
| `/api/meetings` | Meeting collection routes | Create, list, and manage meetings |
| `GET` | `/api/meetings/{meeting_id}` | Retrieve meeting details |
| `/api/meetings/{meeting_id}/files` | Meeting file routes | Upload or list meeting files |

The API includes interactive documentation when the FastAPI server is running:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Database configuration

Copy the environment template and configure the MySQL connection:

```powershell
cd backend
Copy-Item .env.example .env
```

Example format:

```dotenv
DATABASE_URL=mysql+pymysql://USER:PASSWORD@localhost:3306/multimodal_llm?charset=utf8mb4
```

URL-encode database passwords containing reserved characters such as `@`, `:`, `/`, `#`, or `%`. If `DATABASE_URL` is not set, the backend configuration can fall back to SQLite.

The local `.env` file contains credentials and must not be committed.

### Supported meeting files

The storage service is prepared for meeting assets in these categories:

- Audio recordings
- Video recordings
- Presentations

Presentation files include `.pptx` and `.pdf` formats. Upload limits and allowed extensions are controlled by the backend configuration.

Uploaded files are stored in a meeting-specific directory:

```text
backend/storage/meetings/{meeting_id}/{file_id}.{extension}
```

## Backend setup

Run the following commands from the repository root:

```powershell
cd backend

# Create and activate a virtual environment
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install the backend dependencies once their package manifest is restored
python -m pip install --upgrade pip
python -m pip install fastapi uvicorn sqlalchemy pymysql python-dotenv python-multipart

# Start the API
uvicorn app.main:app --reload
```

Verify the server:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/health"
```

The health endpoint should return:

```json
{"status":"ok"}
```

## Frontend setup

The frontend directory currently contains only local `node_modules` dependencies. Once the React/Vite source and package manifest are present, setup will normally use:

```powershell
cd frontend
npm install
npm run dev
```

The default Vite development origin is `http://localhost:5173`, which is also included in the intended CORS configuration.

## Recommended project structure

As source files are restored, keep generated and secret data out of Git:

- Commit application code, tests, and dependency manifests.
- Do not commit `.venv/`, `node_modules/`, `.env`, databases, or uploaded meeting media.
- Keep API routers in `backend/app/routers/`.
- Keep reusable I/O and storage logic in `backend/app/services/`.
- Keep SQLAlchemy models and Pydantic schemas separate for clear API boundaries.
- Add frontend components and API calls under `frontend/src/`.

## Future roadmap

- Restore and version the backend source and frontend application
- Add dependency manifests and reproducible setup instructions
- Add automated backend and frontend tests
- Integrate speech-to-text transcription
- Parse presentation slides and extract key content
- Summarize meetings and identify decisions and action items
- Link summary claims and decisions to audio and slide evidence