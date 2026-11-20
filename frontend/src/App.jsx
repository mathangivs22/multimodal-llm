import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import MeetingsPage from "./pages/MeetingsPage.jsx";
import UploadMeetingPage from "./pages/UploadMeetingPage.jsx";
import MeetingDetailPage from "./pages/MeetingDetailPage.jsx";
import MeetingResultsPage from "./pages/MeetingResultsPage.jsx";
import NotFoundPage from "./pages/NotFoundPage.jsx";
import SettingsPage from "./pages/SettingsPage.jsx";
import { needsServerUrl } from "./services/server.js";

export default function App() {
  const { pathname } = useLocation();
  // First launch of the mobile app: ask for the server address before anything else
  if (needsServerUrl() && pathname !== "/settings") return <Navigate to="/settings" replace />;

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<MeetingsPage />} />
        <Route path="meetings/new" element={<UploadMeetingPage />} />
        <Route path="meetings/:meetingId" element={<MeetingDetailPage />} />
        <Route path="meetings/:meetingId/results" element={<MeetingResultsPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
