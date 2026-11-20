import { ANALYSIS_STATES, stageLabel } from "../utils/analysisState.js";

/**
 * Explains why a meeting has no results yet. Renders nothing for a completed meeting.
 * `job` is the meeting's latest analysis job: its current step while analyzing, and
 * the step and error message when it failed.
 */
export default function AnalysisStatePanel({ status, job, children }) {
  const state = ANALYSIS_STATES[status];
  if (!state) return null;
  const step = stageLabel(job?.stage);
  const failedJob = status === "failed" && job?.status === "failed" ? job : null;
  return (
    <section className={`panel analysis-state analysis-state-${status}`} aria-live="polite">
      <div className="analysis-state-head">
        {status === "processing" && <span className="spinner" aria-hidden="true" />}
        <h2>{state.title}</h2>
      </div>
      {status === "processing" && step && job?.status === "running" && (
        <p className="analysis-step">Now: {step}…</p>
      )}
      <p className="muted">{state.text}</p>
      {failedJob && (
        <div className="analysis-error">
          {step && <p><strong>Failed while:</strong> {step.toLowerCase()}</p>}
          {failedJob.error_message && (
            <details>
              <summary>Technical details</summary>
              <pre>{failedJob.error_message}</pre>
            </details>
          )}
        </div>
      )}
      {children}
    </section>
  );
}
