"""
Application configuration loaded from environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Central configuration for the Concierge Triage Agent."""

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Google Gemini
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.0-flash")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./concierge_triage.db")
    DB_PATH: str = os.getenv("DB_PATH", "concierge_triage.db")

    # CORS
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")

    # Risk Model Thresholds
    RISK_SCORE_THRESHOLD_HIGH: int = int(
        os.getenv("RISK_SCORE_THRESHOLD_HIGH", "70")
    )
    RISK_SCORE_THRESHOLD_CRITICAL: int = int(
        os.getenv("RISK_SCORE_THRESHOLD_CRITICAL", "85")
    )

    # RAG Configuration
    RAG_CONFIDENCE_THRESHOLD: float = float(
        os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.65")
    )
    RAG_CHUNK_SIZE: int = 500
    RAG_CHUNK_OVERLAP: int = 50
    RAG_TOP_K: int = 5

    # PHI De-identification
    PHI_ENTITIES: list[str] = [
        "PERSON",
        "PHONE_NUMBER",
        "EMAIL_ADDRESS",
        "US_SSN",
        "LOCATION",
        "DATE_TIME",
        "MEDICAL_LICENSE",
        "IP_ADDRESS",
        "CREDIT_CARD",
    ]


settings = Settings()
