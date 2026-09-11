"""Pydantic schemas for request/response validation."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from app.models import AppointmentStatus, FamilyRelation, UserRole


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2)
    phone: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class OTPVerify(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)


class ForgotPassword(BaseModel):
    email: EmailStr


class ResetPassword(BaseModel):
    email: EmailStr
    otp: str
    new_password: str = Field(min_length=8)


class GoogleAuth(BaseModel):
    id_token: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    avatar_url: str | None
    role: UserRole
    is_verified: bool
    health_score: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Health Metrics ────────────────────────────────────────────────────────────

class HealthMetricCreate(BaseModel):
    metric_type: str
    value: float
    unit: str
    notes: str | None = None


class HealthMetricResponse(BaseModel):
    id: uuid.UUID
    metric_type: str
    value: float
    unit: str
    recorded_at: datetime
    notes: str | None

    model_config = {"from_attributes": True}


# ── Doctors & Appointments ────────────────────────────────────────────────────

class DoctorResponse(BaseModel):
    id: uuid.UUID
    name: str
    specialty: str
    experience_years: int
    rating: float
    consultation_fee: float
    is_online: bool
    bio: str | None
    avatar_url: str | None
    hospital: str | None
    languages: list | None

    model_config = {"from_attributes": True}


class AppointmentCreate(BaseModel):
    doctor_id: uuid.UUID
    scheduled_at: datetime
    notes: str | None = None


class AppointmentResponse(BaseModel):
    id: uuid.UUID
    doctor_id: uuid.UUID
    scheduled_at: datetime
    status: AppointmentStatus
    notes: str | None
    meeting_url: str | None
    call_summary: dict | None
    created_at: datetime
    doctor: DoctorResponse | None = None

    model_config = {"from_attributes": True}


# ── AI Chat ───────────────────────────────────────────────────────────────────

class ChatMessageCreate(BaseModel):
    content: str
    language: str = "en"


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    confidence: float | None
    sources: list | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionResponse(BaseModel):
    id: uuid.UUID
    title: str
    language: str
    created_at: datetime
    messages: list[ChatMessageResponse] = []

    model_config = {"from_attributes": True}


# ── Reports & Prescriptions ───────────────────────────────────────────────────

class ReportAnalysisResponse(BaseModel):
    id: uuid.UUID
    title: str
    report_type: str
    file_url: str
    analysis: dict | None
    risk_level: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PrescriptionResponse(BaseModel):
    id: uuid.UUID
    medicines: list | None
    doctor_name: str | None
    image_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Family Profiles ───────────────────────────────────────────────────────────

class FamilyProfileCreate(BaseModel):
    name: str
    relation: FamilyRelation
    date_of_birth: datetime | None = None
    gender: str | None = None
    blood_group: str | None = None
    allergies: list[str] = []
    medical_history: list[str] = []


class FamilyProfileResponse(BaseModel):
    id: uuid.UUID
    name: str
    relation: FamilyRelation
    date_of_birth: datetime | None
    gender: str | None
    blood_group: str | None
    allergies: list | None
    medical_history: list | None

    model_config = {"from_attributes": True}


# ── Medicine & Disease Knowledge ──────────────────────────────────────────────

class MedicineInfo(BaseModel):
    name: str
    uses: list[str]
    dosage: str
    side_effects: list[str]
    warnings: list[str]
    pregnancy: str
    children: str
    interactions: list[str]


class DiseaseInfo(BaseModel):
    name: str
    causes: list[str]
    symptoms: list[str]
    prevention: list[str]
    treatment: list[str]
    lifestyle: list[str]
    diet: list[str]
    exercise: list[str]


# ── Risk Prediction ───────────────────────────────────────────────────────────

class RiskPredictionResponse(BaseModel):
    diabetes_risk: float
    heart_disease_risk: float
    hypertension_risk: float
    factors: list[str]
    recommendations: list[str]


# ── Nutrition ─────────────────────────────────────────────────────────────────

class NutritionAnalysis(BaseModel):
    food_name: str
    calories: float
    protein: float
    carbs: float
    fat: float
    healthy_alternatives: list[str]


# ── Emergency ─────────────────────────────────────────────────────────────────

class EmergencyContactCreate(BaseModel):
    name: str
    phone: str
    relation: str
    is_primary: bool = False


class EmergencyContactResponse(BaseModel):
    id: uuid.UUID
    name: str
    phone: str
    relation: str
    is_primary: bool

    model_config = {"from_attributes": True}


# ── Dashboard ─────────────────────────────────────────────────────────────────

class DashboardResponse(BaseModel):
    health_score: int
    upcoming_appointments: list[AppointmentResponse]
    medicine_reminders: list[dict[str, Any]]
    recent_reports: list[ReportAnalysisResponse]
    daily_tip: str
    recommended_doctors: list[DoctorResponse]
