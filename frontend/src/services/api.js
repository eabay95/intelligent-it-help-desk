import { authErrorMessage, getSupabase } from "./supabase";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export async function apiRequest(endpoint, options = {}) {
  const auth = getSupabase().auth;
  const { data: { session }, error } = await auth.getSession();
  if (error) throw new Error(authErrorMessage(error));
  if (!session) throw new Error("Sign in to continue.");

  async function request(accessToken) {
    const headers = new Headers(options.headers);
    if (options.body) headers.set("Content-Type", "application/json");
    headers.set("Authorization", `Bearer ${accessToken}`);
    const timeout = AbortSignal.timeout(10000);
    const signal = options.signal ? AbortSignal.any([options.signal, timeout]) : timeout;
    try {
      return await fetch(`${API_BASE_URL}${endpoint}`, { ...options, headers, signal });
    } catch {
      options.signal?.throwIfAborted();
      throw new Error(timeout.aborted
        ? "The Help Desk API did not respond in time. Try again."
        : "Could not reach the Help Desk API. Check that the backend is running and allows this site's origin.");
    }
  }

  let response = await request(session.access_token);
  if (response.status === 401) {
    options.signal?.throwIfAborted();
    const { data: { session: current } } = await auth.getSession();
    if (current?.user.id !== session.user.id) throw new Error("Sign in to continue.");

    const { data: { session: refreshed }, error: refreshError } =
      current.access_token === session.access_token
        ? await auth.refreshSession()
        : { data: { session: current } };
    options.signal?.throwIfAborted();
    if (refreshError?.name === "AuthRetryableFetchError") {
      throw new Error(authErrorMessage(refreshError));
    }
    if (refreshed?.user.id === session.user.id) response = await request(refreshed.access_token);
    if (response.status === 401) {
      const { data: { session: latest } } = await auth.getSession();
      if (latest?.user.id === session.user.id &&
          [current.access_token, refreshed?.access_token].includes(latest.access_token)) {
        await auth.signOut({ scope: "local" });
      }
      throw new Error("Your session expired. Sign in again.");
    }
  }

  if (!response.ok) {
    if (response.status >= 500 && response.status !== 503) {
      throw new Error("The Help Desk API encountered a server error. Try again.");
    }
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    const message = Array.isArray(detail) ? detail.map((error) => error.msg).join(" ") : detail;
    throw new Error(
      typeof message === "string" ? message : response.status === 403
        ? "You do not have permission to access this help desk resource."
        : `Request failed (${response.status}).`,
    );
  }
  return response.status === 204 ? null : response.json();
}
