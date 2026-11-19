import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="page">
      <div className="empty">
        <h2>This page doesn't exist</h2>
        <p>The link may be out of date.</p>
        <Link to="/" className="btn-primary">
          Go to meetings
        </Link>
      </div>
    </div>
  );
}
