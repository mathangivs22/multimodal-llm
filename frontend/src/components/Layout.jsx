import { NavLink, Outlet } from "react-router-dom";
import { isNativeApp } from "../services/server.js";

function Logo() {
  return (
    <svg className="logo-mark" viewBox="0 0 32 32" aria-hidden="true">
      <circle cx="11" cy="16" r="4.5" fill="none" stroke="currentColor" strokeWidth="2" />
      <circle cx="21" cy="16" r="4.5" className="logo-dot" />
      <path d="M15.5 16h1" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}

export default function Layout() {
  return (
    <div className="app">
      <aside className="sidebar">
        <NavLink to="/" className="brand" end>
          <Logo />
          <span>MeetingIQ</span>
        </NavLink>
        <nav className="nav" aria-label="Main">
          <NavLink to="/" end className="nav-link">
            Meetings
          </NavLink>
          <NavLink to="/meetings/new" className="nav-link">
            New meeting
          </NavLink>
          {isNativeApp && (
            <NavLink to="/settings" className="nav-link">
              Settings
            </NavLink>
          )}
        </nav>
        <p className="sidebar-foot">Runs locally. Your recordings never leave this machine.</p>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
