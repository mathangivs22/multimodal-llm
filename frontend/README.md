# MeetingIQ frontend

React + Vite. Talks to the FastAPI backend through a dev-server proxy (`/api` → `http://127.0.0.1:8000`).

## Run (Windows PowerShell)

Start the backend first (see `../backend/README.md`), then in a second terminal:

```powershell
cd meetingiq\frontend
npm install
npm run dev
```

Open http://localhost:5173

## Pages so far

| Route | Page |
|---|---|
| `/` | Meetings list (from `GET /api/meetings`) |
| `/meetings/new` | Upload page: title, description, recording, slides |
| `/meetings/:id` | Meeting details and uploaded files |

## Structure

```
src/
  components/   Layout (sidebar), SourcePicker (file drop zone), StatusBadge
  pages/        MeetingsPage, UploadMeetingPage, MeetingDetailPage, NotFoundPage
  services/     api.js (all backend calls)
  utils/        files.js (validation rules matching the backend, formatting)
  styles.css    design tokens and all styles
```

## Mobile app

The same app also builds as an Android and iOS app with Capacitor. See [MOBILE.md](MOBILE.md).
