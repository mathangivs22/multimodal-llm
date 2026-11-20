import { useState } from "react";
import { THEMES, getTheme, setTheme } from "../utils/theme.js";

const LABELS = { system: "System", light: "Light", dark: "Dark" };

/** Cycles System -> Light -> Dark. */
export default function ThemeToggle() {
  const [theme, setThemeState] = useState(getTheme);
  const next = THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length];

  function cycle() {
    setTheme(next);
    setThemeState(next);
  }

  return (
    <button type="button" className="theme-toggle" onClick={cycle}
      aria-label={`Theme: ${LABELS[theme]}. Switch to ${LABELS[next]}.`} title={`Switch to ${LABELS[next]}`}>
      <ThemeIcon theme={theme} />
      <span className="theme-toggle-label">Theme: {LABELS[theme]}</span>
    </button>
  );
}

function ThemeIcon({ theme }) {
  if (theme === "light") {
    return (
      <svg viewBox="0 0 16 16" aria-hidden="true">
        <circle cx="8" cy="8" r="3" fill="none" stroke="currentColor" strokeWidth="1.5" />
        <path d="M8 1.5v1.5M8 13v1.5M1.5 8H3M13 8h1.5M3.4 3.4l1 1M11.6 11.6l1 1M3.4 12.6l1-1M11.6 4.4l1-1"
          stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    );
  }
  if (theme === "dark") {
    return (
      <svg viewBox="0 0 16 16" aria-hidden="true">
        <path d="M13.5 9.5A5.5 5.5 0 0 1 6.5 2.5a5.5 5.5 0 1 0 7 7z" fill="none" stroke="currentColor"
          strokeWidth="1.5" strokeLinejoin="round" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true">
      <circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M8 2a6 6 0 0 1 0 12z" fill="currentColor" />
    </svg>
  );
}
