import os
from contextlib import contextmanager
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

import main
from app.api.auth import verified_user_id
from app.database import get_db
from app.models.profile import Profile
from app.models.ticket import Base, utc_now
from app.services import classifier

TICKET = {"title": " VPN keeps dropping ", "description": "Connection drops every few minutes."}
VALID_PREDICTION = {"category": "Network", "confidence": 0.85, "model_version": "v1"}
EMPLOYEE_ID = UUID("0e98bd2f-f7fe-4a4c-b7c0-84252c2477d0")
OTHER_ID = UUID("b717e982-7336-4896-ad93-5d9866a9920e")
TECHNICIAN_ID = UUID("93beb6ba-a431-4e8c-b036-724f14b8ddf5")
PROFILES = {"employee": EMPLOYEE_ID, "other-employee": OTHER_ID, "technician": TECHNICIAN_ID}
TECH = {"Authorization": "Bearer technician"}
OTHER = {"Authorization": "Bearer other-employee"}


@pytest.fixture
def database(tmp_path, monkeypatch):
    url = os.getenv("TEST_DATABASE_URL")
    engine = create_engine(url or f"sqlite:///{tmp_path / 'tickets.db'}")
    schema = None
    if url:
        schema = f"helpdesk_test_{uuid4().hex}"
        with engine.begin() as connection:
            connection.execute(CreateSchema(schema))
        engine = engine.execution_options(schema_translate_map={None: schema})

    def get_test_db():
        with Session(engine) as db:
            yield db

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(Profile(
            id=user_id, full_name=f"Test {token}", role="technician" if token == "technician" else "employee",
            created_at=utc_now(), updated_at=utc_now(),
        ) for token, user_id in PROFILES.items())
        db.commit()
    monkeypatch.setitem(main.api.dependency_overrides, get_db, get_test_db)
    yield
    if schema:
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
    engine.dispose()


@pytest.fixture
def new_client(database, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://auth.example.test")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "test-publishable")

    def auth_server(request):
        assert str(request.url) == "https://auth.example.test/auth/v1/user"
        assert request.headers["apikey"] == "test-publishable"
        token = request.headers["Authorization"].removeprefix("Bearer ")
        if token == "offline":
            raise httpx.ConnectError("Auth provider offline")
        if token not in PROFILES:
            return httpx.Response(401, json={"message": token})
        return httpx.Response(200, json={
            "id": str(PROFILES[token]), "user_metadata": {"role": "technician"}
        })

    @contextmanager
    def connected_client(token="employee"):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        with TestClient(main.app, headers=headers) as test_client:
            with httpx.Client(transport=httpx.MockTransport(auth_server)) as auth_http:
                main.api.state.auth_http = auth_http
                yield test_client

    return connected_client


@pytest.fixture
def client(new_client):
    with new_client() as test_client:
        yield test_client


def mock_classifier(monkeypatch, payload, status=200):
    seen = []

    def post(url, *, json, timeout):
        seen.append((url, json, timeout))
        return httpx.Response(status, request=httpx.Request("POST", url), json=payload)

    monkeypatch.setattr(classifier.httpx, "post", post)
    return seen


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_create_retrieve_and_filter_ticket(client, monkeypatch):
    seen = mock_classifier(monkeypatch, VALID_PREDICTION)
    response = client.post("/tickets", json=TICKET)
    assert response.status_code == 201
    ticket = response.json()
    assert ticket["title"] == TICKET["title"].strip()
    assert ticket["description"] == TICKET["description"]
    assert ticket["requester_id"] == str(EMPLOYEE_ID)
    assert ticket["status"] == "Open"
    assert ticket["category"] == "Network"
    assert ticket["recommended_team"] == "Network Support"
    assert ticket["priority"] == "Medium"
    assert ticket["classification_source"] == "model"
    assert ticket["classification_confidence"] == 0.85
    assert ticket["classification_model_version"] == "v1"
    assert seen == [(f"{classifier.ML_URL}/predict", {
        "title": TICKET["title"].strip(), "description": TICKET["description"]
    }, classifier.ML_TIMEOUT)]
    assert client.get(f"/tickets/{ticket['id']}").json() == ticket
    assert client.get("/tickets", params={
        "category": "Network", "status": "Open", "priority": "Medium"
    }).json() == [ticket]
    assert client.get("/tickets", params={"status": "Resolved"}).json() == []


def test_ticket_updates_visible_to_employee(client, monkeypatch):
    mock_classifier(monkeypatch, VALID_PREDICTION)
    ticket = client.post("/tickets", json=TICKET).json()
    path = f"/tickets/{ticket['id']}"
    updated = client.patch(path, headers=TECH, json={"status": "In Progress"}).json()
    assert updated["classification_source"] == "model"
    assert updated["updated_at"] > ticket["updated_at"]
    response = client.patch(path, headers=TECH, json={
        "status": "Resolved", "category": "Account Access", "priority": "High"
    })
    assert response.status_code == 200
    updated = response.json()
    assert updated["recommended_team"] == "Identity & Access Support"
    assert updated["classification_source"] == "manual"
    assert updated["priority"] == "High"
    assert updated["classification_confidence"] is None
    employee_tickets = client.get("/tickets").json()
    assert employee_tickets[0]["status"] == "Resolved"


@pytest.mark.parametrize("payload", [
    {"title": "", "description": "A problem"},
    {"title": " ", "description": "A problem"},
    {"title": "hello"},
    {**TICKET, "title": "x" * 161},
    {**TICKET, "description": "x" * 5001},
    {**TICKET, "description": "contains\u0000null"},
    {**TICKET, "impact": "everywhere"},
    {**TICKET, "requester_id": "someone-else"},
])
def test_invalid_creation(client, payload):
    assert client.post("/tickets", json=payload).status_code == 422
    assert client.get("/tickets").json() == []


@pytest.mark.parametrize("payload", [
    {}, {"status": None}, {"status": "Closed"}, {"category": "Unknown"}, {"title": "Rewrite"}
])
def test_invalid_update(client, payload):
    assert client.patch("/tickets/1", headers=TECH, json=payload).status_code == 422


def test_missing_ticket(client):
    assert client.get("/tickets/1").status_code == 404
    assert client.patch("/tickets/1", headers=TECH, json={"status": "Resolved"}).status_code == 404


@pytest.mark.parametrize("impact,urgency,expected", [
    ("Individual", "Routine", "Low"),
    ("Team", "Routine", "Medium"),
    ("Team", "Blocked", "High"),
    ("Organization", None, "High"),
    ("Organization", "Blocked", "Critical"),
])
def test_priority_rules(client, monkeypatch, impact, urgency, expected):
    mock_classifier(monkeypatch, VALID_PREDICTION)
    result = client.post("/tickets", json={**TICKET, "impact": impact, "urgency": urgency}).json()
    assert result["priority"] == expected


def test_ml_timeout_keeps_persisted_ticket(client, monkeypatch):
    def timeout(*_args, **_kwargs):
        raise httpx.ReadTimeout("Classifier timed out")

    monkeypatch.setattr(classifier.httpx, "post", timeout)
    response = client.post("/tickets", json=TICKET)
    assert response.status_code == 201
    ticket = response.json()
    assert ticket["category"] == "Unclassified"
    assert ticket["classification_source"] == "fallback"
    assert ticket["recommended_team"] == "General Support"
    assert client.get(f"/tickets/{ticket['id']}").json() == ticket


@pytest.mark.parametrize("payload,status", [
    ({"classification_source": "fallback", "category": "Unclassified"}, 200),
    ({**VALID_PREDICTION, "category": "Unexpected"}, 200),
    ({**VALID_PREDICTION, "confidence": 1.8}, 200),
    ({**VALID_PREDICTION, "confidence": "0.8"}, 200),
    (["invalid"], 200),
    ({}, 503),
])
def test_invalid_or_fallback_predictions(client, monkeypatch, payload, status):
    mock_classifier(monkeypatch, payload, status)
    response = client.post("/tickets", json=TICKET)
    assert response.status_code == 201
    assert response.json()["classification_source"] == "fallback"


def test_persistence_across_fresh_api_lifespans(new_client, monkeypatch):
    mock_classifier(monkeypatch, VALID_PREDICTION)
    with new_client() as app:
        ticket = app.post("/tickets", json=TICKET).json()
        app.patch(f"/tickets/{ticket['id']}", headers=TECH, json={"status": "Resolved"}).raise_for_status()
    with new_client() as restarted_app:
        response = restarted_app.get(f"/tickets/{ticket['id']}")
        assert response.json()["status"] == "Resolved"


def test_model_does_not_replace_manual_classification(client, monkeypatch):
    def classify_after_manual_edit(url, **_kwargs):
        persisted = client.get("/tickets").json()
        assert len(persisted) == 1
        client.patch(f"/tickets/{persisted[0]['id']}", headers=TECH, json={"category": "Hardware"}).raise_for_status()
        return httpx.Response(200, request=httpx.Request("POST", url), json=VALID_PREDICTION)

    monkeypatch.setattr(classifier.httpx, "post", classify_after_manual_edit)
    ticket = client.post("/tickets", json=TICKET).json()
    assert ticket["category"] == "Hardware"
    assert ticket["recommended_team"] == "Hardware Support"
    assert ticket["classification_source"] == "manual"


def test_cross_origin_patch_preflight(client):
    response = client.options("/tickets/1", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "PATCH",
        "Access-Control-Request-Headers": "content-type,authorization",
    })
    assert response.status_code == 200
    assert "PATCH" in response.headers["access-control-allow-methods"]


@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://127.0.0.1:5173"])
def test_auth_preflight_allows_bearer_header(client, origin):
    response = client.options("/auth/me", headers={
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization",
    })
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "authorization" in response.headers["access-control-allow-headers"].lower()


def test_auth_preflight_rejects_unlisted_origin(client):
    response = client.options("/auth/me", headers={
        "Origin": "https://unlisted.example.test",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization",
    })
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_unexpected_profile_error_preserves_cors_and_hides_details(monkeypatch):
    def unexpected():
        raise RuntimeError("private error details")

    monkeypatch.setitem(main.api.dependency_overrides, verified_user_id, unexpected)
    origin = "http://localhost:5173"
    with TestClient(main.app, raise_server_exceptions=False) as app:
        response = app.get("/auth/me", headers={"Origin": origin})
    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == origin
    assert "private error details" not in response.text


@pytest.mark.parametrize("method,path", [
    ("GET", "/auth/me"), ("GET", "/tickets"), ("POST", "/tickets"),
    ("GET", "/tickets/1"), ("PATCH", "/tickets/1"),
])
def test_missing_bearer_is_rejected(new_client, method, path):
    with new_client(token=None) as anonymous:
        response = anonymous.request(method, path, json=TICKET if method == "POST" else None)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("token", ["expired access token", "invalid JWT signature"])
def test_provider_rejects_invalid_tokens(new_client, token):
    with new_client(token=token) as connection:
        assert connection.get("/auth/me").status_code == 401


def test_auth_provider_outage_fails_closed(new_client):
    with new_client(token="offline") as connection:
        assert connection.get("/tickets").status_code == 503


def test_role_and_ownership_are_server_enforced(client, monkeypatch):
    mock_classifier(monkeypatch, VALID_PREDICTION)
    ticket = client.post("/tickets", json=TICKET).raise_for_status().json()
    other = client.post("/tickets", headers=OTHER, json=TICKET).raise_for_status().json()
    path = f"/tickets/{ticket['id']}"
    identity = client.get("/auth/me").json()
    assert identity["role"] == "employee"
    assert identity["id"] == str(EMPLOYEE_ID)
    assert client.patch("/auth/me", json={"role": "technician"}).status_code == 405
    assert client.get("/tickets", params={"requester_id": str(OTHER_ID)}).json() == [ticket]
    assert client.get("/tickets", headers=OTHER).json() == [other]
    assert client.get(path, headers=OTHER).status_code == 403
    assert client.patch(path, json={"status": "Resolved"}).status_code == 403
    assert client.get("/auth/me", headers=TECH).json()["role"] == "technician"
    assert client.get("/tickets", headers=TECH).json() == [other, ticket]
    assert client.get(path, headers=TECH).json() == ticket
    assert client.post("/tickets", headers=TECH, json=TICKET).status_code == 403


@pytest.mark.skipif(not os.getenv("TEST_ML_SERVICE_URL"), reason="Requires a trained local R service")
def test_live_classifier_with_authenticated_ticket(client, monkeypatch):
    monkeypatch.setattr(classifier, "ML_URL", os.environ["TEST_ML_SERVICE_URL"])
    ticket = client.post("/tickets", json={
        "title": "File Share Access", "description": "Please grant access to the shared folders."
    }).raise_for_status().json()
    assert ticket["requester_id"] == str(EMPLOYEE_ID)
    assert ticket["classification_source"] == "model"
    assert 0 <= ticket["classification_confidence"] <= 1
    assert ticket["recommended_team"]
    assert client.get(f"/tickets/{ticket['id']}").json() == ticket

def test_only_technicians_can_delete_tickets(client, monkeypatch):
    mock_classifier(monkeypatch, VALID_PREDICTION)
    ticket = client.post("/tickets", json=TICKET).raise_for_status().json()
    other = client.post(
        "/tickets", headers=OTHER, json=TICKET
    ).raise_for_status().json()
    path = f"/tickets/{ticket['id']}"

    assert client.delete(path).status_code == 403
    assert client.get(path).json() == ticket
    assert client.delete("/tickets/0", headers=TECH).status_code == 422

    response = client.delete(path, headers=TECH)
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(path).status_code == 404
    assert client.get("/tickets", headers=TECH).json() == [other]
    assert client.delete(path, headers=TECH).status_code == 404