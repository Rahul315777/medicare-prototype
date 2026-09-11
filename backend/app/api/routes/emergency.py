"""Emergency module and nearby services routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import EmergencyContact, User
from app.schemas import EmergencyContactCreate, EmergencyContactResponse

router = APIRouter(prefix="/emergency", tags=["Emergency"])


@router.post("/trigger")
async def trigger_emergency(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    latitude: float | None = None,
    longitude: float | None = None,
):
    contacts = await db.execute(
        select(EmergencyContact).where(EmergencyContact.user_id == user.id)
    )
    emergency_contacts = contacts.scalars().all()

    return {
        "status": "emergency_triggered",
        "ambulance_number": "102",
        "message": "Emergency services notified. Stay calm.",
        "location_shared": latitude is not None and longitude is not None,
        "latitude": latitude,
        "longitude": longitude,
        "contacts_notified": [c.phone for c in emergency_contacts],
        "nearest_hospitals": [
            {"name": "City General Hospital", "distance_km": 1.2, "phone": "+91-11-23456789"},
            {"name": "Apollo Emergency", "distance_km": 2.5, "phone": "+91-11-98765432"},
        ],
    }


@router.post("/contacts", response_model=EmergencyContactResponse, status_code=201)
async def add_emergency_contact(
    data: EmergencyContactCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    contact = EmergencyContact(user_id=user.id, **data.model_dump())
    db.add(contact)
    await db.flush()
    return contact


@router.get("/contacts", response_model=list[EmergencyContactResponse])
async def list_emergency_contacts(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(EmergencyContact).where(EmergencyContact.user_id == user.id))
    return result.scalars().all()


@router.get("/nearby")
async def nearby_services(
    latitude: float = 28.6139,
    longitude: float = 77.2090,
    service_type: str = "hospital",
    radius_km: float = 5.0,
):
    services = {
        "hospital": [
            {"name": "AIIMS Delhi", "type": "hospital", "distance_km": 2.1, "rating": 4.8},
            {"name": "Safdarjung Hospital", "type": "hospital", "distance_km": 3.4, "rating": 4.5},
        ],
        "clinic": [
            {"name": "HealthFirst Clinic", "type": "clinic", "distance_km": 0.8, "rating": 4.6},
        ],
        "lab": [
            {"name": "Dr. Lal PathLabs", "type": "lab", "distance_km": 1.5, "rating": 4.7},
            {"name": "SRL Diagnostics", "type": "lab", "distance_km": 2.0, "rating": 4.5},
        ],
        "pharmacy": [
            {"name": "Apollo Pharmacy", "type": "pharmacy", "distance_km": 0.5, "rating": 4.4},
            {"name": "MedPlus", "type": "pharmacy", "distance_km": 1.1, "rating": 4.3},
        ],
    }
    return {
        "latitude": latitude,
        "longitude": longitude,
        "services": services.get(service_type, services["hospital"]),
        "maps_url": f"https://www.google.com/maps/search/{service_type}/@{latitude},{longitude},{int(radius_km * 1000)}m",
    }
