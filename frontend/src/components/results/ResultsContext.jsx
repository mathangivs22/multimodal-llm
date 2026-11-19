import { createContext, useCallback, useContext, useMemo } from "react";

const ResultsContext = createContext(null);

/** DOM ids for everything evidence can point at. */
export const domId = {
  transcript: (id) => `segment-${id}`,
  slide: (id) => `slide-${id}`,
  conflict: (id) => `conflict-${id}`,
};

function byId(list) {
  return Object.fromEntries(list.map((item) => [item.id, item]));
}

/**
 * Lookups shared by every results section, plus goTo(), which scrolls to a transcript
 * line, slide or conflict and briefly highlights it.
 * beforeJump runs first so the page can clear transcript filters that would hide the target.
 */
export function ResultsProvider({ analysis, beforeJump, children }) {
  const value = useMemo(() => {
    const people = byId(analysis.participants);
    const colorIndex = Object.fromEntries(analysis.participants.map((p, i) => [p.id, i % 6]));
    const segments = byId(analysis.transcript);
    const slides = byId(analysis.slides);

    // transcript segment id / slide id -> conflicts that cite it
    const conflictsByRef = {};
    for (const c of analysis.conflicts) {
      for (const p of c.positions) {
        for (const ref of p.evidence) {
          const list = (conflictsByRef[`${ref.type}:${ref.id}`] ??= []);
          if (!list.includes(c)) list.push(c);
        }
      }
    }
    const segmentsBySlide = {};
    for (const s of analysis.transcript) {
      if (s.slide_id) (segmentsBySlide[s.slide_id] ??= []).push(s);
    }
    const missing = new Set(analysis.missing ?? []);
    return { analysis, people, colorIndex, segments, slides, conflictsByRef, segmentsBySlide, missing };
  }, [analysis]);

  const goTo = useCallback(
    (type, id) => {
      beforeJump?.();
      // Wait a frame so a filtered-out transcript line is rendered again before scrolling
      requestAnimationFrame(() => {
        const el = document.getElementById(domId[type](id));
        if (!el) return;
        const smooth = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        el.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "center" });
        el.classList.remove("flash");
        void el.offsetWidth; // restart the animation if it is already running
        el.classList.add("flash");
        el.focus({ preventScroll: true });
      });
    },
    [beforeJump],
  );

  return <ResultsContext.Provider value={{ ...value, goTo }}>{children}</ResultsContext.Provider>;
}

export function useResults() {
  const ctx = useContext(ResultsContext);
  if (!ctx) throw new Error("useResults must be used inside <ResultsProvider>");
  return ctx;
}
