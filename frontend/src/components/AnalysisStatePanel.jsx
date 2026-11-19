import { ANALYSIS_STATES } from "../utils/analysisState.js";

/** Explains why a meeting has no results yet. Renders nothing for a completed meeting. */
export default function AnalysisStatePanel({ status, children }) {
  const state = ANALYSIS_STATES[status];
  if (!state) return null;
  return (
    <section className={`panel analysis-state analysis-state-${status}`} aria-live="polite">
      <div className="analysis-state-head">
        {status === "processing" && <span className="spinner" aria-hidden="true" />}
        <h2>{state.title}</h2>
      </div>
      <p className="muted">{state.text}</p>
      {children}
    </section>
  );
}
