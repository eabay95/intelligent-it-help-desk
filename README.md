# Intelligent IT Help Desk

## Overview

Employees submit IT support tickets and track their progress. Technicians review and resolve tickets with category, priority, and support-team suggestions.

## Features

- Employee registration, login, ticket submission, and status tracking
- Role-based technician dashboard for filtering, updating, and resolving tickets
- Automated R ticket classification, rule-based priority, and team recommendations
- Ticket storage in Supabase PostgreSQL and manual triage when classification is unavailable

## Tech Stack

- **Frontend** — React, JavaScript, Vite
- **Backend** — Python, FastAPI, SQLAlchemy, Alembic
- **Database and authentication** — Supabase PostgreSQL and Supabase Auth
- **Machine learning** — R, TF-IDF, and Plumber. Naive Bayes serves predictions and logistic regression is retained for evaluation.

## Project Structure

```text
intelligent-it-help-desk/
├── frontend/   React portal and frontend tests
├── backend/    FastAPI, Supabase integration, migrations, and backend tests
├── ml-r/       Classifier, Plumber, evaluation, and ML tests
├── infra/      Reserved for deployment configuration
├── docs/       Project planning and technical notes
└── tests/      Reserved for shared integration tests
```

## Getting Started

Install Node.js 22.12+ or 24, Python 3.14 (the repository pin), uv, and R 4.4+. Set up a [Supabase project and Email Auth](backend/README.md#configure-supabase), then copy `frontend/.env.example` and `backend/.env.example` to `.env` in their respective directories. Keep the database URI in the backend only.

| Directory | Commands |
| --- | --- |
| `frontend/` | Run `npm ci`. |
| `backend/` | Run `uv sync --locked`. After reviewing the [migration guide](backend/README.md#migrations-and-existing-tickets), run `uv run --env-file .env alembic upgrade head` against the intended database. |
| `ml-r/` | Install the [R dependencies](ml-r/README.md#train-and-run). If the baseline artifact is missing, run `Rscript train.R`. Start Plumber with `Rscript run.R`. |
| `backend/` | Start FastAPI with `uv run uvicorn main:app --reload --env-file .env`. |
| `frontend/` | Run `npm run dev` and open the printed URL. See the [frontend guide](frontend/README.md) for alternate ports. |

Use separate terminals for the running services. The root `compose.yaml` is optional and starts standalone PostgreSQL for local database tests.

## Testing

- `backend/` — `uv run pytest`
- `frontend/` — `npm test`, `npm run lint`, and `npm run build`
- `ml-r/` — `Rscript test.R` and, with Plumber running, `Rscript test-api.R`

## Team Responsibilities

- **Frontend** — React interface and user workflows
- **Backend** — FastAPI, Supabase, authentication, and the database
- **Machine learning** — R classifier, evaluation, and Plumber

## Project Status

The MVP supports employee submission through technician resolution. AWS deployment and improved classification of operational tickets are planned. See the [ML evaluation](ml-r/evaluation/model-decision.md) for current limitations.
