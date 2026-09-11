"""Dashboard, health metrics, and family profile routes."""

from datetime import datetime, timezone
import random
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import (
    Appointment,
    AppointmentStatus,
    Doctor,
    FamilyProfile,
    HealthMetric,
    MedicalReport,
    MedicineReminder,
    User,
)
from app.schemas import (
    DashboardResponse,
    FamilyProfileCreate,
    FamilyProfileResponse,
    HealthMetricCreate,
    HealthMetricResponse,
)

router = APIRouter(tags=["Dashboard & Health"])

DAILY_TIPS = [
    "Drink at least 8 glasses of water today for optimal hydration.",
    "Take a 10-minute walk after meals to help regulate blood sugar.",
    "Practice deep breathing for 5 minutes to reduce stress levels.",
    "Include colorful vegetables in every meal for essential nutrients.",
    "Aim for 7-8 hours of quality sleep tonight.",
]


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    now = datetime.now(timezone.utc)

    appts = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.doctor))
        .where(Appointment.patient_id == user.id, Appointment.status == AppointmentStatus.SCHEDULED)
        .order_by(Appointment.scheduled_at)
        .limit(5)
    )
    appointments = appts.scalars().all()

    reminders = await db.execute(
        select(MedicineReminder)
        .where(MedicineReminder.user_id == user.id, MedicineReminder.is_active == True)  # noqa: E712
        .limit(5)
    )

    reports = await db.execute(
        select(MedicalReport)
        .where(MedicalReport.user_id == user.id)
        .order_by(MedicalReport.created_at.desc())
        .limit(3)
    )

    doctors = await db.execute(select(Doctor).order_by(Doctor.rating.desc()).limit(4))

    tip = random.choice(DAILY_TIPS)

    return DashboardResponse(
        health_score=user.health_score,
        upcoming_appointments=appointments,
        medicine_reminders=[
            {"id": str(r.id), "medicine_name": r.medicine_name, "timing": r.timing, "dosage": r.dosage}
            for r in reminders.scalars().all()
        ],
        recent_reports=reports.scalars().all(),
        daily_tip=tip,
        recommended_doctors=doctors.scalars().all(),
    )


@router.post("/health-metrics", response_model=HealthMetricResponse, status_code=201)
async def add_health_metric(
    data: HealthMetricCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    metric = HealthMetric(user_id=user.id, **data.model_dump())
    db.add(metric)
    await db.flush()
    return metric


@router.get("/health-metrics", response_model=list[HealthMetricResponse])
async def get_health_metrics(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    metric_type: str | None = None,
    limit: int = 50,
):
    query = select(HealthMetric).where(HealthMetric.user_id == user.id)
    if metric_type:
        query = query.where(HealthMetric.metric_type == metric_type)
    query = query.order_by(HealthMetric.recorded_at.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/family-profiles", response_model=FamilyProfileResponse, status_code=201)
async def create_family_profile(
    data: FamilyProfileCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    profile = FamilyProfile(user_id=user.id, **data.model_dump())
    db.add(profile)
    await db.flush()
    return profile


@router.get("/family-profiles", response_model=list[FamilyProfileResponse])
async def list_family_profiles(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(FamilyProfile).where(FamilyProfile.user_id == user.id))
    return result.scalars().all()
