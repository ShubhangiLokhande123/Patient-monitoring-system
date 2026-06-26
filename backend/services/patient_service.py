"""
Patient service layer - handles all patient-related business logic.
"""

import json
from datetime import datetime
from typing import Optional
from database import get_db
from models.patient import Patient, PatientSummary
from models.alerts import RiskScore


class PatientService:
    """Service for patient data operations."""

    def get_all_patients(self, status: Optional[str] = None) -> list[dict]:
        """Get all patients, optionally filtered by status."""
        with get_db() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM patients WHERE status = ? ORDER BY discharge_date DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM patients ORDER BY discharge_date DESC"
                ).fetchall()
            return [dict(row) for row in rows]

    def get_patient_by_id(self, patient_id: str) -> Optional[dict]:
        """Get a single patient by ID."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM patients WHERE id = ?", (patient_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_patient_summary(self, patient_id: str) -> Optional[dict]:
        """Get patient with latest risk score and alert count."""
        patient = self.get_patient_by_id(patient_id)
        if not patient:
            return None

        with get_db() as conn:
            # Get latest risk score
            risk_row = conn.execute(
                """
                SELECT score, category FROM risk_scores 
                WHERE patient_id = ? 
                ORDER BY calculated_at DESC LIMIT 1
                """,
                (patient_id,),
            ).fetchone()

            # Get active alert count
            alert_count = conn.execute(
                "SELECT COUNT(*) FROM alerts WHERE patient_id = ? AND status = 'active'",
                (patient_id,),
            ).fetchone()[0]

            # Calculate days post discharge
            discharge_date = datetime.strptime(patient["discharge_date"], "%Y-%m-%d")
            days_post = (datetime.now() - discharge_date).days

            return {
                **patient,
                "latest_risk_score": risk_row["score"] if risk_row else None,
                "latest_risk_category": risk_row["category"] if risk_row else None,
                "active_alerts": alert_count,
                "days_post_discharge": days_post,
            }

    def update_patient_status(self, patient_id: str, status: str) -> bool:
        """Update patient status."""
        with get_db() as conn:
            conn.execute(
                "UPDATE patients SET status = ?, updated_at = datetime('now') WHERE id = ?",
                (status, patient_id),
            )
            return True

    def get_high_risk_patients(self, threshold: int = 70) -> list[dict]:
        """Get patients with risk scores above threshold."""
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT p.*, rs.score, rs.category 
                FROM patients p
                JOIN risk_scores rs ON p.id = rs.patient_id
                WHERE rs.score >= ? AND p.status = 'active'
                ORDER BY rs.score DESC
                """,
                (threshold,),
            ).fetchall()
            return [dict(row) for row in rows]

    def create_patient(self, patient: Patient) -> dict:
        """Create a new patient record."""
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO patients (
                    id, first_name, last_name, date_of_birth, phone,
                    diagnosis, procedure_name, discharge_date,
                    discharge_summary_id, assigned_clinician,
                    comorbidities, length_of_stay_days,
                    admission_acuity, er_visits_prior_6m, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    patient.id,
                    patient.first_name,
                    patient.last_name,
                    patient.date_of_birth,
                    patient.phone,
                    patient.diagnosis,
                    patient.procedure_name,
                    patient.discharge_date,
                    patient.discharge_summary_id,
                    patient.assigned_clinician,
                    json.dumps(patient.comorbidities),
                    patient.length_of_stay_days,
                    patient.admission_acuity,
                    patient.er_visits_prior_6m,
                    patient.status,
                ),
            )
        return self.get_patient_by_id(patient.id)


# Singleton
patient_service = PatientService()
