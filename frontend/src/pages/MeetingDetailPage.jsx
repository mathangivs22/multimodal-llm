import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import AnalysisPanel from "../components/AnalysisPanel.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { errorMessage, getMeeting } from "../services/api.js";
import { formatBytes, formatDate } from "../utils/files.js";

const TYPE_LABELS = { audio: "Audio", video: "Video", presentation: "Slides" };

export default function MeetingDetailPage() {
  const { meetingId } = useParams();
  const location = useLocation();
  const [meeting, setMeeting] = useState(null);
  const [error, setError] = useState(null);

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
        <StatusBadge status={meeting.status} />
      </header>

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

      <AnalysisPanel
        meetingId={meetingId}
        initialStatus={meeting.status}
        onStatusChange={(status) => setMeeting((m) => (m ? { ...m, status } : m))}
      />
    </div>
  );
}
