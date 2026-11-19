const LABELS = {
  created: "Waiting for files",
  uploaded: "Ready to analyze",
  processing: "Analyzing",
  completed: "Analyzed",
  failed: "Analysis failed",
};

export default function StatusBadge({ status }) {
  return (
    <span className={`badge badge-${status}`}>
      <span className="badge-dot" aria-hidden="true" />
      {LABELS[status] ?? status}
    </span>
  );
}
