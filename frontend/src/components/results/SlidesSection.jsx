import { formatRange, formatTimestamp } from "../../utils/time.js";
import { firstName } from "./Evidence.jsx";
import { domId, useResults } from "./ResultsContext.jsx";

export default function SlidesSection() {
  const { analysis } = useResults();
  const slides = [...analysis.slides].sort((a, b) => a.number - b.number);

  return (
    <section id="slides" className="results-section" aria-labelledby="slides-title">
      <div className="section-head">
        <h2 id="slides-title" className="section-title">Slides shown</h2>
        {slides.length > 0 && <p className="muted">{slides.length} slides</p>}
      </div>
      {slides.length === 0 ? (
        <div className="panel">
          <p className="muted">No slides were presented in this meeting.</p>
        </div>
      ) : (
        <ul className="slide-list">
          {slides.map((s) => (
            <li key={s.id}>
              <SlideCard slide={s} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function SlideCard({ slide }) {
  const { segmentsBySlide, conflictsByRef, people, goTo, missing } = useResults();
  const noTiming = missing.has("slide_timing");
  const said = segmentsBySlide[slide.id] ?? [];
  const conflicts = conflictsByRef[`slide:${slide.id}`] ?? [];

  return (
    <article id={domId.slide(slide.id)} tabIndex={-1} className="slide-card">
      <div className="slide-face">
        <p className="slide-number">Slide {slide.number}</p>
        {slide.title && <h3 className="slide-title">{slide.title}</h3>}
        {slide.text ? <p className="slide-text">{slide.text}</p> : <p className="muted">No text found on this slide.</p>}
      </div>

      <div className="slide-info">
        {slide.shown_at.length > 0 && (
          <p className="slide-shown">
            On screen {slide.shown_at.map((r) => formatRange(r.start, r.end)).join(", ")}
          </p>
        )}

        {conflicts.length > 0 && (
          <div className="segment-flags">
            {conflicts.map((c) => (
              <button key={c.id} type="button" className="chip chip-conflict"
                onClick={() => goTo("conflict", c.id)} title={c.title}>
                Contradicted: {c.title}
              </button>
            ))}
          </div>
        )}

        {slide.speaker_notes && (
          <div className="slide-block">
            <p className="slide-said-label">Presenter notes</p>
            <p className="slide-notes">{slide.speaker_notes}</p>
          </div>
        )}

        {slide.diagram && <DiagramDetails diagram={slide.diagram} />}

        {noTiming ? null : said.length === 0 ? (
          <div className="slide-block">
            <p className="slide-said-label">Said while on screen</p>
            <p className="muted">Nothing.</p>
          </div>
        ) : (
          <div className="slide-block">
            <p className="slide-said-label">Said while on screen</p>
            <ul className="slide-said">
              {said.map((seg) => (
                <li key={seg.id}>
                  <button type="button" className="said-line" onClick={() => goTo("transcript", seg.id)}>
                    <span className="said-time">{formatTimestamp(seg.start)}</span>
                    <span className="said-who">{seg.speaker_id ? firstName(people[seg.speaker_id]) : ""}</span>
                    <span className="said-text">{seg.text}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </article>
  );
}

/** Components are listed under the container they follow ("CLIENTS", "EDGE", ...), else by category. */
function groupComponents(components) {
  const hasContainers = components.some((c) => c.category === "Container");
  const groups = [];
  for (const c of components) {
    if (hasContainers && c.category === "Container") {
      groups.push({ label: c.name, items: [] });
    } else if (hasContainers) {
      if (!groups.length) groups.push({ label: "Other", items: [] });
      groups[groups.length - 1].items.push(c.name);
    } else {
      const label = c.category ?? "Components";
      let g = groups.find((x) => x.label === label);
      if (!g) groups.push((g = { label, items: [] }));
      g.items.push(c.name);
    }
  }
  return groups.filter((g) => g.items.length);
}

function DiagramDetails({ diagram }) {
  const groups = groupComponents(diagram.components);
  const steps = diagram.workflow_steps;
  return (
    <div className="slide-block diagram">
      <p className="slide-said-label">Read from the diagram</p>
      {steps.length > 0 && (
        <ol className="flow" aria-label="Flow">
          {steps.map((step, i) => (
            <li key={i}>
              {i > 0 && <span className="flow-arrow" aria-hidden="true">→</span>}
              <span className="flow-step">{step}</span>
            </li>
          ))}
        </ol>
      )}
      {groups.length > 0 && (
        <dl className="diagram-groups">
          {groups.map((g) => (
            <div key={g.label} className="diagram-group">
              <dt>{g.label}</dt>
              <dd>{g.items.join(", ")}</dd>
            </div>
          ))}
        </dl>
      )}
      {diagram.uncertain.length > 0 && (
        <div className="diagram-uncertain">
          <p className="diagram-uncertain-label">Not certain</p>
          <ul>
            {diagram.uncertain.map((u, i) => (
              <li key={i}>{u}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
