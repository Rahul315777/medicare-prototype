"""Voice AI pipeline: Speech-to-Text → LLM Intent Router → Text-to-Speech."""

import base64
import io
import json
import logging
from typing import Any

from openai import AsyncOpenAI
# 1. ADDED: Groq Client for free/fast Speech-to-Text
from groq import AsyncGroq

from app.ai.rag import rag_service
from app.core.config import settings

logger = logging.getLogger(__name__)

class VoiceAIService:
    def __init__(self) -> None:
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY or "sk-placeholder")
        # 2. ADDED: Initialize Groq Client
        self.groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None

    async def speech_to_text(self, audio_bytes: bytes, language: str = "en") -> str:
        """Convert audio to text using Groq's Whisper model (Free & Fast)."""
        if not self.groq_client:
            logger.error("Groq API key is missing. STT will fail.")
            return "Groq key missing."

        try:
            # 3. CHANGED: Using Groq instead of OpenAI for STT to bypass 429 errors
            transcript = await self.groq_client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=("audio.webm", audio_bytes, "audio/webm"),
                response_format="text"
            )
            return transcript.strip()
        except Exception as e:
            logger.error(f"Groq STT Error: {e}")
            return ""

    async def text_to_speech(self, text: str, language: str = "en") -> bytes:
        """Convert text response to speech."""
        if not settings.OPENAI_API_KEY or not text:
            return b""

        try:
            response = await self.openai_client.audio.speech.create(
                model="tts-1",
                voice="nova",
                input=text[:4096],
            )
            return response.content
        except Exception as e:
            logger.error(f"TTS Error: {e}")
            return b""

    async def process_voice_conversation(
        self,
        audio_bytes: bytes,
        chat_history: list[tuple[str, str]] | None = None,
        language: str = "en",
    ) -> dict[str, Any]:
        """Full voice pipeline with App Navigation & Booking Control."""
        
        # 1. Kaan (Hearing): Audio to Text (Now uses Groq)
        transcript = await self.speech_to_text(audio_bytes, language)
        if not transcript:
            return {"action": "error", "answer": "I couldn't hear you properly.", "audio_base64": None}

        # 2. Dimaag (Intent Routing): Decide what to do with the text
        system_prompt = """You are MediCare AI, the core voice controller of a medical app.
Analyze the user's text and determine their intent. Respond ONLY in valid JSON format.

Rules:
1. Action "navigate": For opening pages (e.g., "show my reports", "take me to dashboard"). Set target to "/reports", "/dashboard", "/emergency", etc.
2. Action "book": For booking an appointment (e.g., "book an appointment with Dr. Sharma"). Set target to "/appointments" and extract details.
3. Action "chat": For general medical questions (e.g., "what is paracetamol?"). Set target to null.
4. "reply_text": A short spoken acknowledgment (e.g., "Opening your reports", "Let's book your appointment").

JSON Format:
{
  "action": "navigate" | "book" | "chat",
  "target": "/page_url" | null,
  "data": {"doctor_name": "...", "date": "..."},
  "reply_text": "Short spoken response here"
}"""

        try:
            # Still using OpenAI for Intent Routing as instructed
            intent_completion = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL or "gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcript}
                ],
                response_format={"type": "json_object"}
            )
            intent_data = json.loads(intent_completion.choices[0].message.content)
        except Exception as e:
            logger.error(f"Intent parsing error: {e}")
            intent_data = {"action": "chat", "reply_text": "Let me check that for you."}

        action = intent_data.get("action", "chat")
        reply_text = intent_data.get("reply_text", "Processing your request.")
        confidence = 1.0
        sources = []

        # 3. Action Execution: Agar chat hai toh medical database (RAG) se answer nikalo
        if action == "chat":
            rag_result = await rag_service.query(transcript, chat_history, language)
            reply_text = rag_result["answer"]
            confidence = rag_result["confidence"]
            sources = rag_result["sources"]

        # 4. Zubaan (Speaking): Generate Audio for the final response
        audio_response = await self.text_to_speech(reply_text, language)

        # Frontend ko poora control package bhej rahe hain
        return {
            "transcript": transcript,
            "action": action,                           # 'navigate', 'book', or 'chat'
            "target": intent_data.get("target"),        # e.g., '/appointments'
            "command_data": intent_data.get("data", {}),# e.g., {'doctor_name': 'Sharma'}
            "answer": reply_text,                       # Spoken text
            "confidence": confidence,
            "sources": sources,
            "audio_base64": base64.b64encode(audio_response).decode() if audio_response else None,
        }

voice_service = VoiceAIService()