"""
MediCare AI - Smart Auto-Scanning Engine (PDF + Images + X-Ray Vision)
"""

import base64
import io
import json
import logging
import os
from typing import Any
from PIL import Image
import httpx

from groq import Groq
from app.core.config import settings

logger = logging.getLogger(__name__)

groq_client = Groq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None
if groq_client is None:
    logger.warning("GROQ_API_KEY is not set - medical report/vision analysis will run in degraded mode.")

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")


async def fetch_real_doctors(specialty: str, location: str = "India") -> list:
    """Google Places API se real doctors fetch karta hai, fail hone par mock data deta hai"""
    
    # 🚨 FALLBACK: Agar Google API fail ho jaye (jaise billing ka issue ho) toh yeh Dummy data jayega
    def get_mock_doctors(spec):
        return [
            {"name": f"Dr. R.K. Sharma", "address": f"City Care Hospital, {location}", "rating": "4.8/5", "status": "Available", "specialty": spec},
            {"name": f"Dr. Neha Gupta", "address": f"Apollo Clinic, Sector 14, {location}", "rating": "4.6/5", "status": "Available", "specialty": spec}
        ]

    if not GOOGLE_MAPS_API_KEY:
        logger.warning("GOOGLE_MAPS_API_KEY is missing. Using fallback doctors.")
        return get_mock_doctors(specialty)
        
    query = f"{specialty} doctors in {location}"
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={query}&key={GOOGLE_MAPS_API_KEY}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            data = response.json()
            
        # Agar Google Billing error de ya list khali ho
        if "error_message" in data or not data.get("results"):
            logger.error(f"Google Maps blocked the request (Billing/API issue). Using fallback.")
            return get_mock_doctors(specialty)

        doctors = []
        for place in data.get("results", [])[:4]: # Top 4 real doctors
            doctors.append({
                "id": place.get("place_id"),
                "name": place.get("name"),
                "address": place.get("formatted_address"),
                "rating": str(place.get("rating", "N/A")) + "/5",
                "status": "Available" if place.get("business_status") == "OPERATIONAL" else "Unknown",
                "specialty": specialty
            })
        return doctors
    except Exception as e:
        logger.error(f"Google Maps HTTP Error: {e}")
        return get_mock_doctors(specialty)


def extract_ocr_text(file_content: bytes, filename: str) -> str:
    """Safely extracts text from PDFs or text documents."""
    try:
        if filename and filename.lower().endswith(".pdf"):
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(file_content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            if text.strip():
                return text
        else:
            import pytesseract
            
            # Agar Windows par tesseract ka path set karna pade
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

            image = Image.open(io.BytesIO(file_content))
            return pytesseract.image_to_string(image)
    except FileNotFoundError as e:
        logger.error(f"Tesseract OCR is not installed on your system! Error: {e}")
        return "ERROR_TESSERACT_MISSING"
    except Exception as exc:
        logger.warning(f"OCR processing fallback for {filename}: {exc}")
    return ""


async def analyze_medical_report(
    ocr_text: str, 
    report_type: str, 
    file_bytes: bytes = None, 
    filename: str = ""
) -> dict[str, Any]:
    
    clean_filename = (filename or "").lower().strip()
    clean_type = (report_type or "").lower().strip()

    is_image_file = clean_filename.endswith((".png", ".jpg", ".jpeg", ".webp"))
    is_imaging_scan = any(tag in clean_type for tag in ["xray", "x-ray", "mri", "ct", "ecg", "scan"])
    has_readable_text = ocr_text and len(ocr_text.strip()) >= 20 and ocr_text != "ERROR_TESSERACT_MISSING"

    if is_imaging_scan and not has_readable_text:
         return {
            "summary": "⚠️ AI VISION ANALYSIS UNAVAILABLE: The vision model has been decommissioned by the provider.",
            "explanation": "Please upload a clear blood report or PDF containing readable text.",
            "risk_level": "low",
            "values": [],
         }

    if ocr_text == "ERROR_TESSERACT_MISSING":
         return {
            "summary": "⚠️ OCR SOFTWARE MISSING: Tesseract OCR is not installed on your system.",
            "explanation": "To scan images for text, please install Tesseract OCR on your Windows machine and restart the server.",
            "risk_level": "low",
            "values": []
        }

    if not has_readable_text:
        return {
            "summary": "⚠️ UNREADABLE DOCUMENT: The uploaded file appears empty or unreadable.",
            "explanation": "No readable clinical text detected by Tesseract OCR.",
            "risk_level": "high",
            "values": []
        }

    text_system_prompt = """You are MediCare AI, a strict Clinical Diagnostician and Medical Report Analyzer.
You MUST output ONLY a valid JSON object. Do NOT include markdown blocks like ```json or ```. 
Do NOT output any extra text before or after the JSON.

CRITICAL RULES:
1. You MUST populate the "values" array by extracting every single test name, its numeric result, and its unit from the provided OCR text. DO NOT LEAVE IT EMPTY if there is data.
2. You MUST write a detailed "explanation" identifying the likely disease/condition (e.g., Diabetes, Infection).
3. You MUST provide a "recommended_specialty" based on the results (e.g., 'Cardiologist', 'Endocrinologist', 'General Physician').

JSON STRUCTURE:
{
  "is_valid_medical_doc": true,
  "summary": "Clear 3-sentence summary of the health status.",
  "explanation": "Detailed interpretation identifying the likely disease/condition.",
  "risk_level": "low",
  "recommended_specialty": "Endocrinologist",
  "values": [
    {"name": "HbA1c", "value": "5.0", "unit": "%"}
  ]
}"""

    try:
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b", 
            messages=[
                {"role": "system", "content": text_system_prompt},
                {
                    "role": "user",
                    "content": f"Analyze this medical document (claimed type: {report_type}):\n\n--- BEGIN TEXT ---\n{ocr_text[:3500]}\n--- END TEXT ---"
                }
            ],
            temperature=0.1,
            max_tokens=2000,
        )
        
        raw_response = response.choices[0].message.content.strip()
        
        # Additional safety check to parse the JSON string properly
        try:
             if raw_response.startswith("```json"):
                 raw_response = raw_response.split("```json")[1].split("```")[0].strip()
             elif raw_response.startswith("```"):
                 raw_response = raw_response.split("```")[1].split("```")[0].strip()
                 
             data = json.loads(raw_response)
        except json.JSONDecodeError:
             logger.error(f"Failed to parse model output as JSON: {raw_response}")
             data = {} # fallback

        if not data.get("is_valid_medical_doc", True):
            return {
                "summary": "🚨 INVALID / NON-MEDICAL DOCUMENT. Please upload a valid clinical record.",
                "explanation": "Document content is unrelated to medical diagnostics.",
                "risk_level": "high",
                "values": [],
            }

        # ✅ Google Maps API call to fetch doctors based on AI's recommendation
        specialty = data.get("recommended_specialty", "General Physician")
        real_doctors = await fetch_real_doctors(specialty, "India") 

        return {
            "summary": data.get("summary", "Medical report analyzed successfully."),
            "explanation": data.get("explanation", ""),
            "risk_level": data.get("risk_level", "low"),
            "values": data.get("values", []),
            "recommended_specialty": specialty,
            "real_doctors": real_doctors  # 👈 Doctor data frontend ko bheja ja raha hai
        }

    except Exception as exc:
        logger.error(f"Text Analyzer Error: {exc}")
        return {
            "summary": f"⚠️ Document Analyzer Error: {str(exc)}",
            "explanation": "Groq API failed to process the text.",
            "risk_level": "low",
            "values": []
        }


# ==========================================================
# OTHER AI SERVICES (Prescription, Nutrition, Risks, etc.)
# ==========================================================

async def scan_prescription(ocr_text: str) -> dict[str, Any]:
    return _mock_prescription()

async def analyze_food_image(description: str) -> dict[str, Any]:
    return {
        "food_name": "Mixed meal",
        "calories": 450,
        "protein": 25,
        "carbs": 55,
        "fat": 15,
        "healthy_alternatives": ["Grilled chicken salad", "Steamed vegetables"],
    }

async def predict_health_risks(metrics: dict[str, float], history: list[dict]) -> dict[str, Any]:
    bmi = metrics.get("bmi", 22)
    sugar = metrics.get("sugar", 90)
    systolic = metrics.get("systolic_bp", 120)
    age = metrics.get("age", 35)

    diabetes_risk = min(95, max(5, (sugar - 70) * 0.5 + (bmi - 22) * 2 + (age - 30) * 0.3))
    heart_risk = min(95, max(5, (systolic - 110) * 0.8 + (bmi - 22) * 1.5 + (age - 30) * 0.5))
    hypertension_risk = min(95, max(5, (systolic - 115) * 1.2 + (age - 30) * 0.4))

    factors = []
    if bmi > 25: factors.append("Elevated BMI")
    if sugar > 100: factors.append("Elevated blood sugar")
    if systolic > 130: factors.append("Elevated blood pressure")

    return {
        "diabetes_risk": round(diabetes_risk, 1),
        "heart_disease_risk": round(heart_risk, 1),
        "hypertension_risk": round(hypertension_risk, 1),
        "factors": factors or ["No major major risk factors identified"],
        "recommendations": [
            "Maintain regular exercise (150 min/week)",
            "Follow a balanced diet low in processed foods",
            "Schedule annual health checkups"
        ],
    }

async def analyze_consultation(transcript: str) -> dict[str, Any]:
    return _mock_call_analysis()

async def get_medicine_info(name: str) -> dict[str, Any]:
    return {"name": name, "uses": ["Consult doctor"], "dosage": "As prescribed", "side_effects": ["Varies"], "warnings": ["Take as directed"], "pregnancy": "Consult doctor", "children": "Consult doctor", "interactions": ["Unknown"]}

async def get_disease_info(name: str) -> dict[str, Any]:
    return {"name": name, "causes": ["Consult doctor"], "symptoms": ["Varies"], "prevention": ["Healthy lifestyle"], "treatment": ["Medical consultation required"], "lifestyle": ["Healthy habits"], "diet": ["Balanced diet"], "exercise": ["Regular activity"]}

def _mock_prescription() -> dict[str, Any]:
    return {"doctor_name": "Dr. Sharma", "medicines": [{"name": "Paracetamol", "dosage": "500mg", "timing": "Twice daily", "duration_days": 5}]}

def _mock_call_analysis() -> dict[str, Any]:
    return {"summary": "Patient presented with mild fever.", "symptoms": ["Fever"], "medicines": [], "follow_up": "Return if fever persists", "suggested_tests": [], "doctor_instructions": ["Rest"]}


# ==========================================================
# CLINICAL SUMMARY (Phase 4)
# ==========================================================

CLINICAL_SUMMARY_SYSTEM_PROMPT = """You are MediCare AI, generating a structured clinical summary for a doctor
from a patient's chat history, uploaded report findings, and prescriptions.

You MUST output ONLY a valid JSON object with EXACTLY these keys:
{
  "chief_complaints": "string",
  "symptoms": ["string"],
  "medical_history": "string",
  "medications": ["string"],
  "allergies": "string",
  "reports": "string",
  "important_findings": "string"
}

CRITICAL RULES:
1. Use ONLY the information given in the PATIENT CONTEXT below. NEVER invent, assume, or guess a
   symptom, diagnosis, medication, or result that isn't explicitly present.
2. If a section has no information in the provided context, its value MUST be the literal string
   "Not provided" (or an empty list [] for the "symptoms"/"medications" fields).
3. Do NOT provide a diagnosis or suggest a treatment plan — only summarize what is documented.
4. Do NOT include markdown, code fences, or any text outside the JSON object.
"""

_SUMMARY_FALLBACK: dict[str, Any] = {
    "chief_complaints": "Not provided",
    "symptoms": [],
    "medical_history": "Not provided",
    "medications": [],
    "allergies": "Not provided",
    "reports": "Not provided",
    "important_findings": "Not provided",
}


async def generate_clinical_summary(context_text: str) -> dict[str, Any]:
    """Turn a PatientContext.to_prompt_text() block (see app/services/patient_context.py)
    into a structured clinical summary via Groq. Pure summarization of existing
    data — never invents a symptom, diagnosis, or result that wasn't provided."""
    if groq_client is None:
        logger.warning("GROQ_API_KEY missing — returning empty clinical summary.")
        return dict(_SUMMARY_FALLBACK)

    try:
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": CLINICAL_SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": f"PATIENT CONTEXT:\n\n{context_text}"},
            ],
            temperature=0.1,
            max_tokens=800,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```json"):
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif raw.startswith("```"):
            raw = raw.split("```")[1].split("```")[0].strip()
        data = json.loads(raw)
    except Exception as exc:
        logger.error(f"Clinical summary generation failed: {exc}")
        return dict(_SUMMARY_FALLBACK)

    return {
        "chief_complaints": data.get("chief_complaints", "Not provided"),
        "symptoms": data.get("symptoms", []),
        "medical_history": data.get("medical_history", "Not provided"),
        "medications": data.get("medications", []),
        "allergies": data.get("allergies", "Not provided"),
        "reports": data.get("reports", "Not provided"),
        "important_findings": data.get("important_findings", "Not provided"),
    }