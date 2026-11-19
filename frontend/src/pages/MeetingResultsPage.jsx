import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ConflictsSection from "../components/results/ConflictsSection.jsx";
import MinutesSection from "../components/results/MinutesSection.jsx";
import { ResultsProvider } from "../components/results/ResultsContext.jsx";
import SlidesSection from "../components/results/SlidesSection.jsx";
import TranscriptSection from "../components/results/TranscriptSection.jsx";
import AnalysisStatePanel from "../components/AnalysisStatePanel.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { errorMessage, getMeeting, getMeetingAnalysis } from "../services/api.js";
import { POLL_MS, isAnalyzed } from "../utils/analysisState.js";
import { usePolling } from "../utils/usePolling.js";
import { formatDate } from "../utils/files.js";
import { formatDuration } from "../utils/time.js";

const NO_FILTERS = { query: "", speaker: "" };

// What to tell the reader about parts the analysis didn't produce (see MissingPart in the backend)
const MISSING_LABELS = {
  transcript: "a transcript",
  speakers: "who said each line",
  slides: "the slides",
  slide_timing: "when each slide was on screen",
  minutes: "minutes",
  conflicts: "conflict detection",
  evidence: "links from decisions and action items back to the transcript",
};

function listSentence(items) {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

export default function MeetingResultsPage() {
  const { meetingId } = useParams();
  const [meeting, setMeeting] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState(NO_FILTERS);

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

  // The printed minutes should always contain the full transcript
  useEffect(() => {
    const reset = () => setFilters(NO_FILTERS);
    window.addEventListener("beforeprint", reset);
    return () => window.removeEventListener("beforeprint", reset);
  }, []);

  const clearFilters = useCallback(() => setFilters(NO_FILTERS), []);

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
        <AnalysisStatePanel status={meeting.status}>
          <Link to={`/meetings/${meetingId}`} className="btn-secondary analysis-state-action">
            Back to meeting
          </Link>
        </AnalysisStatePanel>
      </div>
    );
  }

  if (!analysis) return <div className="page"><p className="muted">Loading results…</p></div>;

  const openConflicts = analysis.conflicts.filter((c) => c.status === "unresolved").length;
  const missing = (analysis.missing ?? []).filter((m) => MISSING_LABELS[m]);
  const conflictsChecked = !missing.includes("conflicts");
  const sections = [
    { id: "minutes", label: "Minutes" },
    { id: "conflicts", label: "Conflicts", count: analysis.conflicts.length, alert: openConflicts > 0 },
    { id: "transcript", label: "Transcript", count: analysis.transcript.length },
    { id: "slides", label: "Slides", count: analysis.slides.length },
  ];

  return (
    <ResultsProvider analysis={analysis} beforeJump={clearFilters}>
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

        {!analysis.is_sample && missing.length > 0 && (
          <div className="notice notice-info no-print" role="status">
            <p>
              <strong>Partial analysis.</strong> This analysis doesn't include{" "}
              {listSentence(missing.map((m) => MISSING_LABELS[m]))}.
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
          <button type="button" className="btn-secondary no-print" onClick={() => window.print()}>
            <PrintIcon />
            Print or save as PDF
          </button>
        </header>

        <Glance analysis={analysis} openConflicts={conflictsChecked ? openConflicts : null} />

        <nav className="section-nav no-print" aria-label="Results sections">
          {sections.map((s) => (
            <a key={s.id} href={`#${s.id}`} className="section-nav-link">
              {s.label}
              {s.count > 0 && <span className={`count ${s.alert ? "count-alert" : ""}`}>{s.count}</span>}
            </a>
          ))}
        </nav>

        <MinutesSection />
        <ConflictsSection />
        <TranscriptSection filters={filters} onFiltersChange={setFilters} />
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
    { value: analysis.slides.length, label: "Slides shown", href: "#slides" },
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
