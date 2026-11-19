import { KIND_LABELS, sortConflicts } from "./conflicts.js";
import { formatDate } from "./files.js";
import { formatDay, formatDuration } from "./time.js";

/**
 * The minutes and conflicts as plain text, for email and for pasting into chat apps.
 * Mirrors what the results page shows, in the same order.
 */
export function minutesText(meeting, analysis) {
  const people = Object.fromEntries(analysis.participants.map((p) => [p.id, p.name]));
  const slides = Object.fromEntries(analysis.slides.map((s) => [s.id, s]));
  const missing = new Set(analysis.missing ?? []);
  const lines = [];
  const add = (...l) => lines.push(...l);

  add(`Minutes: ${meeting.title}`);
  const meta = [
    `Date: ${analysis.date || formatDate(meeting.created_at)}`,
    analysis.duration_seconds ? `Duration: ${formatDuration(analysis.duration_seconds)}` : null,
  ].filter(Boolean);
  add(meta.join(" · "));
  if (analysis.participants.length) add(`Attendees: ${analysis.participants.map((p) => p.name).join(", ")}`);

  if (missing.has("minutes")) {
    add("", "Minutes weren't generated for this meeting.");
  } else {
    const { summary } = analysis;
    if (summary.overview || summary.key_points.length) {
      add("", "SUMMARY");
      if (summary.overview) add(summary.overview);
      summary.key_points.forEach((p) => add(`- ${p}`));
    }

    add("", "DECISIONS");
    if (analysis.decisions.length === 0) add("None recorded.");
    analysis.decisions.forEach((d, i) => {
      const by = d.decided_by.map((id) => people[id]).filter(Boolean);
      add(`${i + 1}. ${d.text}${by.length ? ` (agreed by ${by.join(", ")})` : ""}`);
    });

    add("", "ACTION ITEMS");
    if (analysis.action_items.length === 0) add("None recorded.");
    analysis.action_items.forEach((a) => {
      const owner = (a.owner_id && people[a.owner_id]) || "Unassigned";
      const due = a.due_date ? formatDay(a.due_date) : a.due_text || "no date";
      add(`- ${a.task} | Owner: ${owner} | Due: ${due}`);
    });

    if (analysis.pending_items.length) {
      add("", "STILL PENDING");
      analysis.pending_items.forEach((p) => add(`- ${p}`));
    }
    if (analysis.next_meeting) add("", `NEXT MEETING: ${analysis.next_meeting}`);
  }

  add("", "CONFLICTS");
  const conflicts = sortConflicts(analysis.conflicts);
  if (conflicts.length === 0) {
    add(missing.has("conflicts")
      ? "Conflict detection hasn't run for this meeting."
      : "No disagreements, and nothing said contradicts the slides.");
  } else {
    const open = conflicts.filter((c) => c.status === "unresolved").length;
    add(`${conflicts.length} found, ${open} unresolved.`);
    conflicts.forEach((c, i) => {
      const status = c.status === "resolved" ? "Resolved" : "Unresolved";
      const impact = `${c.severity[0].toUpperCase()}${c.severity.slice(1)} impact`;
      add("", `${i + 1}. ${c.title}`, `   ${status} · ${impact} · ${KIND_LABELS[c.kind] ?? c.kind}`);
      if (c.description) add(`   ${c.description}`);
      c.positions.forEach((p) => add(`   - ${positionLabel(p, people, slides)}: "${p.statement}"`));
      add(c.resolution ? `   Outcome: ${c.resolution}` : "   Still open: needs a follow-up.");
    });
  }

  add("", "Sent from MeetingIQ");
  return lines.join("\n");
}

function positionLabel(p, people, slides) {
  if (p.speaker_id) return people[p.speaker_id] ?? "Speaker not identified";
  const slideRef = p.evidence.find((r) => r.type === "slide");
  const slide = slideRef && slides[slideRef.id];
  return slide ? `Slide ${slide.number}` : "Speaker not identified";
}

export function minutesSubject(meeting, analysis) {
  return `Minutes: ${meeting.title} (${analysis.date || formatDate(meeting.created_at)})`;
}
