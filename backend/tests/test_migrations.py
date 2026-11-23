import os
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

import app.database
import main
from app.services import classifier

ADMIN_URL = os.getenv("TEST_MIGRATION_DATABASE_URL")
pytestmark = pytest.mark.skipif(not ADMIN_URL, reason="Requires disposable PostgreSQL with CREATEDB")


@pytest.fixture
def migration_database(monkeypatch):
    url = make_url(ADMIN_URL)
    assert url.host in {"127.0.0.1", "localhost", "::1"}, "Migration tests require a local PostgreSQL instance."
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    name = f"helpdesk_migration_{uuid4().hex}"
    with admin.connect() as db:
        db.exec_driver_sql(f'CREATE DATABASE "{name}"')
    engine = create_engine(url.set(database=name))
    try:
        with engine.begin() as db:
            db.exec_driver_sql("CREATE SCHEMA auth")
            db.exec_driver_sql("CREATE TABLE auth.users (id uuid PRIMARY KEY, raw_user_meta_data jsonb)")
            db.exec_driver_sql("""
                CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS
                $$ SELECT NULLIF(current_setting('request.jwt.claim.sub', true), '')::uuid $$
            """)
            db.exec_driver_sql("GRANT USAGE ON SCHEMA auth TO authenticated")
            db.exec_driver_sql("GRANT USAGE ON SCHEMA public TO authenticated, anon")
        monkeypatch.setattr(app.database, "engine", engine)
        monkeypatch.setenv("DATABASE_URL", "postgresql://127.0.0.1/test")
        yield engine
    finally:
        engine.dispose()
        with admin.connect() as db:
            db.exec_driver_sql(f'DROP DATABASE "{name}"')
        admin.dispose()


def apply_migration():
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    command.upgrade(config, "head")


def seed_user(db, user_id):
    db.execute(text("""
        INSERT INTO auth.users (id, raw_user_meta_data)
        VALUES (:id, '{"full_name": "Test User", "role": "technician"}'::jsonb)
    """), {"id": user_id})


def seed_ticket(db, owner):
    return db.execute(text("""
        INSERT INTO tickets (
            title, description, requester_id, category, priority, recommended_team,
            status, classification_source, created_at, updated_at
        )
        VALUES ('Existing ticket', 'Problem', :owner, 'Other', 'Medium', 'General Support',
                'Open', 'fallback', now(), now())
        RETURNING id
    """), {"owner": owner}).scalar_one()


def authenticate(db, user_id):
    db.exec_driver_sql("SET LOCAL ROLE authenticated")
    db.execute(text("SELECT set_config('request.jwt.claim.sub', :id, true)"), {"id": str(user_id)})


def test_fresh_migration_enforces_rls_and_safe_role_provisioning(migration_database):
    apply_migration()
    employee, other, tech = uuid4(), uuid4(), uuid4()
    with migration_database.begin() as db:
        for user_id in (employee, other, tech):
            seed_user(db, user_id)
        assert db.execute(text("SELECT DISTINCT role FROM profiles")).scalars().all() == ["employee"]
        db.execute(text("UPDATE profiles SET role = 'technician' WHERE id = :id"), {"id": tech})
        own_ticket = seed_ticket(db, employee)
        other_ticket = seed_ticket(db, other)
    with migration_database.begin() as db:
        authenticate(db, employee)
        assert db.execute(text("SELECT id FROM profiles")).scalars().all() == [employee]
        assert db.execute(text("SELECT id FROM tickets")).scalars().all() == [own_ticket]
    with pytest.raises(DBAPIError, match="permission denied"), migration_database.begin() as db:
        authenticate(db, employee)
        db.execute(text("UPDATE profiles SET role = 'technician'"))
    with pytest.raises(DBAPIError, match="permission denied"), migration_database.begin() as db:
        authenticate(db, employee)
        db.execute(text("UPDATE tickets SET status = 'Resolved'"))
    with migration_database.begin() as db:
        authenticate(db, tech)
        assert set(db.execute(text("SELECT id FROM tickets")).scalars()) == {own_ticket, other_ticket}
    with pytest.raises(DBAPIError, match="permission denied"), migration_database.begin() as db:
        db.exec_driver_sql("SET LOCAL ROLE anon")
        db.execute(text("SELECT id FROM tickets"))
    with pytest.raises(DBAPIError, match="permission denied"), migration_database.begin() as db:
        authenticate(db, tech)
        db.execute(text("SELECT version_num FROM helpdesk_alembic_version"))
    with pytest.raises(DBAPIError, match="fk_tickets_requester"), migration_database.begin() as db:
        seed_ticket(db, uuid4())


def test_migration_preserves_existing_tickets_and_requires_reviewed_owner_mapping(migration_database):
    employee = uuid4()
    with migration_database.begin() as db:
        seed_user(db, employee)
        db.exec_driver_sql("""
            CREATE TABLE tickets (
                id SERIAL PRIMARY KEY, title VARCHAR(160) NOT NULL, description TEXT NOT NULL,
                requester_id VARCHAR(64) NOT NULL, category VARCHAR(40) NOT NULL,
                priority VARCHAR(12) NOT NULL, recommended_team VARCHAR(120) NOT NULL,
                status VARCHAR(20) NOT NULL, classification_source VARCHAR(12) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL
            )
        """)
        db.exec_driver_sql("CREATE INDEX ix_tickets_requester_id ON tickets (requester_id)")
        legacy_ticket = seed_ticket(db, "demo-employee")
        uuid_ticket = seed_ticket(db, str(employee))
    apply_migration()
    with migration_database.begin() as db:
        rows = db.execute(text(
            "SELECT id, requester_id, legacy_requester_id, title FROM tickets ORDER BY id"
        )).all()
        assert rows == [
            (legacy_ticket, None, "demo-employee", "Existing ticket"),
            (uuid_ticket, None, str(employee), "Existing ticket"),
        ]
        assert db.execute(text("SELECT role FROM profiles")).scalar_one() == "employee"
    with migration_database.begin() as db:
        authenticate(db, employee)
        assert db.execute(text("SELECT id FROM tickets")).all() == []
    with migration_database.begin() as db:
        db.execute(text("UPDATE tickets SET requester_id = :owner WHERE id = :id"),
                   {"owner": employee, "id": legacy_ticket})
    with migration_database.begin() as db:
        authenticate(db, employee)
        assert db.execute(text("SELECT id FROM tickets")).scalars().all() == [legacy_ticket]


def test_authenticated_ticket_api_on_migrated_database(migration_database, monkeypatch):
    apply_migration()
    employee, technician = uuid4(), uuid4()
    with migration_database.begin() as db:
        seed_user(db, employee)
        seed_user(db, technician)
        db.execute(text("UPDATE profiles SET role = 'technician' WHERE id = :id"), {"id": technician})

    monkeypatch.setenv("SUPABASE_URL", "https://auth.example.test")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "test-publishable")
    if os.getenv("TEST_ML_SERVICE_URL"):
        monkeypatch.setattr(classifier, "ML_URL", os.environ["TEST_ML_SERVICE_URL"])
    else:
        monkeypatch.setattr(classifier.httpx, "post", lambda url, **kwargs: httpx.Response(
            200, request=httpx.Request("POST", url),
            json={"category": "Network", "confidence": 0.8, "model_version": "test-model"},
        ))

    def auth_provider(request):
        accounts = {"Bearer employee": employee, "Bearer technician": technician}
        user_id = accounts.get(request.headers.get("Authorization"))
        return httpx.Response(200, json={"id": str(user_id)}) if user_id else httpx.Response(401)

    employee_headers = {"Authorization": "Bearer employee"}
    technician_headers = {"Authorization": "Bearer technician"}
    with TestClient(main.app) as client, httpx.Client(transport=httpx.MockTransport(auth_provider)) as auth:
        main.api.state.auth_http = auth
        created = client.post("/tickets", headers=employee_headers, json={
            "title": "File Share Access", "description": "Please grant access to the shared folders."
        }).raise_for_status().json()
        assert created["requester_id"] == str(employee)
        assert created["classification_source"] == "model"
        assert created["classification_confidence"] is not None
        response = client.patch(
            f"/tickets/{created['id']}", headers=technician_headers, json={"status": "Resolved"},
        ).raise_for_status()
        assert response.json()["status"] == "Resolved"
        assert client.get("/tickets", headers=employee_headers).json()[0]["status"] == "Resolved"
