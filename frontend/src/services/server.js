import { Capacitor } from "@capacitor/core";
import { Preferences } from "@capacitor/preferences";

/**
 * Where the MeetingIQ backend lives.
 *
 * Website: "" (same origin; in development Vite forwards /api to FastAPI), unless the build
 * sets VITE_API_URL. Mobile app: the address the user enters in Settings, e.g.
 * "http://192.168.1.20:8000" for a laptop on the same Wi-Fi, or "https://meetingiq.example.com".
 */
const KEY = "serverUrl";
export const isNativeApp = Capacitor.isNativePlatform();

let current = import.meta.env.VITE_API_URL ?? "";

/** "192.168.1.20:8000/" -> "http://192.168.1.20:8000". Returns null if it isn't a usable address. */
export function normalizeServerUrl(input) {
  let value = (input ?? "").trim();
  if (!value) return null;
  if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(value)) value = `http://${value}`;
  let url;
  try {
    url = new URL(value);
  } catch {
    return null;
  }
  if (!/^https?:$/.test(url.protocol) || !url.hostname) return null;
  const path = url.pathname.replace(/\/+$/, "").replace(/\/api$/, "");
  return `${url.protocol}//${url.host}${path}`;
}

export function getServerUrl() {
  return current;
}

/** The app needs an address before it can do anything; the website never does. */
export function needsServerUrl() {
  return isNativeApp && !current;
}

/** Read the saved address once, before the app renders. */
export async function loadServerUrl() {
  if (!isNativeApp) return current;
  const { value } = await Preferences.get({ key: KEY });
  current = value ?? current;
  return current;
}

export async function saveServerUrl(url) {
  current = url;
  await Preferences.set({ key: KEY, value: url });
}
