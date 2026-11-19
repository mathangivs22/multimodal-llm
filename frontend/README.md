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
| `/meetings/:id/results` | Results: minutes of the meeting, then conflicts. Only for completed meetings. Email minutes, Copy as text, Print or save as PDF |
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
  utils/        files.js (upload rules matching the backend), time.js, analysisState.js, usePolling.js,
                minutesText.js (minutes as plain text for email and copying), conflicts.js, clipboard.js, theme.js
  styles.css    design tokens and all styles, including the print layout
```

To build against a backend on another address (for example a hosted API), set `VITE_API_URL` when building: `VITE_API_URL=https://api.example.com npm run build`.

## Dark mode

The app follows the device's dark-mode setting. The **Theme** button in the sidebar (the half-filled circle in the phone top bar) switches between **System**, **Light** and **Dark**, and the choice is remembered on that device. All colours are CSS variables at the top of `styles.css`, with the dark values in the "Dark mode" block at the end; add new colours as variables so they work in both themes. Printing and Save as PDF always use the light colours.

## Emailing the minutes

**Email minutes** opens the person's own email app (Outlook, Gmail, the phone's mail app) with the subject and the minutes and conflicts as text filled in; they add recipients and send. MeetingIQ doesn't send email itself, so there's nothing to configure. Desktop email apps can cut off long email links, so on the website, minutes over about 1,800 characters are copied to the clipboard instead and the email asks the person to paste them. In the phone app the full text always goes into the email.

## Mobile app

The same app also builds as an Android and iOS app with Capacitor. See [MOBILE.md](MOBILE.md).
