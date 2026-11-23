import { Navigate } from "react-router-dom";
import { homeFor, useAuth } from "./context";

export default function ProtectedRoute({ role, children }) {
  const { loading, error, session, profile, retry } = useAuth();
  if (loading) return <main className="page"><p role="status">Checking your session…</p></main>;
  if (!session && !error) return <Navigate to="/login" replace />;
  if (error) {
    return (
      <main className="page">
        <p role="alert">{error}</p>
        {session && <button onClick={retry}>Retry profile check</button>}
      </main>
    );
  }
  if (profile.role !== role) return <Navigate to={homeFor(profile.role)} replace />;
  return <section key={profile.id}>{children}</section>;
}
