import { useEffect, useState } from "react";
import { apiRequest } from "../services/api";
import { getSupabase } from "../services/supabase";
import { AuthContext } from "./context";

export default function AuthProvider({ children }) {
  const [session, setSession] = useState(undefined);
  const [{ auth, configurationError }] = useState(() => {
    try {
      return { auth: getSupabase().auth, configurationError: "" };
    } catch (error) {
      return { auth: null, configurationError: error.message };
    }
  });
  const [result, setResult] = useState(null);
  const [revision, setRevision] = useState(0);
  const userId = session?.user.id;

  useEffect(() => {
    if (!auth) return;
    const { data: { subscription } } = auth.onAuthStateChange((_event, nextSession) => {
      if (!nextSession) setResult(null);
      setSession(nextSession);
    });
    return () => subscription.unsubscribe();
  }, [auth]);

  useEffect(() => {
    if (!userId) return;
    const controller = new AbortController();
    async function loadProfile() {
      try {
        const profile = await apiRequest("/auth/me", { signal: controller.signal });
        if (profile.id !== userId || !["employee", "technician"].includes(profile.role)) {
          throw new Error("The help desk could not verify your profile.");
        }
        if (!controller.signal.aborted) setResult({ userId, revision, profile, error: "" });
      } catch (error) {
        if (!controller.signal.aborted) setResult({ userId, revision, profile: null, error: error.message });
      }
    }
    loadProfile();
    return () => controller.abort();
  }, [userId, revision]);

  const current = session && result?.userId === userId ? result : null;
  return (
    <AuthContext.Provider value={{
      session,
      profile: current?.profile,
      error: configurationError || current?.error,
      loading: !configurationError && (session === undefined || (!!session && current?.revision !== revision)),
      retry: () => setRevision((value) => value + 1),
    }}>
      {children}
    </AuthContext.Provider>
  );
}
