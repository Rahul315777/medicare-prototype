"""Admin panel routes for managing users, doctors, appointments, and analytics."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_admin_user
from app.models import Appointment, Doctor, MedicalReport, User
from app.schemas import UserResponse

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/analytics")
async def get_analytics(
    admin: Annotated[User, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    users_count = await db.execute(select(func.count(User.id)))
    doctors_count = await db.execute(select(func.count(Doctor.id)))
    appointments_count = await db.execute(select(func.count(Appointment.id)))
    reports_count = await db.execute(select(func.count(MedicalReport.id)))

    return {
        "total_users": users_count.scalar() or 0,
        "total_doctors": doctors_count.scalar() or 0,
        "total_appointments": appointments_count.scalar() or 0,
        "total_reports": reports_count.scalar() or 0,
        "revenue": {"total": 125000, "currency": "INR", "period": "monthly"},
    }


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    admin: Annotated[User, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 50,
):
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/appointments")
async def list_all_appointments(
    admin: Annotated[User, Depends(get_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 50,
):
    result = await db.execute(select(Appointment).offset(skip).limit(limit))
    return result.scalars().all()
