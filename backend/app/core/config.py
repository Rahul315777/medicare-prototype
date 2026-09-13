"""
Application configuration.
Loads all settings from .env
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ==================================================
    # APP
    # ==================================================

    APP_NAME: str = "MediCare AI"
    APP_VERSION: str = "1.0.0"

    DEBUG: bool = True

    API_V1_PREFIX: str = "/api/v1"

    FRONTEND_URL: str = "http://localhost:3000"

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # ==================================================
    # SECURITY
    # ==================================================

    SECRET_KEY: str = "CHANGE_THIS_TO_A_RANDOM_SECRET"

    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    JWT_ISSUER: str = "medicare-ai"

    JWT_AUDIENCE: str = "medicare-client"

    OTP_EXPIRE_MINUTES: int = 10

    # ==================================================
    # DATABASE
    # ==================================================

    DATABASE_URL: str = "sqlite+aiosqlite:///./medicare.db"

    DATABASE_URL_SYNC: str = "sqlite:///./medicare.db"

    # ==================================================
    # REDIS
    # ==================================================

    REDIS_URL: str = "redis://localhost:6379/0"

    # ==================================================
    # EMAIL
    # ==================================================

    SMTP_HOST: str = "smtp.gmail.com"

    SMTP_PORT: int = 587

    SMTP_USERNAME: str = ""

    SMTP_PASSWORD: str = ""

    SMTP_FROM_EMAIL: str = ""

    SMTP_FROM_NAME: str = "MediCare AI"

    SMTP_TLS: bool = True

    # ==================================================
    # OPENAI
    # ==================================================

    OPENAI_API_KEY: str = ""

    OPENAI_MODEL: str = "gpt-4o"

    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ==================================================
    # GROQ (used for the medical chatbot LLM + vision analysis)
    # ==================================================

    GROQ_API_KEY: str = ""

    # ==================================================
    # GOOGLE
    # ==================================================

    GOOGLE_CLIENT_ID: str = ""

    GOOGLE_CLIENT_SECRET: str = ""

    GOOGLE_MAPS_API_KEY: str = ""

    # ==================================================
    # HUGGING FACE
    # ==================================================

    HUGGINGFACEHUB_API_TOKEN: str = ""

    # ==================================================
    # STORAGE
    # ==================================================

    # Optional explicit path to the tesseract binary. Leave unset to rely on
    # PATH resolution (works on Linux/WSL/Docker and on Windows installs that
    # added Tesseract to PATH). Only set this for a Windows dev machine where
    # Tesseract wasn't added to PATH.
    TESSERACT_CMD: str | None = None

    STORAGE_BACKEND: str = "local"

    UPLOAD_DIR: str = "./uploads"

    CLOUDINARY_CLOUD_NAME: str = ""

    CLOUDINARY_API_KEY: str = ""

    CLOUDINARY_API_SECRET: str = ""

    AWS_ACCESS_KEY_ID: str = ""

    AWS_SECRET_ACCESS_KEY: str = ""

    AWS_S3_BUCKET: str = ""

    AWS_REGION: str = "us-east-1"

    # ==================================================
    # VECTOR DATABASE
    # ==================================================

    VECTOR_DB: str = "faiss"

    CHROMA_PERSIST_DIR: str = "./chroma_db"

    PINECONE_API_KEY: str = ""

    PINECONE_INDEX: str = "medicare-rag"

    # ==================================================
    # RATE LIMIT
    # ==================================================

    RATE_LIMIT: str = "100/minute"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()

    if (
        not settings.DEBUG
        and settings.SECRET_KEY == "CHANGE_THIS_TO_A_RANDOM_SECRET"
    ):
        raise ValueError(
            "SECRET_KEY must be changed before production deployment."
        )

    return settings


settings = get_settings()