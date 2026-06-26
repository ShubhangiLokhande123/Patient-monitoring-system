"""Pydantic models for patient data."""

from pydantic import BaseModel
from typing import Optional


class Patient(BaseModel):
    id: str
    first_name: str
    last_name: str
    date_of_birth: Optional[str] = None
    phone: Optional[str] = None
    diagnosis: str
    procedure_name: Optional[str] = None
    discharge_date: str
    discharge_summary_id: Optional[str] = None
    assigned_clinician: str = "Dr. Sarah Chen"
    comorbidities: list[str] = []
    length_of_stay_days: int = 3
    admission_acuity: str = "elective"
    er_visits_prior_6m: int = 0
    status: str = "active"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PatientSummary(BaseModel):
    id: str
    first_name: str
    last_name: str
    diagnosis: str
    discharge_date: str
    status: str
    latest_risk_score: Optional[int] = None
    latest_risk_category: Optional[str] = None
    active_alerts: int = 0
    days_post_discharge: Optional[int] = None
