/** 95 -> "1:35", 3725 -> "1:02:05" (seconds from the start of the recording). */
export function formatTimestamp(seconds) {
  const total = Math.max(0, Math.floor(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = String(total % 60).padStart(2, "0");
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${s}` : `${m}:${s}`;
}

export function formatRange(start, end) {
  return `${formatTimestamp(start)}–${formatTimestamp(end)}`;
}

/** 98 -> "1 min 38 s", 1920 -> "32 min", 5400 -> "1 h 30 min". */
export function formatDuration(seconds) {
  if (seconds < 60) return `${Math.round(seconds)} s`;
  if (seconds < 600) {
    const s = Math.round(seconds % 60);
    return s ? `${Math.floor(seconds / 60)} min ${s} s` : `${Math.floor(seconds / 60)} min`;
  }
  const mins = Math.round(seconds / 60);
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60);
  return mins % 60 ? `${h} h ${mins % 60} min` : `${h} h`;
}

/** "2026-11-23" -> "23 Nov 2026", read as a calendar date (no time-zone shift). */
export function formatDay(isoDate) {
  const [y, m, d] = isoDate.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
