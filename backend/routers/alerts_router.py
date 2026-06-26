"""
Alerts router - handles alerts and dashboard data.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from models.alerts import Alert, AlertUpdate, DashboardStats
from services.alert_service import alert_service

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/")
async def list_alerts(
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
):
    """Get all alerts, optionally filtered."""
    alerts = alert_service.get_all_alerts(status, severity)
    return {"alerts": alerts, "count": len(alerts)}


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard():
    """Get dashboard statistics."""
    return alert_service.get_dashboard_stats()


@router.get("/{alert_id}")
async def get_alert(alert_id: int):
    """Get an alert by ID."""
    alert = alert_service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int, update: AlertUpdate):
    """Acknowledge an alert."""
    alert = alert_service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    updated = alert_service.acknowledge_alert(alert_id, update.acknowledged_by)
    return {"status": "acknowledged", "alert": updated}


@router.post("/{alert_id}/dismiss")
async def dismiss_alert(alert_id: int, update: AlertUpdate):
    """Dismiss an alert."""
    alert = alert_service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    updated = alert_service.dismiss_alert(alert_id, update.acknowledged_by)
    return {"status": "dismissed", "alert": updated}


@router.get("/patient/{patient_id}")
async def get_patient_alerts(
    patient_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """Get alerts for a specific patient."""
    alerts = alert_service.get_patient_alerts(patient_id, status)
    return {"alerts": alerts, "count": len(alerts)}
