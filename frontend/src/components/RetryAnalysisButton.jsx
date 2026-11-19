import { useState } from "react";
import { errorMessage, startAnalysis } from "../services/api.js";

/**
 * Starts the analysis again for a failed meeting.
 * onStarted(status) lets the page switch to "processing" straight away; its polling does the rest.
 */
export default function RetryAnalysisButton({ meetingId, onStarted }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function retry() {
    setBusy(true);
    setError(null);
    try {
      const { status } = await startAnalysis(meetingId);
      onStarted(status);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <div className="retry">
      <button type="button" className="btn-primary" onClick={retry} disabled={busy}>
        <RetryIcon />
        {busy ? "Starting…" : "Retry analysis"}
      </button>
      {error && <p className="field-error" role="alert">{error}</p>}
    </div>
  );
}

function RetryIcon() {
  return (
    <svg className="btn-icon" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M13.5 8A5.5 5.5 0 1 1 11.9 4.1M12.5 1.5v3h-3" fill="none" stroke="currentColor"
        strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
