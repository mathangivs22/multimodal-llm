/**
 * Calendar files (.ics, RFC 5545) for action item deadlines.
 * Each item becomes an all-day event on its due date (no time zones involved). The UID is
 * the action item's id, so importing the file again updates the event instead of copying it.
 */

/** Escape text for an .ics property value. */
function escapeText(value) {
  return String(value ?? "")
    .replace(/\\/g, "\\\\")
    .replace(/;/g, "\\;")
    .replace(/,/g, "\\,")
    .replace(/\r?\n/g, "\\n");
}

/** Fold lines longer than 75 bytes (UTF-8), continuing with a leading space. */
function fold(line) {
  const bytes = new TextEncoder();
  if (bytes.encode(line).length <= 75) return line;
  const parts = [];
  let current = "";
  for (const ch of line) {
    const limit = parts.length === 0 ? 75 : 74; // continuation lines start with a space
    if (bytes.encode(current + ch).length > limit) {
      parts.push(current);
      current = ch;
    } else {
      current += ch;
    }
  }
  parts.push(current);
  return parts.join("\r\n ");
}

/** "2026-11-20" -> "20261120"; the day after, for the exclusive DTEND. */
function ymd(isoDate) {
  return isoDate.replaceAll("-", "");
}
function nextDay(isoDate) {
  const [y, m, d] = isoDate.split("-").map(Number);
  const next = new Date(Date.UTC(y, m - 1, d + 1));
  return next.toISOString().slice(0, 10).replaceAll("-", "");
}
function stamp(now) {
  return now.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
}

/**
 * items: [{ id, task, dueDate: "YYYY-MM-DD", owner, meetingTitle, url }]
 * Items without dueDate are skipped.
 */
export function buildIcs(items, now = new Date()) {
  const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//MeetingIQ//Action items//EN", "CALSCALE:GREGORIAN"];
  for (const item of items) {
    if (!item.dueDate) continue;
    const details = [
      item.owner ? `Owner: ${item.owner}` : "Owner: unassigned",
      item.meetingTitle ? `From the meeting: ${item.meetingTitle}` : null,
      item.url || null,
    ].filter(Boolean).join("\n");
    lines.push(
      "BEGIN:VEVENT",
      `UID:${item.id}@meetingiq`,
      `DTSTAMP:${stamp(now)}`,
      `DTSTART;VALUE=DATE:${ymd(item.dueDate)}`,
      `DTEND;VALUE=DATE:${nextDay(item.dueDate)}`,
      `SUMMARY:${escapeText(item.task)}`,
      `DESCRIPTION:${escapeText(details)}`,
      ...(item.url ? [`URL:${item.url}`] : []),
      "END:VEVENT",
    );
  }
  lines.push("END:VCALENDAR");
  return lines.map(fold).join("\r\n") + "\r\n";
}

/** Save an .ics file in the browser. */
export function downloadIcs(filename, content) {
  const url = URL.createObjectURL(new Blob([content], { type: "text/calendar;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** "Update the board" -> "update-the-board.ics" */
export function icsFileName(text) {
  const slug = String(text).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 50);
  return `${slug || "action-items"}.ics`;
}
