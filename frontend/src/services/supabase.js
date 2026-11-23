import { createClient } from "@supabase/supabase-js";

let client;

export function authErrorMessage(error) {
  switch (error.code) {
    case "invalid_credentials":
      return "Invalid login credentials. Check your email and password.";
    case "email_not_confirmed":
      return "Confirm your email before signing in.";
    case "weak_password":
      return "Supabase rejected this password. Choose a stronger password.";
    case "user_already_exists":
      return "An account already exists for this email. Sign in or reset your password.";
    case "over_email_send_rate_limit":
    case "over_request_rate_limit":
      return "Too many authentication requests. Wait a moment and try again.";
    default:
      if (error.name === "AuthRetryableFetchError" || error.name === "TimeoutError") {
        return "Could not reach Supabase Auth. Check your connection and try again.";
      }
      return "Supabase Auth could not complete the request. Try again.";
  }
}

export function getSupabase() {
  const url = import.meta.env.VITE_SUPABASE_URL;
  const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !key) throw new Error("Supabase Auth is not configured.");
  client ??= createClient(url, key, {
    global: {
      fetch(resource, options) {
        const timeout = AbortSignal.timeout(10000);
        const signal = options?.signal ? AbortSignal.any([options.signal, timeout]) : timeout;
        return fetch(resource, { ...options, signal });
      },
    },
  });
  return client;
}
