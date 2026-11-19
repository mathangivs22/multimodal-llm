import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import MeetingsPage from "./pages/MeetingsPage.jsx";
import UploadMeetingPage from "./pages/UploadMeetingPage.jsx";
import MeetingDetailPage from "./pages/MeetingDetailPage.jsx";
import NotFoundPage from "./pages/NotFoundPage.jsx";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<MeetingsPage />} />
        <Route path="meetings/new" element={<UploadMeetingPage />} />
        <Route path="meetings/:meetingId" element={<MeetingDetailPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
