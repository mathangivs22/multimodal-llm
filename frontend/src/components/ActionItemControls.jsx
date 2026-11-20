import { useState } from "react";
import { errorMessage, updateActionItem } from "../services/api.js";
import { isNativeApp } from "../services/server.js";
import { buildIcs, downloadIcs, icsFileName } from "../utils/ics.js";

/**
 * Checkbox that ticks an action item as done (PATCH /api/action-items/{id}).
 * The tick shows at once and is undone with a message if saving fails.
 */
export function ActionCheckbox({ itemId, task, status, onChange, disabled = false }) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const done = status === "done";

  async function toggle() {
    const next = done ? "open" : "done";
    setSaving(true);
    setError(null);
    onChange(next); // optimistic
    try {
      await updateActionItem(itemId, next);
    } catch (err) {
      onChange(status); // put it back
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <span className="action-check-wrap">
      <input type="checkbox" className="action-check" checked={done} onChange={toggle}
        disabled={disabled || saving}
        aria-label={done ? `Mark "${task}" as not done` : `Mark "${task}" as done`} />
      {error && <span className="action-check-error" role="alert">{error}</span>}
    </span>
  );
}

/** One action item as a calendar event, downloaded as an .ics file. Hidden in the phone app. */
export function CalendarButton({ item }) {
  if (isNativeApp) return null;
  const hasDate = Boolean(item.dueDate);
  return (
    <button type="button" className="calendar-btn" disabled={!hasDate}
      title={hasDate ? "Add to calendar (.ics file)" : "No exact date to add to a calendar"}
      aria-label={hasDate ? `Add "${item.task}" to calendar` : `"${item.task}" has no exact date`}
      onClick={() => downloadIcs(icsFileName(item.task), buildIcs([item]))}>
      <CalendarIcon />
    </button>
  );
}

export function CalendarIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 16 16" aria-hidden="true">
      <rect x="1.75" y="2.75" width="12.5" height="11.5" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <path d="M1.75 6.25h12.5M5 1.5v2.5M11 1.5v2.5M8 8.4v3.4M6.3 10.1h3.4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

/** Full link to a meeting's results, for calendar event descriptions. */
export function resultsUrl(meetingId) {
  return `${window.location.origin}/meetings/${meetingId}/results`;
}
