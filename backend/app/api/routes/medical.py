"""Medical reports, prescriptions, medicine/disease knowledge, nutrition, risk prediction."""

import io
import logging
import uuid
from datetime import datetime
from typing import Annotated, Any, Dict, List

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, Body
import pypdf
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.ai.memory import memory_service
from app.ai.services import (
    analyze_consultation,
    analyze_food_image,
    analyze_medical_report,
    extract_ocr_text,
    get_disease_info,
    get_medicine_info,
    predict_health_risks,
    scan_prescription,
    fetch_real_doctors,  # 👈 NAYA IMPORT GOOGLE MAPS KE LIYE
)
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import HealthMetric, MedicalReport, MedicineReminder, Prescription, User
from app.schemas import (
    DiseaseInfo,
    MedicineInfo,
    NutritionAnalysis,
    PrescriptionResponse,
    ReportAnalysisResponse,
    RiskPredictionResponse,
)
from app.services.storage import save_upload

router = APIRouter(tags=["Medical Analysis"])

@router.post("/reports/analyze", response_model=ReportAnalysisResponse, status_code=201)
async def analyze_report(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    report_type: str = Form("blood"),
    title: str = Form("Medical Report"),
    lat: float | None = None,  # 👈 NAYA: User ka Latitude aayega yahan
    lng: float | None = None,  # 👈 NAYA: User ka Longitude aayega yahan
):
    """
    Scans real OCR/document text OR Images using Groq Llama-3 & Vision AI.
    """
    file_url = await save_upload(file, "reports")
    
    # Yahan cursor wapas 0 par laya gaya hai taaki AI khali file na padhe
    await file.seek(0)
    
    file_bytes = await file.read()
    filename = file.filename or "report.png"

    # 1. Try OCR text extraction for PDFs or normal documents
    ocr_text = ""
    try:
        if filename.lower().endswith(".pdf"):
            pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    ocr_text += page_text + "\n"
        else:
            ocr_text = extract_ocr_text(file_bytes, filename)
    except Exception as e:
        logger.error("OCR Extraction failed for %s: %s", filename, str(e))
        # Fallback block
        try:
            ocr_text = extract_ocr_text(file_bytes, filename)
        except Exception as fallback_err:
            logger.error("Fallback OCR failed: %s", str(fallback_err))
            ocr_text = ""

    # 2. Analyze Report via AI
    try:
        analysis = await analyze_medical_report(
            ocr_text=ocr_text,
            report_type=report_type,
            file_bytes=file_bytes,
            filename=filename,
        )
        
        # 👈 NAYA LOGIC: Agar location hai, toh Exact aaspas ke doctors layenge
        if lat and lng and isinstance(analysis, dict):
            specialty = analysis.get("recommended_specialty", "General Physician")
            location_str = f"{lat},{lng}"
            # services.py ko hum ye actual location pass kar denge
            analysis["real_doctors"] = await fetch_real_doctors(specialty, location_str)

    except Exception as e:
        logger.error("AI Analysis failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"AI API/Model Error: {str(e)}")

    report = MedicalReport(
        user_id=user.id,
        title=title if title != "Medical Report" else filename,
        report_type=report_type,
        file_url=file_url,
        ocr_text=ocr_text,
        analysis=analysis,
        risk_level=analysis.get("risk_level", "low"),
    )
    db.add(report)
    await db.flush()

    # Feed this report into the patient's long-term FAISS memory
    try:
        await memory_service.remember_report(
            user_id=str(user.id),
            report_id=str(report.id),
            title=report.title,
            summary=analysis.get("summary", ""),
            risk_level=report.risk_level or "low",
        )
    except Exception:
        logger.warning("Failed to persist report %s to long-term memory", report.id, exc_info=True)

    return report


@router.get("/reports", response_model=list[ReportAnalysisResponse])
async def list_reports(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(MedicalReport)
        .where(MedicalReport.user_id == user.id)
        .order_by(MedicalReport.created_at.desc())
    )
    return result.scalars().all()


@router.post("/prescriptions/scan", response_model=PrescriptionResponse, status_code=201)
async def scan_prescription_route(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
):
    file_url = await save_upload(file, "prescriptions")
    
    await file.seek(0)
    content = await file.read()
    filename = file.filename or "rx.jpg"
    
    try:
        ocr_text = extract_ocr_text(content, filename)
    except Exception as e:
        logger.error("Prescription OCR Error: %s", str(e))
        ocr_text = ""
        
    parsed = await scan_prescription(ocr_text)

    prescription = Prescription(
        user_id=user.id,
        image_url=file_url,
        medicines=parsed.get("medicines", []),
        doctor_name=parsed.get("doctor_name"),
    )
    db.add(prescription)

    for med in parsed.get("medicines", []):
        reminder = MedicineReminder(
            user_id=user.id,
            medicine_name=med.get("name", "Unknown"),
            dosage=med.get("dosage", "As directed"),
            timing=med.get("timing", "Daily"),
            duration_days=med.get("duration_days", 7),
        )
        db.add(reminder)

    await db.flush()

    try:
        await memory_service.remember_prescription(
            user_id=str(user.id),
            prescription_id=str(prescription.id),
            doctor_name=prescription.doctor_name,
            medicines=parsed.get("medicines", []),
        )
    except Exception:
        logger.warning("Failed to persist prescription %s to long-term memory", prescription.id, exc_info=True)

    return prescription


@router.get("/medicines/{name}", response_model=MedicineInfo)
async def medicine_knowledge(name: str):
    return await get_medicine_info(name)


@router.get("/diseases/{name}", response_model=DiseaseInfo)
async def disease_knowledge(name: str):
    return await get_disease_info(name)


@router.post("/nutrition/analyze", response_model=NutritionAnalysis)
async def analyze_nutrition(
    user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    await file.seek(0)
    content = await file.read()
    description = f"Food image uploaded, size: {len(content)} bytes"
    return await analyze_food_image(description)


@router.get("/risk-prediction", response_model=RiskPredictionResponse)
async def health_risk_prediction(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(HealthMetric).where(HealthMetric.user_id == user.id))
    metrics_list = result.scalars().all()
    metrics = {m.metric_type: m.value for m in metrics_list}
    
    # Default values logic
    metrics.setdefault("bmi", 23)
    metrics.setdefault("sugar", 95)
    metrics.setdefault("systolic_bp", 120)
    metrics.setdefault("age", 35)

    prediction = await predict_health_risks(metrics, [])
    return RiskPredictionResponse(**prediction)


@router.post("/consultations/analyze")
async def analyze_call(
    user: Annotated[User, Depends(get_current_user)],
    transcript: Annotated[str, Body(..., description="The consultation transcript text")],
):
    return await analyze_consultation(transcript)