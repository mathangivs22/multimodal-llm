import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import StatusBadge from "../components/StatusBadge.jsx";
import { errorMessage, listMeetings } from "../services/api.js";
import { formatDate } from "../utils/files.js";

export default function MeetingsPage() {
  const [meetings, setMeetings] = useState(null);
  const [error, setError] = useState(null);

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
        <ul className="meeting-list">
          {meetings.map((m) => (
            <li key={m.id}>
              <Link to={`/meetings/${m.id}`} className="meeting-row">
                <div className="meeting-row-main">
                  <span className="meeting-title">{m.title}</span>
                  {m.description && <span className="meeting-desc">{m.description}</span>}
                </div>
                <span className="meeting-date">{formatDate(m.created_at)}</span>
                <StatusBadge status={m.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
