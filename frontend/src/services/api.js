import axios from "axios";

// Same-origin: Vite forwards /api to FastAPI (see vite.config.js)
const api = axios.create({ baseURL: "/api", timeout: 30000 });

/** Turn any axios error into one readable sentence for the UI. */
export function errorMessage(err) {
  if (err?.response) {
    const detail = err.response.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg).join(" ");
    return `The server returned an error (${err.response.status}).`;
  }
  if (err?.code === "ECONNABORTED") return "The request timed out. Check that the backend is running.";
  return "Can't reach the MeetingIQ backend. Make sure it is running on port 8000.";
}

export async function listMeetings() {
  const { data } = await api.get("/meetings");
  return data;
}

export async function getMeeting(meetingId) {
  const { data } = await api.get(`/meetings/${meetingId}`);
  return data;
}

export async function createMeeting({ title, description }) {
  const { data } = await api.post("/meetings", {
    title,
    description: description || null,
  });
  return data;
}

/** Upload files to a meeting. onProgress receives a number from 0 to 100. */
export async function uploadMeetingFiles(meetingId, files, onProgress) {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  const { data } = await api.post(`/meetings/${meetingId}/files`, form, {
    timeout: 0, // large recordings can take a while
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100));
    },
  });
  return data;
}

/** Start analysis for a meeting. The backend runs it in the background. */
export async function startAnalysis(meetingId) {
  const { data } = await api.post(`/meetings/${meetingId}/analyze`);
  return data;
}

/** Everything the analysis produced, plus the current job status and stage. */
export async function getResults(meetingId) {
  const { data } = await api.get(`/meetings/${meetingId}/results`);
  return data;
}
