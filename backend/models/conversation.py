"""Pydantic models for conversations and messages."""

from pydantic import BaseModel
from typing import Optional


class Message(BaseModel):
    id: Optional[int] = None
    conversation_id: str
    role: str  # 'patient' | 'agent' | 'system'
    content: str
    deidentified_content: Optional[str] = None
    agent_type: Optional[str] = None  # 'supervisor' | 'vitals' | 'discharge_coach' | 'triage'
    metadata: dict = {}
    created_at: Optional[str] = None


class Conversation(BaseModel):
    id: str
    patient_id: str
    status: str = "active"  # 'active' | 'completed' | 'escalated'
    call_type: str = "daily_checkin"
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    current_agent: str = "supervisor"
    completed_checklist: list[str] = []
    escalation_needed: bool = False
    escalation_reason: Optional[str] = None
    summary: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    patient_id: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    agent_type: str
    risk_score: Optional[int] = None
    risk_category: Optional[str] = None
    alert_triggered: bool = False
    alert_severity: Optional[str] = None
    escalation_needed: bool = False
    metadata: dict = {}
