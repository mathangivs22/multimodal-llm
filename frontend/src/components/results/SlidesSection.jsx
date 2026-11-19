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
  const { segmentsBySlide, conflictsByRef, people, goTo } = useResults();
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
        <p className="slide-shown">
          {slide.shown_at.length > 0
            ? `On screen ${slide.shown_at.map((r) => formatRange(r.start, r.end)).join(", ")}`
            : "Time on screen unknown"}
        </p>

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

        <p className="slide-said-label">Said while on screen</p>
        {said.length === 0 ? (
          <p className="muted">Nothing.</p>
        ) : (
          <ul className="slide-said">
            {said.map((seg) => (
              <li key={seg.id}>
                <button type="button" className="said-line" onClick={() => goTo("transcript", seg.id)}>
                  <span className="said-time">{formatTimestamp(seg.start)}</span>
                  <span className="said-who">{firstName(people[seg.speaker_id])}</span>
                  <span className="said-text">{seg.text}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </article>
  );
}
