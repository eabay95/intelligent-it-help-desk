import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { homeFor, useAuth } from "../auth/context";
import { authErrorMessage, getSupabase } from "../services/supabase";

const headings = {
  login: "Sign in",
  register: "Create an employee account",
  forgot: "Request a password reset",
  reset: "Set a new password",
};

export default function AuthPage({ mode }) {
  const { session, profile, loading, error: authError, retry } = useAuth();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const register = mode === "register";
  const reset = mode === "reset";
  const forgot = mode === "forgot";
  const confirm = register || reset;

  if (profile && (mode === "login" || register)) {
    return <Navigate to={homeFor(profile.role)} replace />;
  }

  async function submit(event) {
    event.preventDefault();
    if (pending) return;
    const form = event.currentTarget;
    const values = new FormData(form);
    const fullName = values.get("full_name")?.trim();
    const email = values.get("email")?.trim();
    const password = values.get("password");
    setError("");
    setMessage("");
    if (register && !fullName) {
      setError("Enter your full name.");
      return;
    }
    if (confirm && (password.length < 8 || password !== values.get("confirm"))) {
      setError("Use at least 8 characters and confirm the same password.");
      return;
    }

    setPending(true);
    try {
      const auth = getSupabase().auth;
      let result;
      if (register) {
        result = await auth.signUp({
          email, password,
          options: { data: { full_name: fullName }, emailRedirectTo: `${window.location.origin}/login` },
        });
      } else if (forgot) {
        result = await auth.resetPasswordForEmail(email, {
          redirectTo: `${window.location.origin}/reset-password`,
        });
      } else if (reset) {
        result = await auth.updateUser({ password });
      } else {
        result = await auth.signInWithPassword({ email, password });
      }
      if (result.error) throw result.error;
      if (result.data?.session) retry();
      if (register && !result.data.session) setMessage("Check your email to confirm your account.");
      if (forgot) setMessage("If an account exists, you’ll receive a password reset link.");
      if (reset) setMessage("Password updated. Continue to the help desk.");
      form.reset();
    } catch (error) {
      setError(authErrorMessage(error));
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="page">
      <section className="panel auth-panel">
        <h1>{headings[mode]}</h1>
        {(loading || pending) && <p role="status">{pending ? "Please wait…" : "Checking your session…"}</p>}
        {(error || authError) && <p role="alert">{error || authError}</p>}
        {session && authError && <button type="button" onClick={retry} disabled={loading}>Retry profile check</button>}
        {message && <p role="status">{message}</p>}
        {reset && !loading && !session && (
          <p>Open the link from your reset email or <Link to="/forgot-password">request a new link</Link>.</p>
        )}
        {(!reset || session) && (
          <form onSubmit={submit}>
            <fieldset>
              {register && <label>Full name<input name="full_name" autoComplete="name" required maxLength={120} /></label>}
              {!reset && <label>Email<input name="email" type="email" autoComplete="email" required /></label>}
              {!forgot && (
                <label>Password
                  <input name="password" type="password" autoComplete={confirm ? "new-password" : "current-password"}
                    required minLength={confirm ? 8 : undefined} />
                </label>
              )}
              {confirm && (
                <label>Confirm password<input name="confirm" type="password" autoComplete="new-password" required /></label>
              )}
              <button type="submit" disabled={pending}>{headings[mode]}</button>
            </fieldset>
          </form>
        )}
        <div className="auth-links">
          {mode === "login" ? (
            <><Link to="/register">Register</Link><Link to="/forgot-password">Forgot password?</Link></>
          ) : <Link to="/login">{session ? "Continue to help desk" : "Back to sign in"}</Link>}
        </div>
      </section>
    </main>
  );
}
