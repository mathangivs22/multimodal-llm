import { Fragment } from "react";
import { formatTimestamp } from "../../utils/time.js";
import { SlideIcon, Speaker } from "./Evidence.jsx";
import { domId, useResults } from "./ResultsContext.jsx";

/** Wrap every case-insensitive match of `query` in <mark>. */
function highlight(text, query) {
  if (!query) return text;
  const lower = text.toLowerCase();
  const q = query.toLowerCase();
  const parts = [];
  let from = 0;
  for (let at = lower.indexOf(q); at !== -1; at = lower.indexOf(q, from)) {
    if (at > from) parts.push(text.slice(from, at));
    parts.push(<mark key={at}>{text.slice(at, at + q.length)}</mark>);
    from = at + q.length;
  }
  parts.push(text.slice(from));
  return parts;
}

/** filters = { query, speaker }; the page owns them so evidence links can clear them. */
export default function TranscriptSection({ filters, onFiltersChange }) {
  const { analysis, slides, conflictsByRef, goTo, missing } = useResults();
  const hasSpeakers = !missing.has("speakers") && analysis.participants.length > 0;
  const { transcript, participants } = analysis;
  const query = filters.query.trim();

  const visible = transcript.filter(
    (s) =>
      (!filters.speaker || s.speaker_id === filters.speaker) &&
      (!query || s.text.toLowerCase().includes(query.toLowerCase())),
  );
  const filtered = visible.length !== transcript.length;

  return (
    <section id="transcript" className="results-section" aria-labelledby="transcript-title">
      <div className="section-head">
        <h2 id="transcript-title" className="section-title">Transcript</h2>
        <p className="muted" aria-live="polite">
          {filtered ? `${visible.length} of ${transcript.length} lines` : `${transcript.length} lines`}
        </p>
      </div>

      <div className="panel transcript-panel">
        <div className="transcript-controls no-print">
          <div className="field field-inline">
            <label htmlFor="transcript-search">Search</label>
            <input id="transcript-search" type="search" placeholder="Words spoken…" value={filters.query}
              onChange={(e) => onFiltersChange({ ...filters, query: e.target.value })} />
          </div>
          {hasSpeakers && <div className="field field-inline">
            <label htmlFor="transcript-speaker">Speaker</label>
            <select id="transcript-speaker" value={filters.speaker}
              onChange={(e) => onFiltersChange({ ...filters, speaker: e.target.value })}>
              <option value="">Everyone</option>
              {participants.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>}
          {filtered && (
            <button type="button" className="btn-text btn-text-plain"
              onClick={() => onFiltersChange({ query: "", speaker: "" })}>
              Clear
            </button>
          )}
        </div>

        {!hasSpeakers && transcript.length > 0 && (
          <p className="muted transcript-note">Speakers weren't identified in this recording.</p>
        )}
        {transcript.length === 0 ? (
          <p className="muted transcript-empty">No transcript is available for this meeting.</p>
        ) : visible.length === 0 ? (
          <p className="muted transcript-empty">No lines match.</p>
        ) : (
          <ol className="transcript">
            {visible.map((seg, i) => {
              // Mark where the slide on screen changes (only when not filtering, so it reads in order)
              const prev = visible[i - 1];
              const slideChanged = !filtered && seg.slide_id && seg.slide_id !== prev?.slide_id;
              const slide = slides[seg.slide_id];
              const conflicts = conflictsByRef[`transcript:${seg.id}`] ?? [];
              return (
                <Fragment key={seg.id}>
                  {slideChanged && slide && (
                    <li className="slide-marker" aria-label={`Slide ${slide.number} shown`}>
                      <button type="button" onClick={() => goTo("slide", slide.id)}>
                        <SlideIcon />
                        Slide {slide.number}{slide.title ? `: ${slide.title}` : ""} on screen
                      </button>
                    </li>
                  )}
                  <li id={domId.transcript(seg.id)} tabIndex={-1} className="segment">
                    {/* data-start is where a media player will seek once one is added */}
                    <span className="segment-time" data-start={seg.start}>{formatTimestamp(seg.start)}</span>
                    <div className="segment-body">
                      {seg.speaker_id && <Speaker id={seg.speaker_id} />}
                      <p className="segment-text">{highlight(seg.text, query)}</p>
                      {conflicts.length > 0 && (
                        <div className="segment-flags">
                          {conflicts.map((c) => (
                            <button key={c.id} type="button" className="chip chip-conflict"
                              onClick={() => goTo("conflict", c.id)} title={c.title}>
                              Part of a conflict: {c.title}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </li>
                </Fragment>
              );
            })}
          </ol>
        )}
      </div>
    </section>
  );
}
