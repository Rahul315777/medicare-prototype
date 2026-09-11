"""Doctor listing, search, and appointment booking routes."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.memory import memory_service
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Appointment, AppointmentStatus, Doctor, User
from app.schemas import AppointmentCreate, AppointmentResponse, DoctorResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Doctors & Appointments"])

SAMPLE_DOCTORS = [
    {"name": "Dr. Priya Sharma", "specialty": "General Physician", "experience_years": 12, "rating": 4.8, "hospital": "Apollo Hospital"},
    {"name": "Dr. Rajesh Kumar", "specialty": "Cardiologist", "experience_years": 18, "rating": 4.9, "hospital": "Fortis Healthcare"},
    {"name": "Dr. Ananya Patel", "specialty": "Dermatologist", "experience_years": 8, "rating": 4.7, "hospital": "Max Hospital"},
    {"name": "Dr. Vikram Singh", "specialty": "Orthopedic", "experience_years": 15, "rating": 4.6, "hospital": "AIIMS Delhi"},
    {"name": "Dr. Meera Reddy", "specialty": "Pediatrician", "experience_years": 10, "rating": 4.8, "hospital": "Rainbow Hospital"},
    {"name": "Dr. Arjun Mehta", "specialty": "Neurologist", "experience_years": 20, "rating": 4.9, "hospital": "Medanta"},
]


async def seed_doctors(db: AsyncSession) -> None:
    count = await db.execute(select(Doctor).limit(1))
    if count.scalar_one_or_none():
        return
    for d in SAMPLE_DOCTORS:
        db.add(Doctor(**d, is_online=True, consultation_fee=500.0))
    await db.flush()


@router.get("/doctors", response_model=list[DoctorResponse])
async def list_doctors(
    db: Annotated[AsyncSession, Depends(get_db)],
    specialty: str | None = None,
    search: str | None = None,
    online_only: bool = False,
    min_rating: float = 0,
    skip: int = 0,
    limit: int = 20,
):
    await seed_doctors(db)
    query = select(Doctor).where(Doctor.rating >= min_rating)
    if specialty:
        query = query.where(Doctor.specialty.ilike(f"%{specialty}%"))
    if search:
        query = query.where(or_(Doctor.name.ilike(f"%{search}%"), Doctor.specialty.ilike(f"%{search}%")))
    if online_only:
        query = query.where(Doctor.is_online == True)  # noqa: E712
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/doctors/{doctor_id}", response_model=DoctorResponse)
async def get_doctor(doctor_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor


@router.post("/appointments", response_model=AppointmentResponse, status_code=201)
async def book_appointment(
    data: AppointmentCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    doctor = await db.execute(select(Doctor).where(Doctor.id == data.doctor_id))
    if not doctor.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Doctor not found")

    appointment = Appointment(
        patient_id=user.id,
        doctor_id=data.doctor_id,
        scheduled_at=data.scheduled_at,
        notes=data.notes,
        meeting_url=f"/consultation/{uuid.uuid4()}",
    )
    db.add(appointment)
    await db.flush()

    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.doctor))
        .where(Appointment.id == appointment.id)
    )
    saved = result.scalar_one()

    try:
        await memory_service.remember_appointment(
            user_id=str(user.id),
            appointment_id=str(saved.id),
            doctor_name=saved.doctor.name,
            specialty=saved.doctor.specialty,
            scheduled_at=saved.scheduled_at.isoformat(),
            notes=saved.notes,
        )
    except Exception:
        logger.warning("Failed to persist appointment %s to long-term memory", saved.id, exc_info=True)

    return saved


@router.get("/appointments", response_model=list[AppointmentResponse])
async def list_appointments(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: AppointmentStatus | None = None,
):
    query = (
        select(Appointment)
        .options(selectinload(Appointment.doctor))
        .where(Appointment.patient_id == user.id)
        .order_by(Appointment.scheduled_at.desc())
    )
    if status_filter:
        query = query.where(Appointment.status == status_filter)
    result = await db.execute(query)
    return result.scalars().all()


@router.patch("/appointments/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id, Appointment.patient_id == user.id)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    appointment.status = AppointmentStatus.CANCELLED
    return {"message": "Appointment cancelled"}
