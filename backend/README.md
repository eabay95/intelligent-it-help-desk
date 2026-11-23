# FastAPI ticket API

## Configure Supabase

1. Open or create a development project in the [Supabase dashboard](https://supabase.com/dashboard). Copy its project URL and publishable key into the backend and frontend environment files.
2. In the project's **Connect** dialog, use the session pooler on IPv4-only networks or the direct connection where available. Set the resulting PostgreSQL URI as `DATABASE_URL` in the backend.
3. Enable Email sign-in and registration in Supabase Auth. Configure the confirmation setting and allow the exact frontend `/login` and `/reset-password` URLs in **URL Configuration**. The default frontend origin is `http://localhost:5173`. Configure SMTP if the project needs to send confirmation or recovery email to external accounts.
4. Review the [migration](#migrations-and-existing-tickets) before applying it. Register an employee in the UI and use the [administrator procedure](#grant-technician-access) for technician access.

## Database connection

Copy `.env.example` to `.env` and fill in the values for the same Supabase project used by the frontend.

| Variable | Purpose |
| --- | --- |
| `SUPABASE_URL` | Supabase project origin, or the local Supabase API origin |
| `SUPABASE_PUBLISHABLE_KEY` | Project publishable key. The verifier uses it with the user's bearer token. |
| `DATABASE_URL` | PostgreSQL connection string from the project's **Connect** dialog |
| `DB_POOL_MODE` | `session` for direct or session-pooler connections (default). `transaction` disables client pooling and psycopg prepared statements. |
| `FRONTEND_URL` | Comma-separated browser origins |
| `ML_SERVICE_URL` | Plumber base URL, default `http://127.0.0.1:8001` |
| `ML_TIMEOUT_SECONDS` | Classifier HTTP timeout, default 2 seconds |
| `TEAM_ROUTING_JSON` | Optional object overriding category-to-team defaults, e.g. `{"Network":"Infrastructure Support"}` |

Percent-encode special characters in the database password. Use `sslmode=require` for hosted connections, or `sslmode=verify-full` with the Supabase root certificate configured through `sslrootcert`. Use a direct or session-mode connection for migrations. In a local Supabase CLI stack, use the DB URI, API URL, and publishable key displayed by `supabase status`. A standalone local PostgreSQL instance is suitable for automated tests using the test-only Auth schema fixture.

## Migrations and existing tickets

Take a reviewed backup of an existing target, inspect its `public.tickets` table for the MVP columns, and schedule the migration before starting the updated API. The migration adopts a clean database or an existing MVP `tickets` table and expects Supabase-managed `auth.users`. It stops for existing ticket RLS policies so an administrator can review them before adoption. Resolve conflicting tables or policies in a test copy first.

```powershell
uv sync --locked
uv run --env-file .env alembic upgrade head
uv run --env-file .env alembic current
uv run uvicorn main:app --reload --env-file .env
```

The migration adds profiles and provisions them for existing Auth users and future signups. It renames the old requester column to `legacy_requester_id` without changing ticket IDs or content. A new nullable UUID links tickets to profiles. Historical rows start unassigned, even if their old requester value looks like a UUID. Technicians retain access to these records. New tickets always receive the verified employee UUID from FastAPI.

If the old MVP records are in another PostgreSQL database, take an export and restore the original schema and data into a reviewed staging copy before migration. If the target already contains tickets, reconcile primary keys and ownership in staging before importing. For each historical row whose owner you can verify, run a narrowly scoped update as an administrator. The old requester text is retained for audit.

```sql
BEGIN;
UPDATE public.tickets
SET requester_id = '<confirmed employee UUID>'::uuid
WHERE id = <reviewed ticket ID>
  AND requester_id IS NULL
  AND legacy_requester_id = '<expected historical requester>'
RETURNING id, requester_id;
-- Commit only after checking the returned row.
COMMIT;
```

If rollback is needed, use the pre-migration backup and reconcile any post-migration writes first. Ticket ownership uses a restrictive foreign key, so deleting an Auth user with tickets requires a reviewed retention or reassignment procedure.

## Grant technician access

Create or invite the user in Supabase Auth, confirm their identity and address through the trusted administrator process, and copy their UUID from **Authentication → Users**. Then, as a database administrator in the SQL editor, run the following scoped update.

```sql
UPDATE public.profiles AS p
SET role = 'technician', updated_at = now()
FROM auth.users AS u
WHERE p.id = u.id
  AND p.id = '<verified user UUID>'::uuid
  AND u.email_confirmed_at IS NOT NULL
RETURNING p.id, p.role;
```

Expect exactly one row. Demote by changing the role to `employee` with a UUID-scoped administrator update. Authorization reads the current profile from PostgreSQL for each request. Sign in again or refresh the frontend to reload navigation after a role change.

## Endpoints

| Method | Path | Access |
| --- | --- | --- |
| GET | `/health` | Public process liveness |
| GET | `/auth/me` | Verified user's profile and database role |
| POST | `/tickets` | Employees, with server-assigned requester |
| GET | `/tickets` | Employees see their own tickets. Technicians see all tickets. Optional filters are `status`, `category`, and `priority`. |
| GET | `/tickets/{id}` | Owner or technician |
| PATCH | `/tickets/{id}` | Technicians. Accepts status, category, and priority. |

Missing or rejected bearer tokens receive HTTP 401. Unauthorized actions receive HTTP 403. The API accepts `Open`, `In Progress`, and `Resolved` as statuses. Titles and descriptions are limited to 160 and 5,000 characters.

Tickets are committed before classification. A valid Plumber response sets the category, suggested team, model version, and any confidence score. Unavailable classification leaves `Unclassified` with source `fallback` and routes the ticket to General Support. A manual category override clears the prior prediction metadata and recalculates the team. A pending classification respects technician overrides.

Priority is **Critical** for Organization and Blocked, **High** for Organization or Blocked, **Low** for Individual and Routine, and **Medium** otherwise. The allowed impact values are Individual, Team, and Organization. The allowed urgency values are Routine and Blocked. Routing defaults are Network Support, Hardware Support, Application Support, and Identity & Access Support for Network, Hardware, Software, and Account Access respectively. Other and Unclassified route to General Support.

## Security model

FastAPI verifies each access token online at the configured project's Supabase Auth user endpoint. Supabase handles verification with the project's signing configuration. FastAPI uses the verified UUID and the database-backed role, ignoring user-editable metadata for permissions. An Auth provider outage returns HTTP 503. RLS allows authenticated Data API users to read their own profile and tickets, and technicians to read all tickets. Data API writes are revoked for both user roles. Technician changes go through FastAPI so routing and prediction metadata update together.

The direct SQLAlchemy connection does not attach the user's JWT to the database transaction. A Supabase owner connection can bypass RLS, so FastAPI enforces all ownership and role checks itself. Keep the database URI server-side and use a least-privilege runtime database role before hosting. Auth verification adds a network dependency to protected requests. Session logout clears the local session and revokes its refresh token. An issued access token may remain valid until expiration.

## Testing

The root `compose.yaml` can supply standalone PostgreSQL for the optional database tests. Copy the root `.env.example` to `.env`, choose a local password, and run `docker compose up -d --wait postgres` from the root.

`uv run pytest` uses mocked Auth and temporary SQLite files. Set `TEST_DATABASE_URL` to a dedicated PostgreSQL test database to run the same ticket suite there. It creates and drops unique schemas. Set `TEST_MIGRATION_DATABASE_URL` to a local disposable PostgreSQL admin database for the migration suite. The role must be able to create and drop databases, and the instance must have `anon` and `authenticated` roles:

```sql
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
```

Migration tests simulate Supabase's Auth schema in disposable databases. Set `TEST_ML_SERVICE_URL` to a running local Plumber instance with a trained model for the live classifier test. Use test-only database connections.
