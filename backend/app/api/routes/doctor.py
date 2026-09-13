"""Doctor Portal: appointment queue, patient clinical view, red-flag
acknowledgement, and clinical-summary review.

Deliberately separate from app.api.routes.doctors (patient-facing doctor
listing/booking) — everything in this module requires get_current_doctor and
only ever exposes data the requesting doctor is actually entitled to see.

Reuses, rather than duplicates:
- app.core.deps.get_current_doctor / log_audit for auth + auditability
- app.services.patient_context.get_patient_context for the clinical picture
- app.ai.services.generate_clinical_summary + Appointment.call_summary for
  the AI summary (this module never generates a second, competing summary
  engine — it only adds a doctor_review layer on top)
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.services import generate_clinical_summary
from app.core.database import get_db
from app.core.deps import get_client_ip, get_current_doctor, log_audit
from app.models import (
    Appointment,
    ClinicalSession,
    ClinicalSessionStatus,
    Doctor,
    RedFlagAlert,
)
from app.schemas import (
    AppointmentResponse,
    DoctorAppointmentItem,
    DoctorPatientBasicInfo,
    DoctorPatientSummaryResponse,
    DoctorSummaryReviewRequest,
    RedFlagAcknowledgeRequest,
    RedFlagAlertResponse,
)
from app.services.patient_context import get_patient_context

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/doctor", tags=["Doctor Portal"])

_SEVERITY_RANK = {"low": 0, "moderate": 1, "high": 2, "critical": 3}


# ==========================================================
# Shared helpers
# ==========================================================

def _appointment_load_options():
    return (selectinload(Appointment.patient), selectinload(Appointment.doctor))


async def _get_owned_appointment(
    appointment_id: uuid.UUID, doctor: Doctor, db: AsyncSession
) -> Appointment:
    """Fetch an appointment, enforcing that it belongs to the requesting
    doctor. An appointment that exists but belongs to another doctor returns
    404 (not 403) so we don't confirm the id is valid to an unrelated party.
    """
    result = await db.execute(
        select(Appointment)
        .options(*_appointment_load_options())
        .where(Appointment.id == appointment_id, Appointment.doctor_id == doctor.id)
    )
    appointment = result.scalar_one_or_none()
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment


async def _latest_clinical_session(
    db: AsyncSession, patient_id: uuid.UUID
) -> ClinicalSession | None:
    """Most recent clinical session for this patient.

    Known limitation: there is no direct FK from Appointment to
    ClinicalSession in the current schema, so this is inferred by patient
    identity + recency rather than tied to this specific appointment. Good
    enough for a single-active-case prototype; a future phase should add an
    explicit link if patients can have multiple concurrent cases.
    """
    result = await db.execute(
        select(ClinicalSession)
        .options(selectinload(ClinicalSession.red_flags))
        .where(ClinicalSession.user_id == patient_id)
        .order_by(ClinicalSession.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _doctor_has_relationship_with_patient(
    db: AsyncSession, doctor: Doctor, patient_id: uuid.UUID
) -> bool:
    result = await db.execute(
        select(Appointment.id)
        .where(Appointment.doctor_id == doctor.id, Appointment.patient_id == patient_id)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


# ==========================================================
# 1. Doctor appointment queue
# ==========================================================

@router.get("/appointments", response_model=list[DoctorAppointmentItem])
async def list_doctor_appointments(
    doctor: Annotated[Doctor, Depends(get_current_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.patient))
        .where(Appointment.doctor_id == doctor.id)
        .order_by(Appointment.scheduled_at.desc())
    )
    appointments = result.scalars().all()

    items: list[DoctorAppointmentItem] = []
    for appt in appointments:
        session = await _latest_clinical_session(db, appt.patient_id)

        clinical_session_status = None
        history_completed = False
        has_red_flags = False
        highest_red_flag_severity = None
        red_flag_count = 0

        if session is not None:
            clinical_session_status = (
                session.status.value if hasattr(session.status, "value") else str(session.status)
            )
            history_completed = session.status == ClinicalSessionStatus.COMPLETED
            flags = session.red_flags
            red_flag_count = len(flags)
            has_red_flags = red_flag_count > 0
            if flags:
                highest_red_flag_severity = max(
                    flags, key=lambda f: _SEVERITY_RANK.get(f.severity.value, 0)
                ).severity.value

        items.append(
            DoctorAppointmentItem(
                id=appt.id,
                scheduled_at=appt.scheduled_at,
                status=appt.status,
                notes=appt.notes,
                call_summary=appt.call_summary,
                patient=DoctorPatientBasicInfo.model_validate(appt.patient),
                clinical_session_status=clinical_session_status,
                history_completed=history_completed,
                has_red_flags=has_red_flags,
                highest_red_flag_severity=highest_red_flag_severity,
                red_flag_count=red_flag_count,
                summary_available=appt.call_summary is not None,
            )
        )
    return items


# ==========================================================
# 2. Doctor patient clinical view (per-appointment)
# ==========================================================

@router.get("/appointments/{appointment_id}/patient-summary", response_model=DoctorPatientSummaryResponse)
async def get_doctor_patient_summary(
    appointment_id: uuid.UUID,
    doctor: Annotated[Doctor, Depends(get_current_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    appointment = await _get_owned_appointment(appointment_id, doctor, db)

    try:
        context = await get_patient_context(db, appointment.patient_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Patient context not found")

    return DoctorPatientSummaryResponse(
        appointment_id=appointment.id,
        call_summary=appointment.call_summary,
        patient_context=context.model_dump(),
    )


# ==========================================================
# 3. Red-flag acknowledgement
# ==========================================================

@router.patch("/red-flags/{alert_id}/acknowledge", response_model=RedFlagAlertResponse)
async def acknowledge_red_flag(
    alert_id: uuid.UUID,
    data: RedFlagAcknowledgeRequest,
    request: Request,
    doctor: Annotated[Doctor, Depends(get_current_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(RedFlagAlert).where(RedFlagAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail="Red flag alert not found")

    # A doctor may only acknowledge alerts for a patient they actually have
    # an appointment with — never a hard-coded id, never an arbitrary patient.
    if not await _doctor_has_relationship_with_patient(db, doctor, alert.user_id):
        raise HTTPException(status_code=404, detail="Red flag alert not found")

    alert.acknowledged = True
    alert.acknowledged_by = doctor.user_id
    alert.acknowledged_at = datetime.now(timezone.utc)
    # Never deleted — this is an append-only clinical safety record.

    await log_audit(
        db,
        doctor.user_id,
        action="acknowledge_red_flag",
        resource="red_flag_alert",
        details={"alert_id": str(alert.id), "note": data.note} if data.note else {"alert_id": str(alert.id)},
        ip=get_client_ip(request),
    )
    await db.flush()
    await db.refresh(alert)
    return alert


# ==========================================================
# 4. Doctor summary review
# ==========================================================

@router.patch("/appointments/{appointment_id}/summary-review", response_model=AppointmentResponse)
async def review_clinical_summary(
    appointment_id: uuid.UUID,
    data: DoctorSummaryReviewRequest,
    doctor: Annotated[Doctor, Depends(get_current_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Let the doctor correct the AI-generated clinical summary.

    Corrections are stored under call_summary['doctor_review'], never by
    overwriting the original AI fields — this is a decision-support tool,
    and an AI inference must not silently become a confirmed medical fact.
    Anyone reading call_summary can still see exactly what the AI produced
    and, separately, what the reviewing doctor confirmed or corrected.
    """
    appointment = await _get_owned_appointment(appointment_id, doctor, db)

    if appointment.call_summary is not None:
        base_summary = dict(appointment.call_summary)
        existing_review = dict(base_summary.pop("doctor_review", {}) or {})
    else:
        # No AI summary yet for this appointment — reuse the existing
        # aggregator + generator (not a new summary engine) so the doctor
        # isn't blocked on the patient having triggered it first.
        try:
            context = await get_patient_context(db, appointment.patient_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Patient context not found")
        base_summary = await generate_clinical_summary(context.to_prompt_text())
        existing_review = {}

    updated_review = dict(existing_review)
    for field in (
        "chief_complaints",
        "symptoms",
        "medical_history",
        "medications",
        "allergies",
        "reports",
        "important_findings",
        "doctor_notes",
    ):
        value = getattr(data, field)
        if value is not None:
            updated_review[field] = value

    updated_review["reviewed"] = True
    updated_review["reviewed_by"] = str(doctor.user_id) if doctor.user_id else None
    updated_review["reviewed_at"] = datetime.now(timezone.utc).isoformat()

    new_call_summary = dict(base_summary)
    new_call_summary["doctor_review"] = updated_review
    appointment.call_summary = new_call_summary

    await db.flush()
    await db.refresh(appointment)
    return appointment
