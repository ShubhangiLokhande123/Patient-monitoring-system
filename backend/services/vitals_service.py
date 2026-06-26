"""
Vitals service layer - handles vitals data storage and retrieval.
"""

import json
from datetime import datetime
from typing import Optional
from database import get_db


class VitalsService:
    """Service for vitals data operations."""

    def record_vitals(
        self,
        patient_id: str,
        conversation_id: Optional[str] = None,
        pain_level: Optional[int] = None,
        temperature: Optional[float] = None,
        wound_status: Optional[str] = None,
        medication_adherence: Optional[bool] = None,
        mobility_status: Optional[str] = None,
        appetite: Optional[str] = None,
        additional_notes: Optional[str] = None,
    ) -> dict:
        """Record vitals for a patient."""
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO vitals (
                    patient_id, conversation_id, pain_level, temperature,
                    wound_status, medication_adherence, mobility_status,
                    appetite, additional_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    patient_id,
                    conversation_id,
                    pain_level,
                    temperature,
                    wound_status,
                    1 if medication_adherence else 0 if medication_adherence is False else None,
                    mobility_status,
                    appetite,
                    additional_notes,
                ),
            )
            vitals_id = cursor.lastrowid

        return self.get_vitals(vitals_id)

    def get_vitals(self, vitals_id: int) -> Optional[dict]:
        """Get vitals record by ID."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM vitals WHERE id = ?", (vitals_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_latest_vitals(self, patient_id: str) -> Optional[dict]:
        """Get the most recent vitals for a patient."""
        with get_db() as conn:
            row = conn.execute(
                """
                SELECT * FROM vitals 
                WHERE patient_id = ? 
                ORDER BY recorded_at DESC LIMIT 1
                """,
                (patient_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_vitals_history(
        self, patient_id: str, limit: int = 10
    ) -> list[dict]:
        """Get vitals history for a patient."""
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT * FROM vitals 
                WHERE patient_id = ? 
                ORDER BY recorded_at DESC
                LIMIT ?
                """,
                (patient_id, limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_conversation_vitals(self, conversation_id: str) -> Optional[dict]:
        """Get vitals recorded during a specific conversation."""
        with get_db() as conn:
            row = conn.execute(
                """
                SELECT * FROM vitals 
                WHERE conversation_id = ?
                ORDER BY recorded_at DESC LIMIT 1
                """,
                (conversation_id,),
            ).fetchone()
            return dict(row) if row else None


# Singleton
vitals_service = VitalsService()
