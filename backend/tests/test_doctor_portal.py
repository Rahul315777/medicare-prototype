"""Tests for the Doctor Portal: appointment queue, patient clinical view,
red-flag acknowledgement, and summary review.

Same fixture pattern as tests/test_clinical.py (full ASGI app, no DB
mocking). Doctor accounts can't be created through the public /auth/register
endpoint (by design — self-registration as a doctor shouldn't be possible),
so tests create the User(role=DOCTOR) + Doctor row directly via the app's
own AsyncSessionLocal, exactly as an admin/seeding script would.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.main import app
from app.models import Appointment, Doctor, User, UserRole

API = "/api/v1"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _register_and_login(client: AsyncClient, label: str = "patient") -> tuple[dict, uuid.UUID]:
    email = f"{label}-{uuid.uuid4().hex[:10]}@medicare.app"
    password = "securepass123"
    resp = await client.post(
        f"{API}/auth/register",
        json={"email": email, "password": password, "full_name": f"Test {label.title()}"},
    )
    assert resp.status_code == 201, resp.text

    resp = await client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]

    me = await client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = uuid.UUID(me.json()["id"])
    return {"Authorization": f"Bearer {token}"}, user_id


async def _create_doctor_account(client: AsyncClient, name: str = "Dr. Test") -> tuple[dict, uuid.UUID]:
    """Create a DOCTOR-role user with a linked Doctor row directly in the DB
    (there is no public self-registration path for doctors), then log in
    through the normal API to get a real access token."""
    email = f"doctor-{uuid.uuid4().hex[:10]}@medicare.app"
    password = "securepass123"

    async with AsyncSessionLocal() as db:
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name=name,
            role=UserRole.DOCTOR,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.flush()

        doctor = Doctor(user_id=user.id, name=name, specialty="General Physician")
        db.add(doctor)
        await db.commit()
        await db.refresh(doctor)
        doctor_id = doctor.id
        user_id = user.id

    resp = await client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, doctor_id, user_id


async def _book_appointment(client: AsyncClient, patient_headers: dict, doctor_id: uuid.UUID) -> uuid.UUID:
    resp = await client.post(
        f"{API}/appointments",
        json={
            "doctor_id": str(doctor_id),
            "scheduled_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        },
        headers=patient_headers,
    )
    assert resp.status_code == 201, resp.text
    return uuid.UUID(resp.json()["id"])


# ==========================================================
# Authorization
# ==========================================================

@pytest.mark.asyncio
async def test_normal_user_cannot_access_doctor_appointments(client):
    patient_headers, _ = await _register_and_login(client)
    resp = await client.get(f"{API}/doctor/appointments", headers=patient_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_cannot_access_doctor_appointments(client):
    resp = await client.get(f"{API}/doctor/appointments")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_doctor_sees_own_appointment_and_not_unrelated_one(client):
    doctor_a_headers, doctor_a_id, _ = await _create_doctor_account(client, "Dr. A")
    doctor_b_headers, doctor_b_id, _ = await _create_doctor_account(client, "Dr. B")
    patient_headers, _ = await _register_and_login(client)

    appt_id = await _book_appointment(client, patient_headers, doctor_a_id)

    resp = await client.get(f"{API}/doctor/appointments", headers=doctor_a_headers)
    assert resp.status_code == 200, resp.text
    ids = [a["id"] for a in resp.json()]
    assert str(appt_id) in ids

    resp = await client.get(f"{API}/doctor/appointments", headers=doctor_b_headers)
    assert resp.status_code == 200
    ids_b = [a["id"] for a in resp.json()]
    assert str(appt_id) not in ids_b

    # Doctor B cannot pull Doctor A's appointment patient-summary directly either.
    resp = await client.get(f"{API}/doctor/appointments/{appt_id}/patient-summary", headers=doctor_b_headers)
    assert resp.status_code == 404


# ==========================================================
# Patient summary content + red flags
# ==========================================================

@pytest.mark.asyncio
async def test_doctor_patient_summary_includes_clinical_session_and_red_flags(client):
    doctor_headers, doctor_id, _ = await _create_doctor_account(client)
    patient_headers, _ = await _register_and_login(client)

    # Patient has a red-flag-triggering clinical session.
    resp = await client.post(
        f"{API}/clinical-sessions",
        json={"chief_complaint": "I suddenly have severe chest pain and difficulty breathing"},
        headers=patient_headers,
    )
    assert resp.status_code == 201, resp.text

    appt_id = await _book_appointment(client, patient_headers, doctor_id)

    # Queue should reflect the red flag before the doctor even opens the detail view.
    resp = await client.get(f"{API}/doctor/appointments", headers=doctor_headers)
    assert resp.status_code == 200
    row = next(a for a in resp.json() if a["id"] == str(appt_id))
    assert row["has_red_flags"] is True
    assert row["highest_red_flag_severity"] in ("high", "critical")
    assert row["red_flag_count"] >= 1

    resp = await client.get(f"{API}/doctor/appointments/{appt_id}/patient-summary", headers=doctor_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["appointment_id"] == str(appt_id)
    sessions = data["patient_context"]["clinical_sessions"]
    assert len(sessions) >= 1
    flags = sessions[0]["red_flags"]
    assert len(flags) >= 1
    assert flags[0]["severity"] in ("high", "critical")
    assert flags[0]["acknowledged"] is False


# ==========================================================
# Red-flag acknowledgement
# ==========================================================

@pytest.mark.asyncio
async def test_doctor_can_acknowledge_related_patients_red_flag(client):
    doctor_headers, doctor_id, _doctor_user_id = await _create_doctor_account(client)
    patient_headers, _ = await _register_and_login(client)

    resp = await client.post(
        f"{API}/clinical-sessions",
        json={"chief_complaint": "severe chest pain and difficulty breathing"},
        headers=patient_headers,
    )
    alert_id = resp.json()["red_flags"][0]["id"]

    await _book_appointment(client, patient_headers, doctor_id)

    resp = await client.patch(
        f"{API}/doctor/red-flags/{alert_id}/acknowledge",
        json={"note": "Reviewed, advised ER."},
        headers=doctor_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["acknowledged"] is True
    assert data["acknowledged_at"] is not None


@pytest.mark.asyncio
async def test_unrelated_doctor_cannot_acknowledge_red_flag(client):
    doctor_headers, _doctor_id, _ = await _create_doctor_account(client, "Dr. Unrelated")
    patient_headers, _ = await _register_and_login(client)

    resp = await client.post(
        f"{API}/clinical-sessions",
        json={"chief_complaint": "severe chest pain and difficulty breathing"},
        headers=patient_headers,
    )
    alert_id = resp.json()["red_flags"][0]["id"]

    # No appointment ever booked between this doctor and this patient.
    resp = await client.patch(
        f"{API}/doctor/red-flags/{alert_id}/acknowledge",
        json={},
        headers=doctor_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_normal_user_cannot_acknowledge_red_flag(client):
    patient_headers, _ = await _register_and_login(client)
    resp = await client.post(
        f"{API}/clinical-sessions",
        json={"chief_complaint": "severe chest pain and difficulty breathing"},
        headers=patient_headers,
    )
    alert_id = resp.json()["red_flags"][0]["id"]

    resp = await client.patch(
        f"{API}/doctor/red-flags/{alert_id}/acknowledge",
        json={},
        headers=patient_headers,
    )
    assert resp.status_code == 403


# ==========================================================
# Summary review
# ==========================================================

@pytest.mark.asyncio
async def test_doctor_summary_review_preserves_ai_output_and_adds_review(client):
    doctor_headers, doctor_id, doctor_user_id = await _create_doctor_account(client)
    patient_headers, _ = await _register_and_login(client)

    resp = await client.post(
        f"{API}/clinical-sessions", json={"chief_complaint": "Mild sore throat"}, headers=patient_headers
    )
    assert resp.status_code == 201

    appt_id = await _book_appointment(client, patient_headers, doctor_id)

    # No GROQ_API_KEY reachable in this sandbox -> generate_clinical_summary
    # falls back to its documented "Not provided" shape. That's fine: this
    # test checks the review layering behavior, not AI output quality.
    resp = await client.patch(
        f"{API}/doctor/appointments/{appt_id}/summary-review",
        json={"chief_complaints": "Sore throat, 2 days, no fever", "doctor_notes": "Likely viral pharyngitis."},
        headers=doctor_headers,
    )
    assert resp.status_code == 200, resp.text
    call_summary = resp.json()["call_summary"]

    assert "doctor_review" in call_summary
    review = call_summary["doctor_review"]
    assert review["chief_complaints"] == "Sore throat, 2 days, no fever"
    assert review["doctor_notes"] == "Likely viral pharyngitis."
    assert review["reviewed"] is True
    assert review["reviewed_by"] == str(doctor_user_id)

    # The AI-generated field(s) at the top level must still be present and
    # untouched by the doctor's correction (provenance preserved).
    assert "chief_complaints" in call_summary
    assert "symptoms" in call_summary


@pytest.mark.asyncio
async def test_unrelated_doctor_cannot_review_summary(client):
    doctor_a_headers, doctor_a_id, _ = await _create_doctor_account(client, "Dr. A")
    doctor_b_headers, _doctor_b_id, _ = await _create_doctor_account(client, "Dr. B")
    patient_headers, _ = await _register_and_login(client)

    appt_id = await _book_appointment(client, patient_headers, doctor_a_id)

    resp = await client.patch(
        f"{API}/doctor/appointments/{appt_id}/summary-review",
        json={"chief_complaints": "Should not be allowed"},
        headers=doctor_b_headers,
    )
    assert resp.status_code == 404


# ==========================================================
# Sanity: Phase 1/2 still intact after this change
# ==========================================================

@pytest.mark.asyncio
async def test_existing_clinical_flow_still_works(client):
    patient_headers, _ = await _register_and_login(client)
    resp = await client.post(
        f"{API}/clinical-sessions", json={"chief_complaint": "I have a headache for 2 days"}, headers=patient_headers
    )
    assert resp.status_code == 201
    assert resp.json()["red_flags"] == []
