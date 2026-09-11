"""MediCare AI Smart RAG System."""

import logging
from pathlib import Path
from typing import Any

from groq import Groq
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ai.memory import get_embeddings, memory_service
from app.core.config import settings

logger = logging.getLogger(__name__)

PERSIST_DIR = Path(settings.UPLOAD_DIR) / "faiss_medical_index"

GREETINGS = {"hi", "hello", "hey", "hi there", "good morning", "good evening", "namaste", "how are you", "how are u", "hopw are u", "how are you?"}

MEDICAL_SYSTEM_PROMPT = """You are MediCare AI, a professional, empathetic, and highly knowledgeable medical health assistant.
RULES:
1. ONLY answer medical, health, wellness, disease, symptom, and treatment-related questions.
2. If the user asks a non-medical question, politely refuse and say: "I am MediCare AI, a specialized health assistant. I can only answer medical and health-related questions."
3. Provide accurate, clear, and well-structured answers (use brief bullet points if explaining symptoms, causes, or treatments).
4. If the "Patient's Own History" section below contains relevant information, refer to it naturally to personalize your answer.
5. Always add a short professional disclaimer at the end: "Note: Consult a doctor for professional medical advice."
"""

DEFAULT_KNOWLEDGE_DOCS = [
    "Joint pain (arthralgia) is inflammation or soreness in joints often caused by arthritis, strain, or injury, and can be managed with rest, cold/heat therapy, and pain relievers.",
    "Cancer is a disease characterized by the uncontrolled growth and spread of abnormal cells in the body, which can be treated via chemotherapy, surgery, or radiation.",
    "Acne is a common skin disease characterized by pimples on the face, chest, and back caused by clogged pores and excess oil production.",
    "Fever is an abnormal increase in body temperature, often acting as the immune system's natural defense against bacterial or viral infections.",
]

class MedicalRAGService:
    def __init__(self) -> None:
        self.embeddings = get_embeddings()

        if not settings.GROQ_API_KEY:
            logger.warning("GROQ_API_KEY is not set.")
        self.groq_client = Groq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None

        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
        self.vector_store: FAISS | None = None
        self._load_or_create_index()

    def _load_or_create_index(self) -> None:
        if PERSIST_DIR.exists() and (PERSIST_DIR / "index.faiss").exists():
            try:
                self.vector_store = FAISS.load_local(
                    str(PERSIST_DIR), self.embeddings, allow_dangerous_deserialization=True
                )
                return
            except Exception as exc:
                logger.warning("Could not load index (%s); rebuilding.", exc)
        self._create_default_index()

    def _create_default_index(self) -> None:
        docs = self.text_splitter.create_documents(DEFAULT_KNOWLEDGE_DOCS)
        self.vector_store = FAISS.from_documents(docs, self.embeddings)
        PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        self.vector_store.save_local(str(PERSIST_DIR))

    def add_documents(self, texts: list[str]) -> int:
        if not texts:
            return 0
        docs = self.text_splitter.create_documents(texts)
        if self.vector_store is None:
            self.vector_store = FAISS.from_documents(docs, self.embeddings)
        else:
            self.vector_store.add_documents(docs)
        PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        self.vector_store.save_local(str(PERSIST_DIR))
        return len(docs)

    async def query(
        self,
        question: str,
        chat_history: list[tuple[str, str]] | None = None,
        language: str = "en",
        user_id: str | None = None,
    ) -> dict[str, Any]:
        clean_q = question.lower().strip()
        
        if clean_q in GREETINGS or len(clean_q) < 4:
            return {
                "answer": "Hello! I am MediCare AI, your specialized health assistant. Ask me any medical question or ask about symptoms, conditions, or treatments!",
                "confidence": 99.0,
                "sources": [],
            }

        if self.vector_store is None:
            self._create_default_index()

        raw_kb_docs = self.vector_store.similarity_search_with_score(question, k=3)
        kb_docs = []
        kb_sources = []
        
        for doc, distance in raw_kb_docs:
            if distance < 1.4:
                kb_docs.append(doc)
                kb_sources.append({"content": doc.page_content[:180], "metadata": {**doc.metadata, "type": "knowledge_base"}})

        knowledge_context = "\n".join(d.page_content for d in kb_docs)

        memory_context = ""
        memory_sources: list[dict[str, Any]] = []
        if user_id:
            try:
                memories = await memory_service.recall(user_id, question, k=4)
                if memories:
                    memory_context = "\n".join(f"[{m['metadata'].get('type', 'note')}] {m['content']}" for m in memories)
                    memory_sources = [{"content": m["content"][:180], "metadata": m["metadata"]} for m in memories]
            except Exception as exc:
                logger.warning("User memory recall failed for %s: %s", user_id, exc)

        combined_sources = kb_sources + memory_sources

        if self.groq_client:
            try:
                user_prompt = f"""Use the Book/Reference Context and the Patient's Own History below if they are relevant to the question. Combine them with your medical expertise to answer accurately and personally.

Book/Reference Context:
{knowledge_context or "(none)"}

Patient's Own History:
{memory_context or "(no prior history available yet)"}

User Medical Question: {question}"""

                response = self.groq_client.chat.completions.create(
                   model="openai/gpt-oss-20b",
                    messages=[
                        {"role": "system", "content": MEDICAL_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.3,
                    max_tokens=350,
                )
                answer = response.choices[0].message.content.strip()
                dynamic_confidence = 88.5 if combined_sources else 75.0
                
                return {"answer": answer, "confidence": dynamic_confidence, "sources": combined_sources}
            except Exception as exc:
                error_msg = str(exc)
                logger.error("Groq API error: %s", error_msg)
                return {
                    "answer": f"⚠️ SYSTEM ERROR: Groq API fail ho gayi hai. Error detail: {error_msg}. Apni .env file mein API key check karein.", 
                    "confidence": 0.0, 
                    "sources": []
                }

        if kb_docs:
            fallback_answer = (
                f"Based on medical records: {kb_docs[0].page_content} "
                "(Note: Consult a doctor for professional medical advice)."
            )
            return {"answer": fallback_answer, "confidence": 75.0, "sources": combined_sources}
        else:
            return {
                "answer": "I couldn't find specific information for your query right now. Please consult a doctor for professional medical advice.", 
                "confidence": 99.0, 
                "sources": []
            }

rag_service = MedicalRAGService()