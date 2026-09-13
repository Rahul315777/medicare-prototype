"""
AI Clinical Case-Taking Engine (Phase 1/2)
===========================================

Two responsibilities, kept in one module because they share the same
"never invent, never diagnose" safety rules and the same Groq client:

1. Adaptive question generation — given a chief complaint and the answers
   collected so far, decide the next relevant clinical-history question
   (or that enough has been collected).
2. Red-flag detection — a fast deterministic keyword layer (Layer 1) plus
   an optional Groq classifier (Layer 2) that flags patient answers which
   may need urgent attention. This is a TRIAGE SIGNAL, not a diagnosis.

Both layers are deterministic-first by design: the question sequence and
the keyword rules work with zero network calls, so the interview and the
safety-critical red-flag layer keep functioning (and stay unit-testable)
even when GROQ_API_KEY isn't configured. Groq, when available, only
sharpens phrasing/severity — it never gates whether the feature works.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.ai.services import groq_client

logger = logging.getLogger(__name__)

NOT_PROVIDED = "unknown/not provided"


# ==========================================================
# 1. ADAPTIVE QUESTION BANK (deterministic core)
# ==========================================================
# Each entry: (field, prompt, question_type, options)
# Order matters — earlier fields are asked first. The engine simply skips
# any field already present in collected_fields, so it never re-asks and
# never forces every question on every patient.

_GENERIC_BANK: list[tuple[str, str, str, list[str] | None]] = [
    ("onset", "When did this start?", "text", None),
    ("duration", "How long has it been going on?", "text", None),
    ("severity", "On a scale of 1-10, how severe is it?", "scale", None),
    ("location", "Where exactly do you feel it?", "text", None),
    ("character", "How would you describe it (e.g. sharp, dull, burning, throbbing)?", "text", None),
    ("aggravating_factors", "Does anything make it worse?", "text", None),
    ("relieving_factors", "Does anything make it better?", "text", None),
    ("associated_symptoms", "Are you having any other symptoms along with this?", "text", None),
    ("past_medical_history", "Do you have any ongoing medical conditions (e.g. diabetes, BP, asthma)?", "text", None),
    ("medications", "Are you currently taking any medications?", "text", None),
    ("allergies", "Do you have any known drug allergies?", "text", None),
    ("family_history", "Does this condition run in your family?", "text", None),
    ("personal_history", "Do you smoke, drink alcohol, or use tobacco?", "choice", ["Yes", "No", "Prefer not to say"]),
]

_HEADACHE_BANK: list[tuple[str, str, str, list[str] | None]] = [
    ("onset", "When did the headache start?", "text", None),
    ("duration", "Is it constant, or does it come and go?", "choice", ["Constant", "Comes and goes"]),
    ("severity", "On a scale of 1-10, how severe is the pain?", "scale", None),
    ("location", "Where is the pain located (one side, both sides, back of head, forehead)?", "text", None),
    ("associated_symptoms", "Any nausea, vomiting, sensitivity to light, or vision changes?", "text", None),
    ("aggravating_factors", "Does light, noise, or movement make it worse?", "text", None),
    ("past_medical_history", "Do you get headaches like this often, or is this new?", "text", None),
    ("medications", "Have you taken anything for it? Did it help?", "text", None),
    ("allergies", "Any known drug allergies?", "text", None),
]

_ABDOMINAL_PAIN_BANK: list[tuple[str, str, str, list[str] | None]] = [
    ("onset", "When did the stomach pain start?", "text", None),
    ("location", "Where exactly is the pain (upper, lower, left, right, all over)?", "text", None),
    ("duration", "Is the pain constant or does it come in waves?", "choice", ["Constant", "Comes in waves"]),
    ("severity", "On a scale of 1-10, how severe is the pain?", "scale", None),
    ("aggravating_factors", "Does eating make it better or worse?", "text", None),
    ("associated_symptoms", "Any vomiting, diarrhea, constipation, or blood in stool?", "text", None),
    ("associated_symptoms_fever", "Do you have a fever?", "choice", ["Yes", "No"]),
    ("associated_symptoms_urinary", "Any burning or pain while urinating?", "choice", ["Yes", "No"]),
    ("past_medical_history", "Any past similar episodes or known digestive conditions?", "text", None),
    ("medications", "Are you taking any medications currently?", "text", None),
    ("allergies", "Any known drug allergies?", "text", None),
]

_CHEST_PAIN_BANK: list[tuple[str, str, str, list[str] | None]] = [
    ("onset", "When did the chest pain start?", "text", None),
    ("character", "Would you describe it as sharp, crushing, heavy/pressure, or burning?", "text", None),
    ("radiation", "Does the pain spread to your arm, jaw, neck, or back?", "text", None),
    ("associated_symptoms", "Any shortness of breath, sweating, nausea, or dizziness with it?", "text", None),
    ("severity", "On a scale of 1-10, how severe is it right now?", "scale", None),
    ("aggravating_factors", "Does it get worse with exertion or breathing?", "text", None),
    ("past_medical_history", "Any history of heart disease, high BP, diabetes, or high cholesterol?", "text", None),
    ("medications", "Are you currently on any heart or BP medication?", "text", None),
]

_CATEGORY_BANKS: dict[str, list[tuple[str, str, str, list[str] | None]]] = {
    "headache": _HEADACHE_BANK,
    "abdominal_pain": _ABDOMINAL_PAIN_BANK,
    "chest_pain": _CHEST_PAIN_BANK,
    "generic": _GENERIC_BANK,
}

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "headache": ["headache", "head pain", "migraine", "sir dard", "sar dard"],
    "abdominal_pain": ["stomach", "abdomen", "abdominal", "belly", "pet dard", "pet me dard"],
    "chest_pain": ["chest pain", "chest discomfort", "seene me dard", "chest tightness"],
}

# A short interview is the point — a government/AYUSH OPD has minutes, not
# an hour. Stop once this many fields are collected even if the bank has more.
MAX_FIELDS_PER_SESSION = 8


def _categorize_complaint(chief_complaint: str) -> str:
    text = (chief_complaint or "").lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category
    return "generic"


def get_next_question(
    chief_complaint: str, collected_fields: dict[str, Any]
) -> tuple[str, str, str, list[str] | None] | None:
    """Deterministic core of the adaptive engine: pick the next unanswered
    field from the complaint-appropriate question bank, or None if the
    interview has collected enough (or the bank is exhausted)."""

    if len(collected_fields) >= MAX_FIELDS_PER_SESSION:
        return None

    category = _categorize_complaint(chief_complaint)
    bank = _CATEGORY_BANKS.get(category, _GENERIC_BANK)

    for field, prompt, question_type, options in bank:
        if field not in collected_fields:
            return field, prompt, question_type, options
    return None


async def refine_next_question_with_llm(
    chief_complaint: str,
    collected_fields: dict[str, Any],
    fallback: tuple[str, str, str, list[str] | None] | None,
) -> tuple[str, str, str, list[str] | None] | None:
    """Optional Groq pass that can re-phrase or re-prioritize the next
    question using the full conversation context. Falls back to the
    deterministic `fallback` on any error, missing key, or when Groq isn't
    configured — the interview must keep working without an LLM."""

    if groq_client is None:
        return fallback

    context_lines = [f"Chief complaint: {chief_complaint}"]
    for field, value in collected_fields.items():
        context_lines.append(f"- {field}: {value}")
    context_text = "\n".join(context_lines)

    system_prompt = """You are assisting a structured clinical history-taking tool for a busy \
outpatient department. You are NOT diagnosing. Given a patient's chief complaint and the \
clinical fields already collected, output ONLY a JSON object for the single best next \
question to ask:
{"field": "short_snake_case_field_name", "next_question": "the question text", \
"question_type": "text", "should_continue": true}
Rules:
- Never repeat a field already listed as collected.
- should_continue must be false only when history is genuinely sufficient for a doctor \
to begin the consultation.
- No markdown, no extra text, JSON only."""

    try:
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context_text},
            ],
            temperature=0.2,
            max_tokens=200,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip() if "```" in raw[3:] else raw.strip("`")
        data = json.loads(raw)

        if not data.get("should_continue", True):
            return None

        field = data.get("field")
        question = data.get("next_question")
        if not field or not question or field in collected_fields:
            return fallback  # LLM tried to repeat a field or gave nothing usable

        return field, question, data.get("question_type", "text"), None
    except Exception as exc:
        logger.warning("LLM next-question refinement failed, using deterministic fallback: %s", exc)
        return fallback


# ==========================================================
# 2. RED-FLAG DETECTION
# ==========================================================

# (regex, symptom label, severity, category). Patterns are matched against
# normalized (lowercased, punctuation-light) text and support common
# phrasings/variants rather than one exact string each.
_RED_FLAG_RULES: list[tuple[str, str, str, str]] = [
    (r"chest\s*(pain|pressure|tightness|discomfort)", "chest pain", "critical", "cardiac"),
    (r"(difficulty|trouble|can'?t|unable to)\s*breath", "difficulty breathing", "critical", "respiratory"),
    (r"short(ness)?\s*of\s*breath", "shortness of breath", "high", "respiratory"),
    (r"sudden(ly)?\s*(weakness|numbness)", "sudden weakness/numbness", "critical", "neurological"),
    (r"(one\s*side|half)\s*of\s*(the\s*)?(body|face)\s*(is\s*)?(weak|numb|drooping)", "one-sided weakness", "critical", "neurological"),
    (r"face\s*(is\s*)?drooping", "facial drooping", "critical", "neurological"),
    (r"slurred?\s*speech", "slurred speech", "critical", "neurological"),
    (r"(loss of|lost)\s*consciousness|fainted|unconscious|unresponsive", "loss of consciousness", "critical", "neurological"),
    (r"seizure|convulsion|fit(s)?\b", "seizure", "critical", "neurological"),
    (r"(severe|uncontrolled|heavy|profuse)\s*bleeding", "severe/uncontrolled bleeding", "high", "hemorrhage"),
    (r"(vomit(ing)?|coughing up)\s*blood", "vomiting/coughing blood", "high", "hemorrhage"),
    (r"blood\s*in\s*(stool|urine)", "blood in stool/urine", "moderate", "hemorrhage"),
    (r"(severe\s*)?allergic\s*reaction|anaphylaxis|throat\s*(is\s*)?(closing|swelling)", "severe allergic reaction", "critical", "allergy"),
    (r"suicid|kill myself|want(ing)? to die|end my life|self[\s-]?harm", "self-harm/suicidal ideation", "critical", "mental_health"),
    (r"severe\s*(abdominal|stomach|belly)\s*pain", "severe abdominal pain", "moderate", "abdominal"),
    (r"high\s*fever.*(child|infant|baby)|(child|infant|baby).*high\s*fever", "high fever in infant/child", "high", "pediatric"),
]

_SEVERITY_RANK = {"low": 0, "moderate": 1, "high": 2, "critical": 3}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def detect_red_flags_rule_based(text: str) -> list[dict[str, str]]:
    """Layer 1: fast, deterministic, high-sensitivity keyword/regex matching.
    Returns a list of {symptom, severity, category} matches (possibly empty).
    This layer alone must never depend on network access."""

    normalized = _normalize(text)
    if not normalized:
        return []

    matches: list[dict[str, str]] = []
    for pattern, symptom, severity, category in _RED_FLAG_RULES:
        if re.search(pattern, normalized):
            matches.append({"symptom": symptom, "severity": severity, "category": category})
    return matches


async def classify_red_flags_llm(context_text: str) -> dict[str, Any] | None:
    """Layer 2: contextual Groq classifier for cases the keyword layer may
    miss or under/over-call. Returns None (never raises) if Groq isn't
    configured or the call fails — callers must treat that as "no opinion",
    not "no red flag"."""

    if groq_client is None:
        return None

    system_prompt = """You are a clinical TRIAGE SIGNAL classifier, not a diagnostician. \
Given a snippet of patient-reported symptoms from a pre-consultation interview, decide \
whether it describes a potential medical emergency requiring urgent attention. Output \
ONLY this JSON object, nothing else:
{"red_flags_detected": false, "severity": "low", "detected_symptoms": [], \
"reason": "", "recommended_action": "routine_consultation"}
severity must be one of: low, moderate, high, critical.
recommended_action must be one of: routine_consultation, prompt_review, urgent_medical_attention.
Never state a diagnosis. Only classify urgency based on what was actually said."""

    try:
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context_text[:2000]},
            ],
            temperature=0.1,
            max_tokens=300,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip() if "```" in raw[3:] else raw.strip("`")
        data = json.loads(raw)
        if not data.get("red_flags_detected"):
            return None
        return {
            "severity": data.get("severity", "moderate"),
            "detected_symptoms": data.get("detected_symptoms", []),
            "reason": data.get("reason", "LLM classifier flagged this response for review."),
            "recommended_action": data.get("recommended_action", "prompt_review"),
        }
    except Exception as exc:
        logger.warning("LLM red-flag classification failed (non-fatal): %s", exc)
        return None


async def analyze_text_for_red_flags(text: str) -> dict[str, Any] | None:
    """Combine Layer 1 + Layer 2 for one piece of patient-reported text.
    Returns None if nothing was flagged, otherwise a dict ready to become
    a RedFlagAlert row (minus session/user ids)."""

    rule_matches = detect_red_flags_rule_based(text)
    llm_result = await classify_red_flags_llm(text)

    if not rule_matches and not llm_result:
        return None

    symptoms: list[str] = []
    severity = "low"
    reasons: list[str] = []
    source = "rule"

    if rule_matches:
        symptoms.extend(m["symptom"] for m in rule_matches)
        severity = max((m["severity"] for m in rule_matches), key=lambda s: _SEVERITY_RANK[s])
        reasons.append("Keyword match: " + ", ".join(sorted({m["symptom"] for m in rule_matches})))

    if llm_result:
        symptoms.extend(llm_result.get("detected_symptoms", []))
        llm_severity = llm_result.get("severity", "low")
        if _SEVERITY_RANK.get(llm_severity, 0) > _SEVERITY_RANK.get(severity, 0):
            severity = llm_severity
        if llm_result.get("reason"):
            reasons.append(f"AI review: {llm_result['reason']}")
        source = "combined" if rule_matches else "llm"

    recommended_action = "urgent_medical_attention" if severity in ("high", "critical") else "prompt_review"

    return {
        "severity": severity,
        "detected_symptoms": sorted(set(symptoms)),
        "reason": " | ".join(reasons) or "Potential red flag detected.",
        "recommended_action": recommended_action,
        "source": source,
    }
