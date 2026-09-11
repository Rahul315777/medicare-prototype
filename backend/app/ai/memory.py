"""
MediCare AI — Long-Term Vector Memory (FAISS)
==============================================

Production-grade, per-user long-term memory built on FAISS + HuggingFace
sentence embeddings (local, no external API calls or API key required).

What gets stored here:
    - Past chat turns (user + assistant messages)
    - Medical history events (conditions, allergies, family history entries)
    - Medical report / prescription summaries
    - Appointment context (doctor, specialty, notes, outcome)

Each user gets their own FAISS index, persisted to disk under
``{UPLOAD_DIR}/user_memory/{user_id}/``, so memory survives restarts and is
never mixed between users. Retrieval is a plain cosine-similarity search over
each user's own index (optionally filtered by memory "type"), which is then
combined by ``app.ai.rag.MedicalRAGService`` with the shared medical knowledge
base index to produce a hybrid answer.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import settings

logger = logging.getLogger(__name__)

MEMORY_ROOT = Path(settings.UPLOAD_DIR) / "user_memory"

# ==========================================================
# Shared embeddings singleton
# ==========================================================
# Loading a sentence-transformers model is expensive (~seconds, ~90MB RAM).
# We load it exactly once and share it between the RAG knowledge-base index
# and every per-user memory index.

_embeddings_lock = threading.Lock()
_embeddings_instance: HuggingFaceEmbeddings | None = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """Return the process-wide singleton embeddings model."""
    global _embeddings_instance
    if _embeddings_instance is None:
        with _embeddings_lock:
            if _embeddings_instance is None:
                logger.info("Loading sentence-transformer embeddings model (all-MiniLM-L6-v2)...")
                _embeddings_instance = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2",
                    encode_kwargs={"normalize_embeddings": True},
                )
    return _embeddings_instance


class UserMemoryStore:
    """A single user's FAISS-backed long-term memory index.

    FAISS + the LangChain wrapper are synchronous/CPU-bound, so every call
    that touches the index runs inside ``asyncio.to_thread`` from the async
    methods below. A per-store lock serializes writes so concurrent requests
    for the same user can't corrupt the on-disk index.
    """

    def __init__(self, user_id: str, embeddings: HuggingFaceEmbeddings) -> None:
        self.user_id = user_id
        self.embeddings = embeddings
        self.dir = MEMORY_ROOT / user_id
        self._lock = threading.Lock()
        self.store: FAISS | None = None
        self._load()

    # -- internal, synchronous, always called under self._lock or at init --

    def _load(self) -> None:
        index_file = self.dir / "index.faiss"
        if index_file.exists():
            try:
                self.store = FAISS.load_local(
                    str(self.dir),
                    self.embeddings,
                    allow_dangerous_deserialization=True,
                )
                return
            except Exception as exc:
                logger.warning("Could not load memory index for user %s (%s). Starting fresh.", self.user_id, exc)
        self.store = None

    def _persist(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        assert self.store is not None
        self.store.save_local(str(self.dir))

    def _add_sync(self, texts: list[str], metadatas: list[dict[str, Any]]) -> None:
        docs = [Document(page_content=t, metadata=m) for t, m in zip(texts, metadatas)]
        with self._lock:
            if self.store is None:
                self.store = FAISS.from_documents(docs, self.embeddings)
            else:
                self.store.add_documents(docs)
            self._persist()

    def _search_sync(self, query: str, k: int, memory_types: list[str] | None) -> list[Document]:
        with self._lock:
            if self.store is None:
                return []
            # Over-fetch then filter by type in Python. LangChain's FAISS
            # metadata-filter support varies by version, so filtering
            # manually here is the more robust/portable approach.
            fetch_k = max(k * 4, 12) if memory_types else k
            results = self.store.similarity_search(query, k=fetch_k)
        if memory_types:
            results = [d for d in results if d.metadata.get("type") in memory_types]
        return results[:k]

    # -- public async API --

    async def add(self, text: str, metadata: dict[str, Any]) -> None:
        if not text or not text.strip():
            return
        enriched = {
            **metadata,
            "user_id": self.user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await asyncio.to_thread(self._add_sync, [text.strip()], [enriched])

    async def search(
        self, query: str, k: int = 5, memory_types: list[str] | None = None
    ) -> list[Document]:
        if not query or not query.strip():
            return []
        return await asyncio.to_thread(self._search_sync, query, k, memory_types)


class MemoryService:
    """Process-wide registry of per-user memory stores plus convenience
    helpers used by the API routes (chat, medical reports, appointments)."""

    def __init__(self) -> None:
        self._stores: dict[str, UserMemoryStore] = {}
        self._registry_lock = threading.Lock()

    def _get_store(self, user_id: str) -> UserMemoryStore:
        store = self._stores.get(user_id)
        if store is None:
            with self._registry_lock:
                store = self._stores.get(user_id)
                if store is None:
                    store = UserMemoryStore(user_id, get_embeddings())
                    self._stores[user_id] = store
        return store

    # -- write helpers, one per source of context --

    async def remember_chat_turn(self, user_id: str, session_id: str, role: str, content: str) -> None:
        await self._get_store(user_id).add(
            content,
            {"type": "chat", "role": role, "session_id": session_id},
        )

    async def remember_medical_event(
        self,
        user_id: str,
        text: str,
        event_type: str = "medical_history",
        source_id: str | None = None,
    ) -> None:
        await self._get_store(user_id).add(
            text,
            {"type": event_type, "source_id": source_id},
        )

    async def remember_report(self, user_id: str, report_id: str, title: str, summary: str, risk_level: str) -> None:
        text = f"Medical report '{title}' (risk: {risk_level}): {summary}"
        await self._get_store(user_id).add(
            text,
            {"type": "report", "source_id": report_id, "risk_level": risk_level},
        )

    async def remember_prescription(self, user_id: str, prescription_id: str, doctor_name: str | None, medicines: list[dict]) -> None:
        med_names = ", ".join(m.get("name", "Unknown") for m in medicines) or "no medicines listed"
        text = f"Prescription from {doctor_name or 'unknown doctor'}: {med_names}"
        await self._get_store(user_id).add(
            text,
            {"type": "prescription", "source_id": prescription_id},
        )

    async def remember_appointment(
        self, user_id: str, appointment_id: str, doctor_name: str, specialty: str, scheduled_at: str, notes: str | None = None
    ) -> None:
        text = f"Appointment with Dr. {doctor_name} ({specialty}) scheduled for {scheduled_at}."
        if notes:
            text += f" Notes: {notes}"
        await self._get_store(user_id).add(
            text,
            {"type": "appointment", "source_id": appointment_id},
        )

    # -- read / retrieval --

    async def recall(
        self, user_id: str, query: str, k: int = 5, memory_types: list[str] | None = None
    ) -> list[dict[str, Any]]:
        docs = await self._get_store(user_id).search(query, k=k, memory_types=memory_types)
        return [{"content": d.page_content, "metadata": d.metadata} for d in docs]

    async def build_context(self, user_id: str, query: str, k: int = 5) -> str:
        """Convenience helper: return a single joined string of the most
        relevant memories, ready to drop into an LLM prompt."""
        memories = await self.recall(user_id, query, k=k)
        if not memories:
            return ""
        return "\n".join(f"[{m['metadata'].get('type', 'note')}] {m['content']}" for m in memories)


# Process-wide singleton, imported by rag.py and the API routes.
memory_service = MemoryService()
