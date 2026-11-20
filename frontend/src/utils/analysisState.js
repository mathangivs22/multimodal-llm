// What to tell people about a meeting's analysis, by meeting status (backend MEETING_STATUSES).
export const ANALYSIS_STATES = {
  created: {
    title: "No files yet",
    text: "Add a recording or slides to this meeting before it can be analyzed.",
  },
  uploaded: {
    title: "Not analyzed yet",
    text: "The files are uploaded. Results will be available here once the meeting has been analyzed.",
  },
  processing: {
    title: "Analyzing",
    text: "Transcribing the recording and reading the slides. This page updates by itself when the results are ready.",
  },
  failed: {
    title: "Analysis failed",
    text: "Something went wrong while analyzing this meeting, so there are no results to show. You can run the analysis again.",
  },
};

export const isAnalyzed = (meeting) => meeting?.status === "completed";

/** How often to re-check a meeting that is being analyzed. */
export const POLL_MS = 5000;

// Steps the analysis pipeline reports in analysis_jobs.stage (services/pipeline.py)
export const STAGE_LABELS = {
  starting: "Starting",
  transcribing: "Transcribing the recording",
  "reading slides": "Reading the slides",
  "reading slide diagrams": "Reading the slide diagrams",
  "writing minutes": "Writing the minutes",
  done: "Finished",
};

export function stageLabel(stage) {
  return STAGE_LABELS[stage] ?? (stage ? stage[0].toUpperCase() + stage.slice(1) : null);
}
