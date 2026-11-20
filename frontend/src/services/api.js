import axios from "axios";
import { getServerUrl, isNativeApp } from "./server.js";

// The base URL is read on every request, so changing the server in Settings applies at once.
// Website: same origin, and in development Vite forwards /api to FastAPI (see vite.config.js).
const api = axios.create({ timeout: 30000 });
api.interceptors.request.use((config) => ({ ...config, baseURL: config.baseURL || `${getServerUrl()}/api` }));

/** Turn any axios error into one readable sentence for the UI. */
export function errorMessage(err) {
  if (err?.response) {
    const detail = err.response.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg).join(" ");
    return `The server returned an error (${err.response.status}).`;
  }
  if (err?.code === "ECONNABORTED") return "The request timed out. Check that the backend is running.";
  return isNativeApp
    ? "Can't reach the MeetingIQ server. Check the server address in Settings and that this phone can reach it."
    : "Can't reach the MeetingIQ backend. Make sure it is running on port 8000.";
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
    // In development, send big uploads straight to the backend: the dev proxy drops them
    baseURL: import.meta.env.DEV ? "http://127.0.0.1:8000/api" : undefined,
    timeout: 0, // large recordings can take a while
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100));
    },
  });
  return data;
}

/** Analysis result: minutes, transcript, slides and conflicts (see backend/app/analysis_schemas.py). */
export async function getMeetingAnalysis(meetingId) {
  const { data } = await api.get(`/meetings/${meetingId}/analysis`);
  return data;
}

/** Start (or retry) the analysis. The meeting moves to "processing" right away. */
export async function startAnalysis(meetingId) {
  const { data } = await api.post(`/meetings/${meetingId}/analyze`);
  return data;
}

/** Check that a server address answers as a MeetingIQ backend. Resolves true or throws. */
export async function checkServer(serverUrl) {
  const { data } = await axios.get(`${serverUrl}/api/health`, { timeout: 8000 });
  if (data?.status !== "ok") throw new Error("not-meetingiq");
  return true;
}

/** Delete a meeting with its files and results. The server refuses while it is being analyzed. */
export async function deleteMeeting(meetingId) {
  await api.delete(`/meetings/${meetingId}`);
}

/** Action items of every analyzed meeting. status: "open" | "done" | "all". */
export async function listActionItems({ status = "all" } = {}) {
  const { data } = await api.get("/action-items", { params: { status } });
  return data;
}

/** Tick an action item as done ("done") or untick it ("open"). Returns the updated item. */
export async function updateActionItem(itemId, status) {
  const { data } = await api.patch(`/action-items/${itemId}`, { status });
  return data;
}
