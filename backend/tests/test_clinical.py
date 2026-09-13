"""Tests for the Phase 1/2 clinical case-taking + red-flag engine.

Uses the same fixture pattern as tests/test_api.py (full ASGI app, no DB
mocking) so it's consistent with the project's existing test conventions.
Each run registers uniquely-emailed users to avoid clashing with previous
runs against the same (non-reset) dev database.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

API = "/api/v1"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _register_and_login(client: AsyncClient) -> dict:
    email = f"clinical-{uuid.uuid4().hex[:10]}@medicare.app"
    password = "securepass123"
    resp = await client.post(
        f"{API}/auth/register",
        json={"email": email, "password": password, "full_name": "Test Patient"},
    )
    assert resp.status_code == 201, resp.text

    resp = await client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_start_clinical_session_normal_complaint(client):
    headers = await _register_and_login(client)

    resp = await client.post(
        f"{API}/clinical-sessions",
        json={"chief_complaint": "I have a headache for 2 days", "language": "en"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()

    assert data["chief_complaint"] == "I have a headache for 2 days"
    assert data["status"] == "active"
    assert len(data["questions"]) == 1  # first adaptive question was generated
    assert data["red_flags"] == []  # plain headache is not an emergency


@pytest.mark.asyncio
async def test_submit_answer_returns_next_question_and_stores_history(client):
    headers = await _register_and_login(client)

    resp = await client.post(
        f"{API}/clinical-sessions",
        json={"chief_complaint": "I have a headache for 2 days"},
        headers=headers,
    )
    session = resp.json()
    session_id = session["id"]
    first_question = session["questions"][0]

    resp = await client.post(
        f"{API}/clinical-sessions/{session_id}/answers",
        json={"question_id": first_question["id"], "field": first_question["field"], "content": "Started this morning"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["answer"]["field"] == first_question["field"]
    assert data["should_continue"] is True
    assert data["next_question"] is not None
    # The engine must not re-ask the field that was just answered.
    assert data["next_question"]["field"] != first_question["field"]

    # Confirm it was actually persisted on the session.
    resp = await client.get(f"{API}/clinical-sessions/{session_id}", headers=headers)
    assert resp.status_code == 200
    session_state = resp.json()
    assert session_state["collected_fields"].get(first_question["field"]) == "Started this morning"
    assert len(session_state["answers"]) == 1


@pytest.mark.asyncio
async def test_session_completion(client):
    headers = await _register_and_login(client)

    resp = await client.post(
        f"{API}/clinical-sessions", json={"chief_complaint": "Mild sore throat"}, headers=headers
    )
    session_id = resp.json()["id"]

    resp = await client.post(f"{API}/clinical-sessions/{session_id}/complete", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert resp.json()["completed_at"] is not None

    # Answering after completion should be rejected.
    resp = await client.post(
        f"{API}/clinical-sessions/{session_id}/answers",
        json={"field": "onset", "content": "yesterday"},
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_red_flag_detected_for_emergency_complaint(client):
    headers = await _register_and_login(client)

    resp = await client.post(
        f"{API}/clinical-sessions",
        json={"chief_complaint": "I suddenly have severe chest pain and difficulty breathing"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()

    assert len(data["red_flags"]) >= 1
    flag = data["red_flags"][0]
    assert flag["severity"] in ("high", "critical")
    assert flag["recommended_action"] == "urgent_medical_attention"
    assert any("chest" in s or "breath" in s for s in flag["detected_symptoms"])

    # And it's independently retrievable via the dedicated endpoint.
    resp = await client.get(f"{API}/clinical-sessions/{data['id']}/red-flags", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_no_false_positive_red_flag_on_normal_answer(client):
    headers = await _register_and_login(client)

    resp = await client.post(
        f"{API}/clinical-sessions", json={"chief_complaint": "I have a mild headache"}, headers=headers
    )
    session = resp.json()
    assert session["red_flags"] == []
    first_question = session["questions"][0]

    resp = await client.post(
        f"{API}/clinical-sessions/{session['id']}/answers",
        json={"question_id": first_question["id"], "field": first_question["field"], "content": "No nausea, no vomiting, just a dull ache"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["red_flags"] == []


@pytest.mark.asyncio
async def test_duplicate_red_flag_not_recreated_for_same_symptoms(client):
    headers = await _register_and_login(client)

    resp = await client.post(
        f"{API}/clinical-sessions",
        json={"chief_complaint": "severe chest pain and difficulty breathing"},
        headers=headers,
    )
    session = resp.json()
    session_id = session["id"]
    initial_flag_count = len(session["red_flags"])
    assert initial_flag_count >= 1
    first_question = session["questions"][0]

    # Mentioning the same emergency symptoms again should not duplicate the alert.
    resp = await client.post(
        f"{API}/clinical-sessions/{session_id}/answers",
        json={
            "question_id": first_question["id"],
            "field": first_question["field"],
            "content": "Yes still the same severe chest pain and difficulty breathing",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["red_flags"] == []  # no *new* alert returned

    resp = await client.get(f"{API}/clinical-sessions/{session_id}/red-flags", headers=headers)
    assert len(resp.json()) == initial_flag_count


@pytest.mark.asyncio
async def test_patient_cannot_access_another_patients_session(client):
    headers_a = await _register_and_login(client)
    headers_b = await _register_and_login(client)

    resp = await client.post(
        f"{API}/clinical-sessions", json={"chief_complaint": "Patient A's private complaint"}, headers=headers_a
    )
    session_id = resp.json()["id"]

    # Patient B cannot read it.
    resp = await client.get(f"{API}/clinical-sessions/{session_id}", headers=headers_b)
    assert resp.status_code == 404

    # Patient B cannot answer it.
    resp = await client.post(
        f"{API}/clinical-sessions/{session_id}/answers",
        json={"field": "onset", "content": "trying to inject an answer"},
        headers=headers_b,
    )
    assert resp.status_code == 404

    # Patient B cannot read its red flags either.
    resp = await client.get(f"{API}/clinical-sessions/{session_id}/red-flags", headers=headers_b)
    assert resp.status_code == 404

    # Unauthenticated requests are rejected outright.
    resp = await client.get(f"{API}/clinical-sessions/{session_id}")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_existing_apis_still_work(client):
    """Sanity check that Phase 2 additions didn't break pre-existing routes."""
    resp = await client.get("/health")
    assert resp.status_code == 200

    headers = await _register_and_login(client)
    resp = await client.get(f"{API}/dashboard", headers=headers)
    assert resp.status_code == 200

    resp = await client.get(f"{API}/doctors", headers=headers)
    assert resp.status_code == 200
