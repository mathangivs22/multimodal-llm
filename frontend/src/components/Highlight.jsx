import { matchRanges } from "../utils/search.js";

/** Renders `text` with the parts matching the search terms wrapped in <mark>. */
export default function Highlight({ text, terms }) {
  const ranges = matchRanges(text ?? "", terms);
  if (!ranges.length) return text;
  const parts = [];
  let from = 0;
  for (const [start, end] of ranges) {
    if (start > from) parts.push(text.slice(from, start));
    parts.push(<mark key={start}>{text.slice(start, end)}</mark>);
    from = end;
  }
  parts.push(text.slice(from));
  return parts;
}
