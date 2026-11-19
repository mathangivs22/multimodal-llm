import { useEffect, useState } from "react";
import { copyText } from "../../utils/clipboard.js";
import { isNativeApp } from "../../services/server.js";
import { minutesSubject, minutesText } from "../../utils/minutesText.js";

// Desktop email apps can cut off long mailto: links (classic Outlook at about 2,000 characters).
// Phone email apps (Gmail, Samsung Email, iOS Mail) take much longer ones.
const MAX_MAILTO_LENGTH = isNativeApp ? 60000 : 1800;

/**
 * "Email minutes" opens the person's own email app with the minutes filled in; they add
 * recipients and send. "Copy as text" is for chat apps. Nothing is sent by MeetingIQ itself.
 */
export default function ShareMinutes({ meeting, analysis }) {
  const [notice, setNotice] = useState(null);

  useEffect(() => {
    if (!notice) return undefined;
    const id = setTimeout(() => setNotice(null), 6000);
    return () => clearTimeout(id);
  }, [notice]);

  async function email() {
    const subject = minutesSubject(meeting, analysis);
    const body = minutesText(meeting, analysis);
    let href = mailto(subject, body);
    if (href.length > MAX_MAILTO_LENGTH) {
      // Too long for an email link: put the full text on the clipboard and ask to paste it
      const copied = await copyText(body);
      href = mailto(subject, copied
        ? "The full minutes are on your clipboard. Paste them here (Ctrl+V, or long-press and Paste)."
        : "The minutes were too long to add here. Use 'Copy as text' on the results page and paste them.");
      setNotice(copied
        ? "The minutes were too long for an email link, so they're copied. Paste them into the email."
        : "Couldn't copy the minutes. Use Copy as text, then paste them into the email.");
    }
    window.location.href = href;
  }

  async function copy() {
    const ok = await copyText(minutesText(meeting, analysis));
    setNotice(ok ? "Minutes copied. Paste them into an email or chat." : "Couldn't copy the minutes on this device.");
  }

  return (
    <div className="share no-print">
      <div className="share-buttons">
        <button type="button" className="btn-secondary" onClick={email}>
          <MailIcon />
          Email minutes
        </button>
        <button type="button" className="btn-secondary" onClick={copy}>
          <CopyIcon />
          Copy as text
        </button>
      </div>
      <p className="share-notice" role="status" aria-live="polite">{notice}</p>
    </div>
  );
}

function mailto(subject, body) {
  return `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

function MailIcon() {
  return (
    <svg className="btn-icon" viewBox="0 0 16 16" aria-hidden="true">
      <rect x="1.5" y="3" width="13" height="10" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <path d="M2 4l6 5 6-5" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg className="btn-icon" viewBox="0 0 16 16" aria-hidden="true">
      <rect x="5" y="5" width="9" height="9.5" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <path d="M11 5V3a1.5 1.5 0 0 0-1.5-1.5h-6A1.5 1.5 0 0 0 2 3v7.5A1.5 1.5 0 0 0 3.5 12H5" fill="none"
        stroke="currentColor" strokeWidth="1.4" />
    </svg>
  );
}
