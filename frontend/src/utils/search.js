/**
 * Meeting search: case-insensitive, accent-insensitive, partial words.
 * Every word in the query must appear somewhere in the title or description.
 */

/** Lowercase and strip accents, keeping one character per character ("Café" -> "cafe"). */
export function fold(text) {
  return (text ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

/** "  Sprint   14 " -> ["sprint", "14"] */
export function searchTerms(query) {
  return fold(query).split(/\s+/).filter(Boolean);
}

export function meetingMatches(meeting, terms) {
  if (terms.length === 0) return true;
  const haystack = fold(`${meeting.title} ${meeting.description ?? ""}`);
  return terms.every((t) => haystack.includes(t));
}

/** [start, end) ranges in `text` where any term matches, merged and sorted. */
export function matchRanges(text, terms) {
  const folded = fold(text);
  // fold() can change length for some characters; only highlight when it doesn't
  if (!terms.length || folded.length !== text.length) return [];
  const ranges = [];
  for (const term of terms) {
    for (let at = folded.indexOf(term); at !== -1; at = folded.indexOf(term, at + term.length)) {
      ranges.push([at, at + term.length]);
    }
  }
  ranges.sort((a, b) => a[0] - b[0]);
  const merged = [];
  for (const r of ranges) {
    const last = merged[merged.length - 1];
    if (last && r[0] <= last[1]) last[1] = Math.max(last[1], r[1]);
    else merged.push([...r]);
  }
  return merged;
}
