import { useId, useRef, useState } from "react";
import { SOURCES, formatBytes, validateFile } from "../utils/files.js";

/**
 * One upload source (recording or slides). Holds a single file.
 * Click, keyboard (Enter/Space on the button) and drag-and-drop all work.
 */
export default function SourcePicker({ sourceKey, file, onChange, disabled }) {
  const source = SOURCES[sourceKey];
  const inputId = useId();
  const inputRef = useRef(null);
  const [error, setError] = useState(null);
  const [dragging, setDragging] = useState(false);

  function accept(candidate) {
    if (!candidate) return;
    const problem = validateFile(candidate, sourceKey);
    setError(problem);
    if (!problem) onChange(candidate);
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragging(false);
    if (disabled) return;
    accept(e.dataTransfer.files?.[0]);
  }

  function remove() {
    setError(null);
    onChange(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <section
      className={`source ${file ? "source-filled" : ""} ${dragging ? "source-dragging" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      aria-labelledby={`${inputId}-title`}
    >
      <header className="source-head">
        <h3 id={`${inputId}-title`}>{source.label}</h3>
        <p>{source.hint}</p>
      </header>

      {file ? (
        <div className="file-chip">
          <div className="file-chip-text">
            <span className="file-name" title={file.name}>{file.name}</span>
            <span className="file-size">{formatBytes(file.size)}</span>
          </div>
          <button type="button" className="btn-text" onClick={remove} disabled={disabled}>
            Remove
          </button>
        </div>
      ) : (
        <div className="drop">
          <p>Drop a file here, or</p>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => inputRef.current?.click()}
            disabled={disabled}
          >
            Choose file
          </button>
          <p className="drop-formats">{source.accept.split(",").join("  ")}</p>
        </div>
      )}

      <input
        ref={inputRef}
        id={inputId}
        type="file"
        accept={source.accept}
        className="visually-hidden"
        tabIndex={-1}
        onChange={(e) => accept(e.target.files?.[0])}
      />

      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
