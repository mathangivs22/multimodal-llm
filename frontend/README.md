# MeetingIQ frontend

React + Vite. Talks to the FastAPI backend through a dev-server proxy (`/api` → `http://127.0.0.1:8000`).

## Run (Windows PowerShell)

Start the backend first (see `../backend/README.md`), then in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Pages

| Route | Page |
|---|---|
| `/` | Meetings list with each meeting's status |
| `/meetings/new` | Upload page: title, description, recording, slides |
| `/meetings/:id` | Meeting details, uploaded files and analysis status (View results / Retry analysis) |
| `/meetings/:id/results` | Results: minutes of the meeting, then conflicts. Only for completed meetings |
| `/settings` | Server address (mobile app only) |

While a meeting is being analyzed, the meeting and results pages re-check its status every 5 seconds.

## Structure

```
src/
  components/
    Layout, SourcePicker (file drop zone), StatusBadge
    AnalysisStatePanel   message for meetings that aren't analyzed yet
    RetryAnalysisButton  re-runs a failed analysis
    results/             MinutesSection, ConflictsSection, Evidence (source labels), ResultsContext
  pages/        MeetingsPage, UploadMeetingPage, MeetingDetailPage, MeetingResultsPage,
                SettingsPage, NotFoundPage
  services/     api.js (all backend calls), server.js (server address), native.js (app-only behaviour)
  utils/        files.js (upload rules matching the backend), time.js, analysisState.js, usePolling.js
  styles.css    design tokens and all styles, including the print layout
```

To build against a backend on another address (for example a hosted API), set `VITE_API_URL` when building: `VITE_API_URL=https://api.example.com npm run build`.

## Mobile app

The same app also builds as an Android and iOS app with Capacitor. See [MOBILE.md](MOBILE.md).
