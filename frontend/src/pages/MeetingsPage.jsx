import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Highlight from "../components/Highlight.jsx";
import StatusBadge, { STATUS_LABELS } from "../components/StatusBadge.jsx";
import { errorMessage, listMeetings } from "../services/api.js";
import { formatDate } from "../utils/files.js";
import { meetingMatches, searchTerms } from "../utils/search.js";

// Order of the status filter chips
const STATUS_ORDER = ["completed", "processing", "uploaded", "created", "failed"];
const CHIP_LABELS = { ...STATUS_LABELS, uploaded: "Ready", failed: "Failed" };

export default function MeetingsPage() {
  const [meetings, setMeetings] = useState(null);
  const [error, setError] = useState(null);
  // The search lives in the address (?q=…&status=…), so Back from a meeting keeps it
  const [params, setParams] = useSearchParams();
  const query = params.get("q") ?? "";
  const status = STATUS_ORDER.includes(params.get("status")) ? params.get("status") : "";
  const searchRef = useRef(null);

  async function load() {
    setError(null);
    try {
      setMeetings(await listMeetings());
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  useEffect(() => {
    load();
  }, []);

  // "/" jumps to the search box, unless you're already typing somewhere
  useEffect(() => {
    function onKey(e) {
      if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey) return;
      const t = e.target;
      if (t instanceof HTMLElement && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
      if (!searchRef.current) return;
      e.preventDefault();
      searchRef.current.focus();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function update(next) {
    const merged = { q: query, status, ...next };
    const p = new URLSearchParams();
    if (merged.q) p.set("q", merged.q);
    if (merged.status) p.set("status", merged.status);
    setParams(p, { replace: true }); // typing shouldn't fill the Back history
  }

  const terms = useMemo(() => searchTerms(query), [query]);
  const textMatches = useMemo(
    () => (meetings ?? []).filter((m) => meetingMatches(m, terms)),
    [meetings, terms],
  );
  const visible = status ? textMatches.filter((m) => m.status === status) : textMatches;
  // Chip counts follow the search text, so they say how many results each filter would give
  const counts = useMemo(() => {
    const c = {};
    for (const m of textMatches) c[m.status] = (c[m.status] ?? 0) + 1;
    return c;
  }, [textMatches]);
  const filtering = terms.length > 0 || status !== "";
  const chips = STATUS_ORDER.filter((s) => (meetings ?? []).some((m) => m.status === s) || s === status);

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Meetings</h1>
          <p className="lede">Every recording and deck you've added, newest first.</p>
        </div>
        <Link to="/meetings/new" className="btn-primary">
          New meeting
        </Link>
      </header>

      {error && (
        <div className="notice notice-error" role="alert">
          <p>{error}</p>
          <button type="button" className="btn-secondary" onClick={load}>
            Try again
          </button>
        </div>
      )}

      {!error && meetings === null && <p className="muted" aria-live="polite">Loading meetings…</p>}

      {meetings?.length === 0 && (
        <div className="empty">
          <h2>No meetings yet</h2>
          <p>Add a recording and the slides that went with it, and MeetingIQ will trace every decision back to the moment it was made.</p>
          <Link to="/meetings/new" className="btn-primary">
            Add your first meeting
          </Link>
        </div>
      )}

      {meetings?.length > 0 && (
        <>
          <div className="search" role="search">
            <div className="search-box">
              <SearchIcon />
              <label htmlFor="meeting-search" className="visually-hidden">Search meetings</label>
              <input id="meeting-search" ref={searchRef} type="search" placeholder="Search meetings…"
                autoComplete="off" spellCheck="false" value={query}
                onChange={(e) => update({ q: e.target.value })}
                onKeyDown={(e) => {
                  if (e.key !== "Escape") return;
                  if (query) update({ q: "" });
                  else e.currentTarget.blur();
                }} />
              {query && (
                <button type="button" className="search-clear" aria-label="Clear search"
                  onClick={() => { update({ q: "" }); searchRef.current?.focus(); }}>
                  <ClearIcon />
                </button>
              )}
              <kbd className="search-hint" aria-hidden="true">/</kbd>
            </div>

            <div className="filter-chips" role="group" aria-label="Filter by status">
              <button type="button" className="filter-chip" aria-pressed={status === ""}
                onClick={() => update({ status: "" })}>
                All <span className="filter-count">{textMatches.length}</span>
              </button>
              {chips.map((s) => (
                <button key={s} type="button" aria-pressed={status === s}
                  className={`filter-chip ${!counts[s] && status !== s ? "filter-chip-empty" : ""}`}
                  onClick={() => update({ status: status === s ? "" : s })}>
                  {CHIP_LABELS[s]} <span className="filter-count">{counts[s] ?? 0}</span>
                </button>
              ))}
            </div>

            <p className="search-count muted" aria-live="polite">
              {filtering ? `Showing ${visible.length} of ${meetings.length} meetings` : ""}
            </p>
          </div>

          {visible.length === 0 ? (
            <div className="empty empty-search">
              <h2>{query ? `No meetings match “${query.trim()}”` : "No meetings with this status"}</h2>
              <p>
                {query && status
                  ? `Nothing matches your search among ${CHIP_LABELS[status].toLowerCase()} meetings.`
                  : "Try a different word, or check the spelling."}
              </p>
              <button type="button" className="btn-secondary" onClick={() => update({ q: "", status: "" })}>
                Clear search
              </button>
            </div>
          ) : (
            <ul className="meeting-list">
              {visible.map((m) => (
                <li key={m.id}>
                  <Link to={`/meetings/${m.id}`} className="meeting-row">
                    <div className="meeting-row-main">
                      <span className="meeting-title"><Highlight text={m.title} terms={terms} /></span>
                      {m.description && (
                        <span className="meeting-desc"><Highlight text={m.description} terms={terms} /></span>
                      )}
                    </div>
                    <span className="meeting-date">{formatDate(m.created_at)}</span>
                    <StatusBadge status={m.status} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}

function SearchIcon() {
  return (
    <svg className="search-icon" viewBox="0 0 16 16" aria-hidden="true">
      <circle cx="7" cy="7" r="4.75" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M10.5 10.5L14 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function ClearIcon() {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true">
      <path d="M4.5 4.5l7 7M11.5 4.5l-7 7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}
