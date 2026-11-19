import { formatTimestamp } from "../../utils/time.js";
import { useResults } from "./ResultsContext.jsx";

function initials(name) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
}

export function firstName(person) {
  return person?.name.split(/\s+/)[0] ?? "Unknown";
}

/** Coloured initials circle plus optional name. */
export function Speaker({ id, showName = true, showRole = false }) {
  const { people, colorIndex } = useResults();
  const person = id ? people[id] : null;
  const name = person?.name ?? "Unknown speaker";
  return (
    <span className="speaker">
      <span className={`avatar ${person ? `avatar-${colorIndex[id] ?? 0}` : "avatar-unknown"}`} aria-hidden="true">
        {person ? initials(person.name) : "?"}
      </span>
      {showName && (
        <span className="speaker-text">
          <span className="speaker-name">{name}</span>
          {showRole && person?.role && <span className="speaker-role">{person.role}</span>}
        </span>
      )}
    </span>
  );
}

/** One chip linking to a transcript line or slide. */
export function EvidenceChip({ refItem }) {
  const { segments, slides, people, goTo } = useResults();

  if (refItem.type === "slide") {
    const slide = slides[refItem.id];
    return (
      <button type="button" className="chip chip-slide" onClick={() => goTo("slide", refItem.id)}
        title={slide?.title ? `Go to slide ${slide.number}: ${slide.title}` : "Go to slide"}>
        <SlideIcon />
        Slide {slide?.number ?? "?"}
      </button>
    );
  }

  const seg = segments[refItem.id];
  const who = seg?.speaker_id ? firstName(people[seg.speaker_id]) : null;
  return (
    <button type="button" className="chip chip-quote" onClick={() => goTo("transcript", refItem.id)}
      title={seg ? `“${seg.text}”` : "Go to transcript"}>
      <QuoteIcon />
      <span className="chip-time">{seg ? formatTimestamp(seg.start) : "?"}</span>
      {who}
      {!who && "Transcript"}
    </button>
  );
}

/** "Source" row of chips under a claim. Renders nothing if there is no evidence. */
export function EvidenceList({ evidence, label = "Source" }) {
  if (!evidence?.length) return null;
  return (
    <div className="evidence">
      <span className="evidence-label">{label}</span>
      {evidence.map((ref) => (
        <EvidenceChip key={`${ref.type}:${ref.id}`} refItem={ref} />
      ))}
    </div>
  );
}

export function SlideIcon() {
  return (
    <svg className="chip-icon" viewBox="0 0 16 16" aria-hidden="true">
      <rect x="1.5" y="2.5" width="13" height="9" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M8 11.5v2.5M5.5 14h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function QuoteIcon() {
  return (
    <svg className="chip-icon" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M2.5 3.5h11v7h-6l-3 2.5v-2.5h-2z" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}
