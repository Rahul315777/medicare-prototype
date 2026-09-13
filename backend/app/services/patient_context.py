"""
Unified Patient Context Aggregator
===================================

Phase 2 of the MediCare end-to-end workflow.

This is a single, read-only service that pulls together everything the
system currently knows about one patient — profile, chat history, OCR
report data, and prescriptions — from the *existing* tables. It adds no new
tables and invents nothing: any field that isn't actually in the DB is made
explicit as "unknown/not provided" rather than guessed, per the project's
medical-safety rule against fabricating patient info.

Consumers (built in later phases):
    - Phase 3: the chatbot can pull report OCR text from here as context.
    - Phase 4: the Clinical Summary generator feeds this + the LLM.
    - Phase 5: the doctor-facing appointment view renders this directly.

Nothing in the codebase calls this yet — it's a standalone building block.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    ChatSession,
    ClinicalSession,
    FamilyProfile,
    FamilyRelation,
    MedicalReport,
    Prescription,
    RedFlagAlert,
    User,
)

NOT_PROVIDED = "unknown/not provided"

# Keep the context focused and cheap to build — these are generous enough
# for a chat prompt or a doctor's summary view without pulling a patient's
# entire lifetime history on every call.
MAX_CHAT_SESSIONS = 3
MAX_MESSAGES_PER_SESSION = 20
MAX_REPORTS = 10
MAX_PRESCRIPTIONS = 10


# ==========================================================
# Output shape
# ==========================================================

class PatientInfo(BaseModel):
    user_id: uuid.UUID
    full_name: str
    email: str
    phone: str = NOT_PROVIDED
    age: int | str = NOT_PROVIDED
    gender: str = NOT_PROVIDED
    blood_group: str = NOT_PROVIDED
    known_allergies: list[str] = []
    known_medical_history: list[str] = []


class ChatTurn(BaseModel):
    role: str
    content: str
    created_at: datetime


class ChatSessionSummary(BaseModel):
    session_id: uuid.UUID
    language: str
    updated_at: datetime
    messages: list[ChatTurn]


class OCRDocument(BaseModel):
    report_id: uuid.UUID
    title: str
    report_type: str
    # Kept for backend/LLM use only. Per the Phase 3 rule, raw OCR text must
    # stay out of the patient-facing UI — callers building an API response
    # for the frontend should drop this field, not just this service.
    ocr_text: str | None
    findings: dict[str, Any] | None  # the structured `analysis` JSON (summary/explanation/values/risk_level)
    risk_level: str = NOT_PROVIDED
    created_at: datetime


class PrescriptionSummary(BaseModel):
    prescription_id: uuid.UUID
    doctor_name: str = NOT_PROVIDED
    medicines: list[dict[str, Any]] = []
    created_at: datetime


class RedFlagSummary(BaseModel):
    alert_id: uuid.UUID
    severity: str
    detected_symptoms: list[str] = []
    reason: str
    recommended_action: str
    source: str = NOT_PROVIDED
    acknowledged: bool
    acknowledged_at: datetime | None = None
    created_at: datetime


class ClinicalSessionSummary(BaseModel):
    session_id: uuid.UUID
    status: str
    chief_complaint: str = NOT_PROVIDED
    collected_fields: dict[str, Any] = {}
    red_flags: list[RedFlagSummary] = []
    created_at: datetime


class PatientContext(BaseModel):
    patient: PatientInfo
    recent_chats: list[ChatSessionSummary]
    reports: list[OCRDocument]
    prescriptions: list[PrescriptionSummary]
    # Phase 1/2: structured AI pre-consultation interviews and any
    # triage/red-flag signals raised during them.
    clinical_sessions: list[ClinicalSessionSummary] = []
    has_any_data: bool  # False ⇒ brand-new patient, nothing recorded yet

    def to_prompt_text(self) -> str:
        """Flatten this context into a plain-text block suitable for an LLM
        prompt (used by the Phase 4 Clinical Summary generator). Every
        section explicitly states when data isn't available rather than
        omitting it silently, so the model can't quietly fill the gap."""
        p = self.patient
        lines: list[str] = []

        lines.append("PATIENT PROFILE:")
        lines.append(f"- Name: {p.full_name}")
        lines.append(f"- Age: {p.age}")
        lines.append(f"- Gender: {p.gender}")
        lines.append(f"- Blood group: {p.blood_group}")
        lines.append(
            f"- Known allergies: {', '.join(p.known_allergies) if p.known_allergies else NOT_PROVIDED}"
        )
        lines.append(
            f"- Known medical history: {', '.join(p.known_medical_history) if p.known_medical_history else NOT_PROVIDED}"
        )

        lines.append("\nRECENT CHAT / SYMPTOM CONVERSATION:")
        if self.recent_chats:
            for session in self.recent_chats:
                for msg in session.messages:
                    lines.append(f"- [{msg.role}] {msg.content}")
        else:
            lines.append(f"- {NOT_PROVIDED}")

        lines.append("\nUPLOADED REPORTS (OCR-derived findings):")
        if self.reports:
            for r in self.reports:
                summary = (r.findings or {}).get("summary", NOT_PROVIDED)
                lines.append(f"- {r.title} ({r.report_type}, risk: {r.risk_level}): {summary}")
        else:
            lines.append(f"- {NOT_PROVIDED}")

        lines.append("\nCURRENT PRESCRIPTIONS:")
        if self.prescriptions:
            for rx in self.prescriptions:
                med_names = ", ".join(m.get("name", "Unknown") for m in rx.medicines) or NOT_PROVIDED
                lines.append(f"- From {rx.doctor_name}: {med_names}")
        else:
            lines.append(f"- {NOT_PROVIDED}")

        lines.append("\nAI PRE-CONSULTATION CLINICAL INTERVIEW:")
        if self.clinical_sessions:
            for cs in self.clinical_sessions:
                lines.append(f"- Chief complaint: {cs.chief_complaint} (status: {cs.status})")
                for field, value in cs.collected_fields.items():
                    lines.append(f"  - {field}: {value}")
                for rf in cs.red_flags:
                    lines.append(
                        f"  - RED FLAG ({rf.severity}): {', '.join(rf.detected_symptoms) or NOT_PROVIDED} — {rf.reason}"
                    )
        else:
            lines.append(f"- {NOT_PROVIDED}")

        return "\n".join(lines)


# ==========================================================
# Aggregator
# ==========================================================

async def get_patient_context(db: AsyncSession, user_id: uuid.UUID | str) -> PatientContext:
    """Build the unified context for one patient.

    Raises ValueError if no user exists with that id — callers (routes)
    should translate that into a 404.
    """
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise ValueError(f"No user found with id {user_id}")

    patient_info = await _build_patient_info(db, user)
    recent_chats = await _build_chat_history(db, user_id)
    reports = await _build_reports(db, user_id)
    prescriptions = await _build_prescriptions(db, user_id)
    clinical_sessions = await _build_clinical_sessions(db, user_id)

    has_any_data = bool(recent_chats or reports or prescriptions or clinical_sessions)

    return PatientContext(
        patient=patient_info,
        recent_chats=recent_chats,
        reports=reports,
        prescriptions=prescriptions,
        clinical_sessions=clinical_sessions,
        has_any_data=has_any_data,
    )


async def _build_patient_info(db: AsyncSession, user: User) -> PatientInfo:
    # A patient's own demographic data (DOB, gender, blood group, allergies,
    # medical history) lives on their "self" FamilyProfile row, not on User.
    profile_result = await db.execute(
        select(FamilyProfile)
        .where(FamilyProfile.user_id == user.id, FamilyProfile.relation == FamilyRelation.SELF)
        .order_by(FamilyProfile.created_at.desc())
    )
    self_profile = profile_result.scalars().first()

    age: int | str = NOT_PROVIDED
    gender = NOT_PROVIDED
    blood_group = NOT_PROVIDED
    allergies: list[str] = []
    medical_history: list[str] = []

    if self_profile is not None:
        if self_profile.date_of_birth is not None:
            today = datetime.now(timezone.utc)
            dob = self_profile.date_of_birth
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        gender = self_profile.gender or NOT_PROVIDED
        blood_group = self_profile.blood_group or NOT_PROVIDED
        allergies = list(self_profile.allergies or [])
        medical_history = list(self_profile.medical_history or [])

    return PatientInfo(
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone or NOT_PROVIDED,
        age=age,
        gender=gender,
        blood_group=blood_group,
        known_allergies=allergies,
        known_medical_history=medical_history,
    )


async def _build_chat_history(db: AsyncSession, user_id: uuid.UUID) -> list[ChatSessionSummary]:
    sessions_result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc())
        .limit(MAX_CHAT_SESSIONS)
    )
    sessions = sessions_result.scalars().all()

    summaries: list[ChatSessionSummary] = []
    for session in sessions:
        ordered_messages = sorted(session.messages, key=lambda m: m.created_at)
        trimmed = ordered_messages[-MAX_MESSAGES_PER_SESSION:]
        summaries.append(
            ChatSessionSummary(
                session_id=session.id,
                language=session.language,
                updated_at=session.updated_at,
                messages=[
                    ChatTurn(role=m.role, content=m.content, created_at=m.created_at)
                    for m in trimmed
                ],
            )
        )
    return summaries


async def _build_reports(db: AsyncSession, user_id: uuid.UUID) -> list[OCRDocument]:
    reports_result = await db.execute(
        select(MedicalReport)
        .where(MedicalReport.user_id == user_id)
        .order_by(MedicalReport.created_at.desc())
        .limit(MAX_REPORTS)
    )
    reports = reports_result.scalars().all()

    return [
        OCRDocument(
            report_id=r.id,
            title=r.title,
            report_type=r.report_type,
            ocr_text=r.ocr_text,
            findings=r.analysis,
            risk_level=r.risk_level or NOT_PROVIDED,
            created_at=r.created_at,
        )
        for r in reports
    ]


async def _build_prescriptions(db: AsyncSession, user_id: uuid.UUID) -> list[PrescriptionSummary]:
    prescriptions_result = await db.execute(
        select(Prescription)
        .where(Prescription.user_id == user_id)
        .order_by(Prescription.created_at.desc())
        .limit(MAX_PRESCRIPTIONS)
    )
    prescriptions = prescriptions_result.scalars().all()

    return [
        PrescriptionSummary(
            prescription_id=p.id,
            doctor_name=p.doctor_name or NOT_PROVIDED,
            medicines=list(p.medicines or []),
            created_at=p.created_at,
        )
        for p in prescriptions
    ]


MAX_CLINICAL_SESSIONS = 3


async def _build_clinical_sessions(db: AsyncSession, user_id: uuid.UUID) -> list[ClinicalSessionSummary]:
    sessions_result = await db.execute(
        select(ClinicalSession)
        .options(selectinload(ClinicalSession.red_flags))
        .where(ClinicalSession.user_id == user_id)
        .order_by(ClinicalSession.created_at.desc())
        .limit(MAX_CLINICAL_SESSIONS)
    )
    sessions = sessions_result.scalars().all()

    return [
        ClinicalSessionSummary(
            session_id=s.id,
            status=s.status.value if hasattr(s.status, "value") else str(s.status),
            chief_complaint=s.chief_complaint or NOT_PROVIDED,
            collected_fields=dict(s.collected_fields or {}),
            red_flags=[
                RedFlagSummary(
                    alert_id=rf.id,
                    severity=rf.severity.value if hasattr(rf.severity, "value") else str(rf.severity),
                    detected_symptoms=list(rf.detected_symptoms or []),
                    reason=rf.reason,
                    recommended_action=rf.recommended_action,
                    source=rf.source.value if hasattr(rf.source, "value") else str(rf.source),
                    acknowledged=rf.acknowledged,
                    acknowledged_at=rf.acknowledged_at,
                    created_at=rf.created_at,
                )
                for rf in s.red_flags
            ],
            created_at=s.created_at,
        )
        for s in sessions
    ]