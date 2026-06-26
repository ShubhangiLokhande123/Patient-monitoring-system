"""Pydantic models for alerts and risk scores."""

from pydantic import BaseModel
from typing import Optional


class Alert(BaseModel):
    id: Optional[int] = None
    patient_id: str
    conversation_id: Optional[str] = None
    severity: str  # 'critical' | 'high' | 'medium' | 'low'
    alert_type: str  # 'red_flag' | 'low_confidence' | 'escalation' | 'risk_change'
    title: str
    description: str
    trigger_text: Optional[str] = None
    status: str = "active"  # 'active' | 'acknowledged' | 'dismissed'
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None
    created_at: Optional[str] = None


class RiskScore(BaseModel):
    id: Optional[int] = None
    patient_id: str
    conversation_id: Optional[str] = None
    score: int  # 0-100
    category: str  # 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL'
    lace_l: int = 0
    lace_a: int = 0
    lace_c: int = 0
    lace_e: int = 0
    vitals_modifier: int = 0
    breakdown: dict = {}
    calculated_at: Optional[str] = None


class AlertUpdate(BaseModel):
    status: str  # 'acknowledged' | 'dismissed'
    acknowledged_by: str = "clinician"


class DashboardStats(BaseModel):
    active_patients: int = 0
    calls_today: int = 0
    avg_risk_score: float = 0.0
    pending_alerts: int = 0
    high_risk_patients: int = 0
    escalations_today: int = 0
    risk_distribution: dict = {}
