import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { homeFor, useAuth } from "../auth/context";
import { getSupabase } from "../services/supabase";

export default function Navbar() {
  const { profile, session } = useAuth();
  const navigate = useNavigate();
  const [signingOut, setSigningOut] = useState(false);
  const [error, setError] = useState("");

  async function signOut() {
    setSigningOut(true);
    setError("");
    try {
      const { error } = await getSupabase().auth.signOut({ scope: "local" });
      if (error) throw error;
      navigate("/login", { replace: true });
    } catch (error) {
      setError(error.message);
    } finally {
      setSigningOut(false);
    }
  }

  return (
    <nav className="navbar">
      <h2>Intelligent IT Help Desk</h2>
      <div className="nav-links">
        {profile && (
          <NavLink to={homeFor(profile.role)}>
            {profile.role === "technician" ? "Technician Dashboard" : "Employee Portal"}
          </NavLink>
        )}
        {session && (
          <>
            <span>{profile?.full_name || session.user.email}</span>
            <button onClick={signOut} disabled={signingOut}>{signingOut ? "Signing out…" : "Sign out"}</button>
          </>
        )}
      </div>
      {error && <p className="nav-error" role="alert">{error}</p>}
    </nav>
  );
}
