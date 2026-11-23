# React help desk

The app provides employee signup, login, logout, session restoration, and password recovery through Supabase Auth. It uses the server's `/auth/me` response for navigation. Employee tickets and technician permissions are scoped by FastAPI.

## Setup and run

From `frontend/`, copy `.env.example` to `.env` if needed and fill in `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`, and `VITE_API_BASE_URL`. Vite makes these variables public in the browser bundle, so only the public project settings belong here. Configure Email Auth and the login and recovery redirects using the [Supabase setup guide](../backend/README.md#configure-supabase).

```powershell
npm ci
npm run dev
```

Vite stops if its requested port is occupied. To run alongside another app on port 5173, use `npm run dev -- --port 5174` and open `http://localhost:5174/login`. Add the exact origin `http://localhost:5174` to the comma-separated backend `FRONTEND_URL` list, restart FastAPI, and allow the corresponding `/login` and `/reset-password` redirect URLs in Supabase. The API URL defaults to `http://127.0.0.1:8000`.

Use the Employee Portal to submit and track requests. A technician signs in separately and can filter tickets, view details, and change status, category, or priority. For an expired session, the API client attempts one refresh and redirects to sign-in if the session is no longer valid. A permission error keeps the signed-in session. For account recovery, use **Forgot password?** and open the link from Supabase in your browser.

## Testing

```powershell
npm test
npm run lint
npm run build
```

The Node test runner renders React in jsdom, stubs the Supabase SDK, and exercises registration, login, logout, session restoration, route protection, recovery, and the employee-to-technician workflow. Automated frontend tests use isolated configuration.
