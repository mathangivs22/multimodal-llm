import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ConflictsSection from "../components/results/ConflictsSection.jsx";
import MinutesSection from "../components/results/MinutesSection.jsx";
import { ResultsProvider } from "../components/results/ResultsContext.jsx";
import ShareMinutes from "../components/results/ShareMinutes.jsx";
import SlidesSection from "../components/results/SlidesSection.jsx";
import AnalysisStatePanel from "../components/AnalysisStatePanel.jsx";
import RetryAnalysisButton from "../components/RetryAnalysisButton.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { errorMessage, getMeeting, getMeetingAnalysis } from "../services/api.js";
import { POLL_MS, isAnalyzed } from "../utils/analysisState.js";
import { usePolling } from "../utils/usePolling.js";
import { formatDate } from "../utils/files.js";
import { formatDuration } from "../utils/time.js";
import { isNativeApp } from "../services/server.js";

export default function MeetingResultsPage() {
  const { meetingId } = useParams();
  const [meeting, setMeeting] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState(null);

  // Load the meeting first; results are only requested once its analysis is completed
  useEffect(() => {
    let cancelled = false;
    setMeeting(null);
    setAnalysis(null);
    setError(null);
    getMeeting(meetingId)
      .then((m) => !cancelled && setMeeting(m))
      .catch((err) => !cancelled && setError(errorMessage(err)));
    return () => {
      cancelled = true;
    };
  }, [meetingId]);

  const analyzed = isAnalyzed(meeting);
  useEffect(() => {
    if (!analyzed) return undefined;
    let cancelled = false;
    getMeetingAnalysis(meetingId)
      .then((a) => !cancelled && setAnalysis(a))
      .catch((err) => !cancelled && setError(errorMessage(err)));
    return () => {
      cancelled = true;
    };
  }, [meetingId, analyzed]);

  usePolling(
    () => getMeeting(meetingId).then(setMeeting).catch(() => {}),
    meeting?.status === "processing",
    POLL_MS,
  );

  if (error) {
    return (
      <div className="page">
        <div className="notice notice-error" role="alert">
          <p>{error}</p>
          <Link to={`/meetings/${meetingId}`} className="btn-secondary">
            Back to meeting
          </Link>
        </div>
      </div>
    );
  }

  if (meeting && !analyzed) {
    return (
      <div className="page">
        <Link to={`/meetings/${meetingId}`} className="back-link">
          Meeting details
        </Link>
        <header className="page-head">
          <div>
            <p className="eyebrow">Meeting results</p>
            <h1>{meeting.title}</h1>
          </div>
          <StatusBadge status={meeting.status} />
        </header>
        <AnalysisStatePanel status={meeting.status} job={meeting.latest_job}>
          <div className="analysis-state-actions">
            {meeting.status === "failed" && (
              <RetryAnalysisButton meetingId={meetingId}
                onStarted={(status) => setMeeting((m) => ({ ...m, status }))} />
            )}
            <Link to={`/meetings/${meetingId}`} className="btn-secondary">
              Back to meeting
            </Link>
          </div>
        </AnalysisStatePanel>
      </div>
    );
  }

  if (!analysis) return <div className="page"><p className="muted">Loading results…</p></div>;

  const openConflicts = analysis.conflicts.filter((c) => c.status === "unresolved").length;
  const conflictsChecked = !(analysis.missing ?? []).includes("conflicts");

  return (
    <ResultsProvider analysis={analysis}>
      <div className="page results-page">
        <Link to={`/meetings/${meetingId}`} className="back-link no-print">
          Meeting details
        </Link>

        {analysis.is_sample && (
          <div className="notice notice-sample no-print" role="status">
            <p>
              <strong>Sample results.</strong> No result files were found for this meeting, so the page
              shows example data (SERVE_SAMPLE_ANALYSIS is on).
            </p>
          </div>
        )}

        <header className="page-head">
          <div>
            <p className="eyebrow">Meeting results</p>
            <h1>{meeting.title}</h1>
            <p className="results-meta">
              <span>{analysis.date || formatDate(meeting.created_at)}</span>
              <span>{formatDuration(analysis.duration_seconds)}</span>
              {analysis.participants.length > 0 && <span>{analysis.participants.length} attendees</span>}
            </p>
          </div>
          <div className="results-actions no-print">
            <ShareMinutes meeting={meeting} analysis={analysis} />
            {/* Printing isn't available inside the phone app's web view */}
            {!isNativeApp && (
              <button type="button" className="btn-secondary" onClick={() => window.print()}>
                <PrintIcon />
                Print or save as PDF
              </button>
            )}
          </div>
        </header>

        <Glance analysis={analysis} openConflicts={conflictsChecked ? openConflicts : null} />

        <MinutesSection />
        <ConflictsSection />
        <SlidesSection />
      </div>
    </ResultsProvider>
  );
}

function Glance({ analysis, openConflicts }) {
  const items = [
    { value: analysis.decisions.length, label: "Decisions", href: "#minutes" },
    { value: analysis.action_items.length, label: "Action items", href: "#minutes" },
    {
      value: openConflicts ?? "–",
      label:
        openConflicts === null
          ? "Conflicts not checked"
          : openConflicts === 1 ? "Unresolved conflict" : "Unresolved conflicts",
      href: "#conflicts",
      alert: openConflicts > 0,
    },
  ];
  return (
    <ul className="glance" aria-label="At a glance">
      {items.map((it) => (
        <li key={it.label}>
          <a href={it.href} className={`glance-item ${it.alert ? "glance-alert" : ""}`}>
            <span className="glance-value">{it.value}</span>
            <span className="glance-label">{it.label}</span>
          </a>
        </li>
      ))}
    </ul>
  );
}

function PrintIcon() {
  return (
    <svg className="btn-icon" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M4 6V1.5h8V6M4 12H2.5A1 1 0 0 1 1.5 11V7a1 1 0 0 1 1-1h11a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1H12M4 9.5h8v5H4z"
        fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
    </svg>
  );
}
