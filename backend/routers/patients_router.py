"""
Patients router - handles patient data operations.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from models.patient import Patient, PatientSummary
from services.patient_service import patient_service
from services.alert_service import alert_service
from services.conversation_service import conversation_service

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/")
async def list_patients(
    status: Optional[str] = Query(None, description="Filter by status (active/completed/archived)")
):
    """Get all patients, optionally filtered by status."""
    patients = patient_service.get_all_patients(status)
    return {"patients": patients, "count": len(patients)}


@router.get("/high-risk")
async def get_high_risk_patients(
    threshold: int = Query(70, description="Risk score threshold")
):
    """Get patients with risk scores above threshold."""
    patients = patient_service.get_high_risk_patients(threshold)
    return {"patients": patients, "count": len(patients)}


@router.get("/{patient_id}", response_model=dict)
async def get_patient(patient_id: str):
    """Get a single patient by ID."""
    patient = patient_service.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.get("/{patient_id}/summary")
async def get_patient_summary(patient_id: str):
    """Get patient with latest risk score and alert count."""
    summary = patient_service.get_patient_summary(patient_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Patient not found")
    return summary


@router.get("/{patient_id}/conversations")
async def get_patient_conversations(patient_id: str):
    """Get all conversations for a patient."""
    patient = patient_service.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    conversations = conversation_service.get_conversations_by_patient(patient_id)
    return {"conversations": conversations, "count": len(conversations)}


@router.get("/{patient_id}/alerts")
async def get_patient_alerts(
    patient_id: str,
    status: Optional[str] = Query(None, description="Filter by alert status")
):
    """Get alerts for a patient."""
    patient = patient_service.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    alerts = alert_service.get_patient_alerts(patient_id, status)
    return {"alerts": alerts, "count": len(alerts)}


@router.get("/{patient_id}/risk-history")
async def get_risk_history(patient_id: str, limit: int = Query(10)):
    """Get risk score history for a patient."""
    patient = patient_service.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    history = alert_service.get_risk_score_history(patient_id, limit)
    return {"risk_history": history, "count": len(history)}


@router.patch("/{patient_id}/status")
async def update_patient_status(patient_id: str, status: str):
    """Update patient status."""
    patient = patient_service.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if status not in ("active", "completed", "archived"):
        raise HTTPException(
            status_code=400,
            detail="Status must be 'active', 'completed', or 'archived'",
        )

    patient_service.update_patient_status(patient_id, status)
    return {"status": "updated", "patient_id": patient_id, "new_status": status}


@router.post("/", response_model=dict)
async def create_patient(patient: Patient):
    """Create a new patient."""
    existing = patient_service.get_patient_by_id(patient.id)
    if existing:
        raise HTTPException(status_code=400, detail="Patient ID already exists")

    created = patient_service.create_patient(patient)
    return created
