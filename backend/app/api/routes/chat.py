"""AI chatbot routes with RAG, conversation history, long-term FAISS memory, and voice support."""
import logging
import uuid
from typing import Annotated

# FIX: Yahan 'Form' import add kiya gaya hai
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.memory import memory_service
from app.ai.rag import rag_service
from app.ai.services import extract_ocr_text
from app.ai.voice import voice_service
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import ChatMessage, ChatSession, User
from app.schemas import ChatMessageCreate, ChatMessageResponse, ChatSessionResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["AI Chatbot"])


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
async def create_session(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    language: str = "en",
):
    session = ChatSession(user_id=user.id, language=language)
    db.add(session)
    await db.flush()
    await db.refresh(session)
    # 1. FIX: MissingGreenlet error se bachne ke liye naye session me empty list assign kiya:
    session.messages = []
    return session


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # 2. FIX: List query me bhi selectinload lagaya taaki messages load ho jayein:
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .limit(20)
    )
    return result.scalars().all()


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session(
    session_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.id == session_id, ChatSession.user_id == user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    session_id: uuid.UUID,
    data: ChatMessageCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.id == session_id, ChatSession.user_id == user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_msg = ChatMessage(session_id=session.id, role="user", content=data.content)
    db.add(user_msg)

    history = [(m.content, "") for m in session.messages if m.role == "user"][-5:]

    # Hybrid RAG: general medical knowledge base + this patient's own
    # long-term FAISS memory (past chats, medical history, reports, appointments).
    try:
        rag_result = await rag_service.query(
            data.content, history, data.language, user_id=str(user.id)
        )
        logger.info(f"RAG result generated successfully for user query: {data.content[:30]}...")
    except Exception as e:
        logger.error(f"Error calling RAG service: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error retrieving medical information from knowledge base."
        )

    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=rag_result["answer"],
        confidence=rag_result["confidence"],
        sources=rag_result["sources"],
    )
    db.add(assistant_msg)
    await db.flush()

    # Persist this exchange into the user's long-term memory so it can be
    # recalled in *future* sessions too, not just within this conversation.
    try:
        await memory_service.remember_chat_turn(str(user.id), str(session.id), "user", data.content)
        await memory_service.remember_chat_turn(str(user.id), str(session.id), "assistant", rag_result["answer"])
    except Exception:
        logger.warning("Failed to persist chat turn to long-term memory", exc_info=True)

    return assistant_msg


@router.get("/memory/search")
async def search_memory(
    user: Annotated[User, Depends(get_current_user)],
    q: str = Query(..., min_length=1, description="Free-text query to search this user's long-term memory"),
    k: int = Query(5, ge=1, le=20),
):
    """Run a similarity search directly over the current user's long-term
    FAISS memory (past chats, medical history, reports, appointments).
    Useful for debugging/inspecting what the assistant "remembers" about you.
    """
    results = await memory_service.recall(str(user.id), q, k=k)
    return {"query": q, "results": results}


@router.post("/voice")
async def voice_chat(
    user: Annotated[User, Depends(get_current_user)],
    audio: UploadFile = File(...),
    # FIX: language parameter ko Form("en") me convert kiya gaya hai
    language: str = Form("en"),
):
    audio_bytes = await audio.read()
    result = await voice_service.process_voice_conversation(audio_bytes, language=language)
    return result


@router.post("/documents")
async def upload_medical_document(
    user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    content = await file.read()
    text = extract_ocr_text(content, file.filename or "doc.pdf")
    chunks_added = rag_service.add_documents([text])
    return {"message": f"Added {chunks_added} document chunks to knowledge base"}