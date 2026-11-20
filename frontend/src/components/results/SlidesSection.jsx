import { useResults } from "./ResultsContext.jsx";

/** The deck: each slide's picture, text, speaker notes and the diagram the vision model read. */
export default function SlidesSection() {
  const { analysis } = useResults();
  const slides = analysis.slides ?? [];
  if (slides.length === 0) return null;

  return (
    <section className="slides-section" aria-labelledby="slides-heading">
      <h2 id="slides-heading">Slides</h2>
      <div className="slide-grid">
        {slides.map((s) => (
          <article key={s.id} className="slide-card" id={`slide-${s.number}`}>
            {s.image_url && <img src={s.image_url} alt={`Slide ${s.number}`} loading="lazy" />}
            <h3>
              {s.number}. {s.title || "Untitled slide"}
            </h3>
            {s.text && <p className="slide-body">{s.text}</p>}
            {s.speaker_notes && (
              <details>
                <summary>Speaker notes</summary>
                <p className="slide-body">{s.speaker_notes}</p>
              </details>
            )}
            {s.diagram && (
              <details>
                <summary>
                  Diagram: {s.diagram.components.length} components, {s.diagram.relationships.length}{" "}
                  connections
                </summary>
                {s.diagram.components.length > 0 && (
                  <p className="chips">
                    {s.diagram.components.map((c, i) => (
                      <span key={i} className="chip">
                        {c.name}
                      </span>
                    ))}
                  </p>
                )}
                {s.diagram.relationships.length > 0 && (
                  <ul className="plain-list">
                    {s.diagram.relationships.map((r, i) => (
                      <li key={i}>
                        {r.source} → {r.target}
                        {r.description ? `: ${r.description}` : ""}
                      </li>
                    ))}
                  </ul>
                )}
                {s.diagram.uncertain.length > 0 && (
                  <p className="muted">Unclear: {s.diagram.uncertain.join("; ")}</p>
                )}
              </details>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
