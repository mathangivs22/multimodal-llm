import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { checkServer } from "../services/api.js";
import { getServerUrl, isNativeApp, normalizeServerUrl, saveServerUrl } from "../services/server.js";

export default function SettingsPage() {
  const navigate = useNavigate();
  const firstRun = isNativeApp && !getServerUrl();
  const [value, setValue] = useState(getServerUrl());
  const [state, setState] = useState({ kind: "idle" }); // idle | checking | saved | error

  async function submit(e) {
    e.preventDefault();
    const url = normalizeServerUrl(value);
    if (!url) {
      setState({ kind: "error", message: "Enter an address such as 192.168.1.20:8000." });
      return;
    }
    setState({ kind: "checking" });
    try {
      await checkServer(url);
    } catch (err) {
      setState({
        kind: "error",
        message: err?.response
          ? `${url} answered, but it isn't a MeetingIQ server.`
          : `Couldn't reach ${url}. Check the address, that the server is running, and that this phone is on the same network.`,
      });
      return;
    }
    await saveServerUrl(url);
    setValue(url);
    setState({ kind: "saved", url });
    if (firstRun) navigate("/", { replace: true });
  }

  if (!isNativeApp) {
    return (
      <div className="page page-narrow">
        <header className="page-head">
          <h1>Settings</h1>
        </header>
        <section className="panel">
          <h2>Server</h2>
          <p className="muted">The website uses the MeetingIQ server it's served from. Nothing to set here.</p>
        </section>
      </div>
    );
  }

  return (
    <div className="page page-narrow">
      <header className="page-head">
        <div>
          <h1>{firstRun ? "Connect to MeetingIQ" : "Settings"}</h1>
          {firstRun && (
            <p className="lede">Enter the address of the MeetingIQ server this app should use.</p>
          )}
        </div>
      </header>

      <section className="panel">
        <h2>Server</h2>
        <form onSubmit={submit} noValidate>
          <div className="field">
            <label htmlFor="server-url">Server address</label>
            <input id="server-url" type="url" inputMode="url" autoCapitalize="off" autoCorrect="off"
              spellCheck="false" placeholder="192.168.1.20:8000" value={value}
              aria-invalid={state.kind === "error"} aria-describedby="server-help"
              onChange={(e) => {
                setValue(e.target.value);
                if (state.kind !== "checking") setState({ kind: "idle" });
              }} />
            <p id="server-help" className="field-help">
              On the same Wi-Fi as the computer running MeetingIQ, use that computer's IP address and port
              8000, and start the backend with <code>--host 0.0.0.0</code>. For a hosted server, use its
              https:// address.
            </p>
            {state.kind === "error" && <p className="field-error" role="alert">{state.message}</p>}
            {state.kind === "saved" && <p className="field-ok" role="status">Connected to {state.url}.</p>}
          </div>
          <div className="form-actions">
            <button type="submit" className="btn-primary" disabled={state.kind === "checking"}>
              {state.kind === "checking" ? "Checking…" : firstRun ? "Connect" : "Save"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
