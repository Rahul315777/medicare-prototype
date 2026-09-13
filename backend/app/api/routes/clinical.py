"""AI clinical case-taking routes: adaptive interview + red-flag detection.

Deliberately separate from app.api.routes.chat (the general RAG chatbot) —
this is a structured, field-by-field pre-consultation history, not free-form
Q&A. See app.ai.clinical for the question-selection and red-flag logic.
"""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.clinical import (
    analyze_text_for_red_flags,
    get_next_question,
    refine_next_question_with_llm,
)
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import (
    ClinicalAnswer,
    ClinicalQuestion,
    ClinicalSession,
    ClinicalSessionStatus,
    RedFlagAlert,
    RedFlagSeverity,
    RedFlagSource,
    User,
)
from app.schemas import (
    ClinicalAnswerCreate,
    ClinicalAnswerSubmitResponse,
    ClinicalSessionCreate,
    ClinicalSessionResponse,
    RedFlagAlertResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/clinical-sessions", tags=["AI Clinical Case-Taking"])


def _session_load_options():
    return (
        selectinload(ClinicalSession.questions),
        selectinload(ClinicalSession.answers),
        selectinload(ClinicalSession.red_flags),
    )


async def _get_owned_session(
    session_id: uuid.UUID, user: User, db: AsyncSession
) -> ClinicalSession:
    """Fetch a session, enforcing that it belongs to the requesting user.
    A session that exists but belongs to someone else returns 404 (not 403)
    so we don't confirm to an attacker that the session id is valid."""

    result = await db.execute(
        select(ClinicalSession)
        .options(*_session_load_options())
        .where(ClinicalSession.id == session_id, ClinicalSession.user_id == user.id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Clinical session not found")
    return session


async def _store_red_flags(
    db: AsyncSession, session: ClinicalSession, user: User, text: str
) -> list[RedFlagAlert]:
    """Run red-flag analysis on `text` and persist any new alert, skipping
    ones that substantially duplicate an already-recorded alert for this
    session (same symptom set).

    Deliberately never reads or appends to `session.red_flags` — this is
    called both with a freshly-constructed, just-flushed `session` (from
    `start_clinical_session`, where `.red_flags` was never eager-loaded) and
    with a session fetched via `_get_owned_session` (where it was). Touching
    an unloaded relationship collection on AsyncSession triggers an implicit
    lazy SELECT outside a greenlet context, which raises MissingGreenlet.
    Querying RedFlagAlert directly works safely in both cases.
    """

    result = await analyze_text_for_red_flags(text)
    if result is None:
        return []

    new_symptoms = set(result["detected_symptoms"])

    existing_result = await db.execute(
        select(RedFlagAlert).where(RedFlagAlert.clinical_session_id == session.id)
    )
    for existing in existing_result.scalars():
        if new_symptoms and new_symptoms.issubset(set(existing.detected_symptoms)):
            return []  # already captured by an earlier, at-least-as-broad alert

    alert = RedFlagAlert(
        user_id=user.id,
        clinical_session_id=session.id,
        severity=RedFlagSeverity(result["severity"]),
        detected_symptoms=result["detected_symptoms"],
        reason=result["reason"],
        recommended_action=result["recommended_action"],
        source=RedFlagSource(result["source"]),
    )
    db.add(alert)
    await db.flush()
    return [alert]


@router.post("", response_model=ClinicalSessionResponse, status_code=201)
async def start_clinical_session(
    data: ClinicalSessionCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    session = ClinicalSession(
        user_id=user.id,
        chief_complaint=data.chief_complaint,
        language=data.language,
        collected_fields={},
    )
    db.add(session)
    await db.flush()

    # The chief complaint itself may already contain a red flag
    # (e.g. "severe chest pain and difficulty breathing").
    await _store_red_flags(db, session, user, data.chief_complaint)

    field, prompt, question_type, options = get_next_question(data.chief_complaint, {})
    question = ClinicalQuestion(
        session_id=session.id,
        field=field,
        prompt=prompt,
        question_type=question_type,
        options=options,
        order_index=0,
    )
    db.add(question)
    await db.flush()

    # `session` here was constructed directly (never loaded via a query), so
    # its `.questions`/`.answers`/`.red_flags` relationship collections were
    # never marked "loaded" — touching them (even just to append) triggers an
    # implicit lazy SELECT outside a greenlet context and raises
    # MissingGreenlet. Re-fetching via `_get_owned_session` (which
    # selectinload's all three) gives back an object whose collections are
    # already populated through a properly-awaited query, so the response
    # model can serialize them safely without any further lazy load.
    return await _get_owned_session(session.id, user, db)


@router.get("/{session_id}", response_model=ClinicalSessionResponse)
async def get_clinical_session(
    session_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await _get_owned_session(session_id, user, db)


@router.post("/{session_id}/answers", response_model=ClinicalAnswerSubmitResponse)
async def submit_answer(
    session_id: uuid.UUID,
    data: ClinicalAnswerCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    session = await _get_owned_session(session_id, user, db)

    if session.status == ClinicalSessionStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="This clinical session is already completed")

    # If a question_id was given, make sure it belongs to THIS session.
    if data.question_id is not None and not any(q.id == data.question_id for q in session.questions):
        raise HTTPException(status_code=400, detail="question_id does not belong to this session")

    answer = ClinicalAnswer(
        session_id=session.id,
        question_id=data.question_id,
        field=data.field,
        content=data.content,
    )
    db.add(answer)

    collected = dict(session.collected_fields or {})
    collected[data.field] = data.content
    session.collected_fields = collected

    await db.flush()
    session.answers.append(answer)

    new_alerts = await _store_red_flags(db, session, user, data.content)

    fallback = get_next_question(session.chief_complaint or "", collected)
    next_field = await refine_next_question_with_llm(session.chief_complaint or "", collected, fallback)

    next_question_obj: ClinicalQuestion | None = None
    should_continue = next_field is not None
    if next_field is not None:
        field, prompt, question_type, options = next_field
        next_question_obj = ClinicalQuestion(
            session_id=session.id,
            field=field,
            prompt=prompt,
            question_type=question_type,
            options=options,
            order_index=len(session.questions),
        )
        db.add(next_question_obj)
        await db.flush()
        session.questions.append(next_question_obj)

    return ClinicalAnswerSubmitResponse(
        answer=answer,
        next_question=next_question_obj,
        should_continue=should_continue,
        red_flags=new_alerts,
    )


@router.post("/{session_id}/complete", response_model=ClinicalSessionResponse)
async def complete_clinical_session(
    session_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from datetime import datetime, timezone

    session = await _get_owned_session(session_id, user, db)
    session.status = ClinicalSessionStatus.COMPLETED
    session.completed_at = datetime.now(timezone.utc)
    await db.flush()
    return session


@router.get("/{session_id}/red-flags", response_model=list[RedFlagAlertResponse])
async def get_session_red_flags(
    session_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    session = await _get_owned_session(session_id, user, db)
    return session.red_flags
