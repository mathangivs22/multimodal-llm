import { useState } from "react";
import { useNavigate } from "react-router-dom";
import SourcePicker from "../components/SourcePicker.jsx";
import { createMeeting, errorMessage, uploadMeetingFiles } from "../services/api.js";

export default function UploadMeetingPage() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [recording, setRecording] = useState(null);
  const [slides, setSlides] = useState(null);
  const [titleError, setTitleError] = useState(null);
  const [formError, setFormError] = useState(null);
  const [phase, setPhase] = useState("idle"); // idle | creating | uploading
  const [progress, setProgress] = useState(0);
  // If the meeting was created but the upload failed, retry against the same meeting
  const [meetingId, setMeetingId] = useState(null);

  const busy = phase !== "idle";
  const files = [recording, slides].filter(Boolean);

  async function handleSubmit(e) {
    e.preventDefault();
    setFormError(null);

    if (!title.trim()) {
      setTitleError("Give the meeting a title.");
      return;
    }
    if (files.length === 0) {
      setFormError("Add a recording, slides, or both before uploading.");
      return;
    }

    try {
      let id = meetingId;
      if (!id) {
        setPhase("creating");
        const meeting = await createMeeting({ title: title.trim(), description: description.trim() });
        id = meeting.id;
        setMeetingId(id);
      }
      setPhase("uploading");
      setProgress(0);
      await uploadMeetingFiles(id, files, setProgress);
      navigate(`/meetings/${id}`, { state: { justUploaded: true } });
    } catch (err) {
      setFormError(errorMessage(err));
      setPhase("idle");
    }
  }

  const buttonLabel =
    phase === "creating" ? "Creating meeting…" : phase === "uploading" ? `Uploading ${progress}%` : "Upload meeting";

  return (
    <div className="page page-narrow">
      <header className="page-head">
        <div>
          <h1>New meeting</h1>
          <p className="lede">
            Add the recording and the slides together. MeetingIQ compares what was said with what was shown.
          </p>
        </div>
      </header>

      <form onSubmit={handleSubmit} noValidate>
        <div className="field">
          <label htmlFor="title">Title</label>
          <input
            id="title"
            type="text"
            value={title}
            maxLength={200}
            placeholder="e.g. Payments service architecture review"
            disabled={busy || Boolean(meetingId)}
            aria-invalid={Boolean(titleError)}
            aria-describedby={titleError ? "title-error" : undefined}
            onChange={(e) => {
              setTitle(e.target.value);
              if (titleError) setTitleError(null);
            }}
          />
          {titleError && (
            <p id="title-error" className="field-error">
              {titleError}
            </p>
          )}
        </div>

        <div className="field">
          <label htmlFor="description">
            Description <span className="optional">optional</span>
          </label>
          <textarea
            id="description"
            rows={3}
            value={description}
            maxLength={5000}
            placeholder="Who attended, what the meeting was for"
            disabled={busy || Boolean(meetingId)}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        <div className={`sources ${recording && slides ? "sources-linked" : ""}`}>
          <SourcePicker sourceKey="recording" file={recording} onChange={setRecording} disabled={busy} />
          <div className="source-link" aria-hidden="true">
            <span />
          </div>
          <SourcePicker sourceKey="slides" file={slides} onChange={setSlides} disabled={busy} />
        </div>
        <p className="sources-note muted">
          {recording && slides
            ? "Both sources added. Findings will link transcript moments to slide numbers."
            : "Both sources give the best results. You can upload just one."}
        </p>

        {formError && (
          <div className="notice notice-error" role="alert">
            <p>{formError}</p>
          </div>
        )}

        {phase === "uploading" && (
          <div
            className="progress"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progress}
            aria-label="Upload progress"
          >
            <span style={{ width: `${progress}%` }} />
          </div>
        )}

        <div className="form-actions">
          <button type="submit" className="btn-primary" disabled={busy}>
            {meetingId && phase === "idle" ? "Retry upload" : buttonLabel}
          </button>
        </div>
      </form>
    </div>
  );
}
