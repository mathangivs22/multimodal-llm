import { useEffect, useState } from "react";
import { errorMessage, getResults, startAnalysis } from "../services/api.js";

const POLL_MS = 5000;

const STAGE_LABELS = {
  starting: "Starting",
  transcribing: "Transcribing audio and video",
  "reading slides": "Reading slides",
  "reading slide diagrams": "Reading slide diagrams",
  "writing minutes": "Writing minutes",
  done: "Done",
};

function clock(seconds) {
  if (seconds == null) return "";
  const total = Math.floor(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const pad = (n) => String(n).padStart(2, "0");
  return h ? `${h}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
}

export default function AnalysisPanel({ meetingId, initialStatus, onStatusChange }) {
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [starting, setStarting] = useState(false);

  const status = results?.status ?? initialStatus;
  const job = results?.latest_job;

  // Load existing results once when the page opens
  useEffect(() => {
    let cancelled = false;
    getResults(meetingId)
      .then((d) => !cancelled && setResults(d))
      .catch((e) => !cancelled && setError(errorMessage(e)));
    return () => {
      cancelled = true;
    };
  }, [meetingId]);

  // While a run is in progress, refresh the results every few seconds
  useEffect(() => {
    if (status !== "processing") return undefined;
    const timer = setInterval(async () => {
      try {
        const d = await getResults(meetingId);
        setResults(d);
        if (d.status !== "processing") onStatusChange?.(d.status);
      } catch (e) {
        setError(errorMessage(e));
      }
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [status, meetingId, onStatusChange]);

  async function handleStart() {
    setStarting(true);
    setError(null);
    try {
      await startAnalysis(meetingId);
      setResults(await getResults(meetingId));
      onStatusChange?.("processing");
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setStarting(false);
    }
  }

  const isProcessing = status === "processing";
  const hasResults =
    results &&
    (results.minutes || results.slides.length || results.transcript.length || results.decisions.length);

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Analysis</h2>
        <button
          type="button"
          className="btn-primary"
          onClick={handleStart}
          disabled={starting || isProcessing}
        >
          {isProcessing ? "Analyzing…" : hasResults ? "Analyze again" : "Analyze"}
        </button>
      </div>

      {isProcessing && (
        <div className="notice" role="status">
          <p>
            {STAGE_LABELS[job?.stage] ?? "Working"}. This can take several minutes; the page
            updates automatically.
          </p>
        </div>
      )}

      {error && (
        <div className="notice notice-error" role="alert">
          <p>{error}</p>
        </div>
      )}

      {!isProcessing && job?.status === "failed" && (
        <div className="notice notice-error" role="alert">
          <p>The last analysis failed.{job.error_message ? ` ${job.error_message}` : ""}</p>
        </div>
      )}

      {!hasResults && !isProcessing && !error && (
        <p className="muted">
          No analysis yet. Click Analyze to transcribe the recordings, read the slides and write
          the minutes.
        </p>
      )}

      {hasResults && <Results results={results} />}
    </section>
  );
}

function Results({ results }) {
  const { minutes, decisions, action_items: actions, slides, transcript } = results;
  return (
    <div className="analysis-results">
      {minutes && (
        <div className="result-block">
          <h3>Summary</h3>
          {minutes.overview?.title && <p className="lede">{minutes.overview.title}</p>}
          {minutes.discussion_summary?.length > 0 && (
            <ul className="plain-list">
              {minutes.discussion_summary.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          )}
          {minutes.pending_items?.length > 0 && (
            <>
              <h4>Still open</h4>
              <ul className="plain-list">
                {minutes.pending_items.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </>
          )}
          {minutes.next_meeting && <p className="muted">Next meeting: {minutes.next_meeting}</p>}
        </div>
      )}

      <div className="result-block">
        <h3>Decisions</h3>
        {decisions.length === 0 ? (
          <p className="muted">No decisions found.</p>
        ) : (
          <ul className="plain-list">
            {decisions.map((d) => (
              <li key={d.id} className="decision-row">
                <span className={`badge badge-${d.kind}`}>{d.kind}</span>
                <span>{d.text}</span>
                {d.source_seq != null && <span className="muted"> · transcript line {d.source_seq}</span>}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="result-block">
        <h3>Action items</h3>
        {actions.length === 0 ? (
          <p className="muted">No action items found.</p>
        ) : (
          <table className="file-table">
            <thead>
              <tr>
                <th scope="col">Task</th>
                <th scope="col">Owner</th>
                <th scope="col">Deadline</th>
              </tr>
            </thead>
            <tbody>
              {actions.map((a) => (
                <tr key={a.id}>
                  <td>{a.task}</td>
                  <td>{a.owner || "—"}</td>
                  <td>{a.deadline_text || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {slides.length > 0 && (
        <div className="result-block">
          <h3>Slides</h3>
          <div className="slide-grid">
            {slides.map((s) => (
              <article key={s.id} className="slide-card">
                {s.image_url && <img src={s.image_url} alt={`Slide ${s.slide_number}`} loading="lazy" />}
                <h4>
                  {s.slide_number}. {s.title || "Untitled slide"}
                </h4>
                {s.body_text && <p className="slide-body">{s.body_text}</p>}
                {s.speaker_notes && (
                  <details>
                    <summary>Speaker notes</summary>
                    <p className="slide-body">{s.speaker_notes}</p>
                  </details>
                )}
                {s.visual && (
                  <details>
                    <summary>
                      Diagram: {s.visual.components?.length ?? 0} components,{" "}
                      {s.visual.relationships?.length ?? 0} connections
                    </summary>
                    {s.visual.components?.length > 0 && (
                      <p className="chips">
                        {s.visual.components.map((c, i) => (
                          <span key={i} className="chip">
                            {c.name}
                          </span>
                        ))}
                      </p>
                    )}
                    {s.visual.relationships?.length > 0 && (
                      <ul className="plain-list">
                        {s.visual.relationships.map((r, i) => (
                          <li key={i}>
                            {r.source} → {r.target}
                            {r.description ? `: ${r.description}` : ""}
                          </li>
                        ))}
                      </ul>
                    )}
                  </details>
                )}
              </article>
            ))}
          </div>
        </div>
      )}

      {transcript.length > 0 && (
        <details className="result-block">
          <summary>
            <h3 className="inline">Transcript ({transcript.length} lines)</h3>
          </summary>
          <ol className="transcript">
            {transcript.map((t) => (
              <li key={t.seq} value={t.seq}>
                <span className="seg-time">{clock(t.start_sec)}</span> {t.text}
              </li>
            ))}
          </ol>
        </details>
      )}
    </div>
  );
}
