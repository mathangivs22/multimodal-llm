import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ActionCheckbox, CalendarButton, CalendarIcon, resultsUrl } from "../components/ActionItemControls.jsx";
import { errorMessage, listActionItems } from "../services/api.js";
import { isNativeApp } from "../services/server.js";
import { buildIcs, downloadIcs } from "../utils/ics.js";
import { formatDay, formatTimestamp } from "../utils/time.js";

const FILTERS = [
  { key: "open", label: "Open" },
  { key: "done", label: "Done" },
  { key: "all", label: "All" },
];

/** Today as "YYYY-MM-DD" in the viewer's own time zone. */
function todayIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function addDays(iso, days) {
  const [y, m, d] = iso.split("-").map(Number);
  const t = new Date(y, m - 1, d + days);
  return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
}

/** Overdue / This week / Later / No date. Done items are never overdue. */
function groupOf(item, today) {
  if (!item.deadline_date) return "none";
  if (item.status !== "done" && item.deadline_date < today) return "overdue";
  if (item.deadline_date <= addDays(today, 7)) return "week";
  return "later";
}

const GROUPS = [
  { key: "overdue", label: "Overdue" },
  { key: "week", label: "Next 7 days" },
  { key: "later", label: "Later" },
  { key: "none", label: "No date" },
];

function toCalendarItem(item) {
  return {
    id: item.id,
    task: item.task,
    dueDate: item.deadline_date,
    owner: item.owner,
    meetingTitle: item.meeting_title,
    url: resultsUrl(item.meeting_id),
  };
}

export default function ActionItemsPage() {
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("open");
  const [owner, setOwner] = useState("");
  // Items ticked or unticked on this visit stay where they are (struck through) until the
  // filter changes, so a tick can be seen and undone instead of the row vanishing
  const [justChanged, setJustChanged] = useState(() => new Set());

  async function load() {
    setError(null);
    try {
      setItems(await listActionItems({ status: "all" }));
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  useEffect(() => {
    load();
  }, []);

  const setStatus = (id, status) => {
    setItems((list) => list.map((it) => (it.id === id ? { ...it, status } : it)));
    setJustChanged((prev) => new Set(prev).add(id));
  };
  const chooseFilter = (key) => {
    setFilter(key);
    setJustChanged(new Set());
  };

  // Owners for the filter, merged case-insensitively ("marcus" and "Marcus" are one person)
  const owners = useMemo(() => {
    const byKey = new Map();
    for (const it of items ?? []) {
      const name = (it.owner || "").trim();
      if (name && !byKey.has(name.toLowerCase())) byKey.set(name.toLowerCase(), name);
    }
    return [...byKey.entries()].sort((a, b) => a[1].localeCompare(b[1]));
  }, [items]);

  const byOwner = (items ?? []).filter((it) => !owner || (it.owner || "").trim().toLowerCase() === owner);
  const counts = {
    open: byOwner.filter((it) => it.status === "open").length,
    done: byOwner.filter((it) => it.status === "done").length,
    all: byOwner.length,
  };
  const visible = byOwner.filter((it) => filter === "all" || it.status === filter || justChanged.has(it.id));
  const today = todayIso();
  const grouped = GROUPS.map((g) => ({ ...g, items: visible.filter((it) => groupOf(it, today) === g.key) }))
    .filter((g) => g.items.length > 0);
  const dated = visible.filter((it) => it.deadline_date && it.status === "open");

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Action items</h1>
          <p className="lede">Tasks from every analyzed meeting, soonest first.</p>
        </div>
        {!isNativeApp && dated.length > 0 && (
          <button type="button" className="btn-secondary"
            onClick={() => downloadIcs("meetingiq-action-items.ics", buildIcs(dated.map(toCalendarItem)))}>
            <CalendarIcon className="btn-icon" />
            Add all to calendar ({dated.length})
          </button>
        )}
      </header>

      {error && (
        <div className="notice notice-error" role="alert">
          <p>{error}</p>
          <button type="button" className="btn-secondary" onClick={load}>Try again</button>
        </div>
      )}

      {!error && items === null && <p className="muted" aria-live="polite">Loading action items…</p>}

      {items?.length === 0 && (
        <div className="empty">
          <h2>No action items yet</h2>
          <p>Action items appear here once a meeting has been analyzed.</p>
          <Link to="/" className="btn-primary">Go to meetings</Link>
        </div>
      )}

      {items?.length > 0 && (
        <>
          <div className="ai-toolbar">
            <div className="filter-chips" role="group" aria-label="Show">
              {FILTERS.map((f) => (
                <button key={f.key} type="button" className="filter-chip" aria-pressed={filter === f.key}
                  onClick={() => chooseFilter(f.key)}>
                  {f.label} <span className="filter-count">{counts[f.key]}</span>
                </button>
              ))}
            </div>
            {owners.length > 0 && (
              <label className="ai-owner">
                Owner
                <select value={owner} onChange={(e) => { setOwner(e.target.value); setJustChanged(new Set()); }}>
                  <option value="">Everyone</option>
                  {owners.map(([key, name]) => <option key={key} value={key}>{name}</option>)}
                </select>
              </label>
            )}
          </div>

          {grouped.length === 0 ? (
            <div className="empty empty-search">
              <h2>{filter === "done" ? "Nothing ticked as done yet" : "Nothing open"}</h2>
              <p>{filter === "open" ? "Every action item is done." : "Tick an action item to mark it done."}</p>
            </div>
          ) : grouped.map((g) => (
            <section key={g.key} className={`ai-group ai-group-${g.key}`} aria-labelledby={`ai-${g.key}`}>
              <h2 id={`ai-${g.key}`}>
                {g.label} <span className={`count ${g.key === "overdue" ? "count-alert" : ""}`}>{g.items.length}</span>
              </h2>
              <ul className="ai-list">
                {g.items.map((it) => (
                  <li key={it.id} className={`ai-row ${it.status === "done" ? "ai-done" : ""}`}>
                    <ActionCheckbox itemId={it.id} task={it.task} status={it.status}
                      onChange={(s) => setStatus(it.id, s)} />
                    <div className="ai-main">
                      <p className="ai-task">{it.task}</p>
                      <p className="ai-meta">
                        <Link to={`/meetings/${it.meeting_id}/results`}>{it.meeting_title}</Link>
                        {it.source_start_sec != null && (
                          <span className="chip chip-quote ai-source">{formatTimestamp(it.source_start_sec)}</span>
                        )}
                        <span className="ai-owner-inline">{it.owner || "Unassigned"}</span>
                      </p>
                    </div>
                    <span className={`ai-owner-cell ${it.owner ? "" : "muted"}`}>{it.owner || "Unassigned"}</span>
                    <span className={`ai-due ${g.key === "overdue" ? "ai-late" : ""}`}>
                      {it.deadline_date ? formatDay(it.deadline_date) : (
                        <span className="muted">{it.deadline_text ? `“${it.deadline_text}”` : "No date"}</span>
                      )}
                    </span>
                    <CalendarButton item={toCalendarItem(it)} />
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </>
      )}
    </div>
  );
}
