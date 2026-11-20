import { createContext, useContext, useMemo } from "react";

const ResultsContext = createContext(null);

function byId(list) {
  return Object.fromEntries(list.map((item) => [item.id, item]));
}

/** Lookups shared by the results sections: people, transcript lines and slides by id. */
export function ResultsProvider({ analysis, onActionStatus, children }) {
  const value = useMemo(() => ({
    analysis,
    people: byId(analysis.participants),
    colorIndex: Object.fromEntries(analysis.participants.map((p, i) => [p.id, i % 6])),
    segments: byId(analysis.transcript),
    slides: byId(analysis.slides),
    missing: new Set(analysis.missing ?? []),
    // Called with (actionItemId, "open" | "done") when an action item is ticked
    onActionStatus: onActionStatus ?? (() => {}),
  }), [analysis, onActionStatus]);

  return <ResultsContext.Provider value={value}>{children}</ResultsContext.Provider>;
}

export function useResults() {
  const ctx = useContext(ResultsContext);
  if (!ctx) throw new Error("useResults must be used inside <ResultsProvider>");
  return ctx;
}
