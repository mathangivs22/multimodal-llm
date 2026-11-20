export const KIND_LABELS = {
  speaker_disagreement: "Speakers disagree",
  speech_vs_slide: "Said vs. shown",
};

const SEVERITY_RANK = { high: 0, medium: 1, low: 2 };

/** Unresolved first, then by severity. */
export function sortConflicts(conflicts) {
  return [...conflicts].sort(
    (a, b) =>
      (a.status === "resolved") - (b.status === "resolved") ||
      SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity],
  );
}
