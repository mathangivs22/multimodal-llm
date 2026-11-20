import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import AnalysisStatePanel from "../components/AnalysisStatePanel.jsx";
import RetryAnalysisButton from "../components/RetryAnalysisButton.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { deleteMeeting, errorMessage, getMeeting } from "../services/api.js";
import { POLL_MS, isAnalyzed } from "../utils/analysisState.js";
import { formatBytes, formatDate } from "../utils/files.js";
import { usePolling } from "../utils/usePolling.js";

const TYPE_LABELS = { audio: "Audio", video: "Video", presentation: "Slides" };

export default function MeetingDetailPage() {
  const { meetingId } = useParams();
  const location = useLocation();
  const [meeting, setMeeting] = useState(null);
  const [error, setError] = useState(null);
  const [deleteError, setDeleteError] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const navigate = useNavigate();

  async function handleDelete() {
    const ok = window.confirm(
      `Delete "${meeting.title}"? Its files, transcript, slides and minutes will be removed. This can't be undone.`,
    );
    if (!ok) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteMeeting(meetingId);
      navigate("/", { replace: true });
    } catch (err) {
      setDeleteError(errorMessage(err));
      setDeleting(false);
    }
  }

  useEffect(() => {
    let cancelled = false;
    setMeeting(null);
    setError(null);
    getMeeting(meetingId)
      .then((data) => !cancelled && setMeeting(data))
      .catch((err) => !cancelled && setError(errorMessage(err)));
    return () => {
      cancelled = true;
    };
  }, [meetingId]);

  // Pick up the end of an analysis without a manual refresh
  usePolling(
    () => getMeeting(meetingId).then(setMeeting).catch(() => {}),
    meeting?.status === "processing",
    POLL_MS,
  );

  if (error) {
    return (
      <div className="page">
        <div className="notice notice-error" role="alert">
          <p>{error}</p>
          <Link to="/" className="btn-secondary">
            Back to meetings
          </Link>
        </div>
      </div>
    );
  }

  if (!meeting) return <div className="page"><p className="muted">Loading meeting…</p></div>;

  return (
    <div className="page">
      <Link to="/" className="back-link">
        All meetings
      </Link>

      {location.state?.justUploaded && (
        <div className="notice notice-success" role="status">
          <p>Uploaded. The files are saved and ready for analysis.</p>
        </div>
      )}

      <header className="page-head">
        <div>
          <h1>{meeting.title}</h1>
          {meeting.description && <p className="lede">{meeting.description}</p>}
        </div>
        <div className="page-head-actions">
          <StatusBadge status={meeting.status} />
          <button
            type="button"
            className="btn-text btn-danger"
            onClick={handleDelete}
            disabled={deleting || meeting.status === "processing"}
            title={meeting.status === "processing" ? "Wait for the analysis to finish" : undefined}
          >
            {deleting ? "Deleting…" : "Delete meeting"}
          </button>
        </div>
      </header>

      {deleteError && (
        <div className="notice notice-error" role="alert">
          <p>{deleteError}</p>
        </div>
      )}

      <section className="panel">
        <h2>Files</h2>
        {meeting.files.length === 0 ? (
          <p className="muted">No files yet.</p>
        ) : (
          <table className="file-table">
            <thead>
              <tr>
                <th scope="col">Name</th>
                <th scope="col">Type</th>
                <th scope="col">Size</th>
                <th scope="col">Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {meeting.files.map((f) => (
                <tr key={f.id}>
                  <td className="file-table-name">{f.original_filename}</td>
                  <td>{TYPE_LABELS[f.file_type] ?? f.file_type}</td>
                  <td>{formatBytes(f.size_bytes)}</td>
                  <td>{formatDate(f.uploaded_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {isAnalyzed(meeting) ? (
        <section className="panel analysis-ready">
          <div>
            <h2>Analysis</h2>
            <p className="muted">The minutes and the conflicts found in the discussion are ready.</p>
          </div>
          <div className="analysis-actions">
            <RetryAnalysisButton
              label="Analyze again"
              meetingId={meetingId}
              onStarted={(status) => setMeeting((m) => ({ ...m, status }))} />
            <Link to="results" className="btn-primary">
              View results
            </Link>
          </div>
        </section>
      ) : (
        <AnalysisStatePanel status={meeting.status} job={meeting.latest_job}>
          {(meeting.status === "failed" || meeting.status === "uploaded") && (
            <RetryAnalysisButton
              label={meeting.status === "failed" ? "Retry analysis" : "Analyze"}
              meetingId={meetingId}
              onStarted={(status) => setMeeting((m) => ({ ...m, status }))} />
          )}
        </AnalysisStatePanel>
      )}
    </div>
  );
}
