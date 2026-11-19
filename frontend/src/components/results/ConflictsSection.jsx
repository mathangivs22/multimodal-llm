import { domId, useResults } from "./ResultsContext.jsx";
import { EvidenceList, SlideIcon, Speaker } from "./Evidence.jsx";

const KIND_LABELS = {
  speaker_disagreement: "Speakers disagree",
  speech_vs_slide: "Said vs. shown",
};
const SEVERITY_RANK = { high: 0, medium: 1, low: 2 };

/** Unresolved first, then by severity. */
function sortConflicts(conflicts) {
  return [...conflicts].sort(
    (a, b) =>
      (a.status === "resolved") - (b.status === "resolved") ||
      SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity],
  );
}

export default function ConflictsSection() {
  const { analysis, missing } = useResults();
  const conflicts = sortConflicts(analysis.conflicts);
  const notChecked = missing.has("conflicts");
  const open = conflicts.filter((c) => c.status === "unresolved").length;

  return (
    <section id="conflicts" className="results-section" aria-labelledby="conflicts-title">
      <div className="section-head">
        <h2 id="conflicts-title" className="section-title">Conflicts</h2>
        {conflicts.length > 0 && (
          <p className="muted">
            {conflicts.length} found · {open === 0 ? "all resolved" : `${open} unresolved`}
          </p>
        )}
      </div>

      {conflicts.length === 0 ? (
        <div className="panel">
          <p className="muted">
            {notChecked
              ? "Conflict detection hasn't run for this meeting, so disagreements and contradictions with the slides aren't shown."
              : "No disagreements, and nothing said contradicts the slides."}
          </p>
        </div>
      ) : (
        <ul className="conflict-list">
          {conflicts.map((c) => (
            <li key={c.id}>
              <ConflictCard conflict={c} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ConflictCard({ conflict: c }) {
  const resolved = c.status === "resolved";
  return (
    <article id={domId.conflict(c.id)} tabIndex={-1}
      className={`conflict conflict-${c.severity} ${resolved ? "conflict-resolved" : ""}`}>
      <div className="conflict-tags">
        <span className="tag">{KIND_LABELS[c.kind] ?? c.kind}</span>
        <span className={`tag tag-severity-${c.severity}`}>
          {c.severity[0].toUpperCase() + c.severity.slice(1)} impact
        </span>
        <span className={`tag ${resolved ? "tag-resolved" : "tag-open"}`}>
          {resolved ? "Resolved" : "Unresolved"}
        </span>
      </div>
      <h3 className="conflict-title">{c.title}</h3>
      <p className="conflict-desc">{c.description}</p>

      <div className="positions">
        {c.positions.map((p, i) => (
          <Position key={i} position={p} />
        ))}
      </div>

      <p className={`conflict-outcome ${resolved ? "" : "conflict-outcome-open"}`}>
        <strong>{resolved ? "Outcome:" : "Still open:"}</strong>{" "}
        {c.resolution ?? "Not settled in the meeting. Needs a follow-up."}
      </p>
    </article>
  );
}

function Position({ position: p }) {
  const { slides } = useResults();
  // A position without a speaker comes from a slide; name the slide it cites
  const slideRef = p.evidence.find((r) => r.type === "slide");
  const slide = slideRef && slides[slideRef.id];
  return (
    <div className="position">
      <div className="position-who">
        {p.speaker_id ? (
          <Speaker id={p.speaker_id} />
        ) : (
          <span className="speaker">
            <span className="avatar avatar-slide" aria-hidden="true">
              <SlideIcon />
            </span>
            <span className="speaker-name">{slide ? `Slide ${slide.number}` : "Slides"}</span>
          </span>
        )}
      </div>
      <blockquote className="position-statement">{p.statement}</blockquote>
      <EvidenceList evidence={p.evidence} />
    </div>
  );
}
