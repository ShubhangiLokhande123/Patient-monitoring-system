"""
Chat/Conversation router - handles patient conversations.
"""

import json
from fastapi import APIRouter, HTTPException
from models.conversation import ChatRequest, ChatResponse, Conversation, Message
from services.conversation_service import conversation_service
from services.patient_service import patient_service
from services.vitals_service import vitals_service
from services.alert_service import alert_service
from agents.supervisor import supervisor_agent
from agents.phi_deidentifier import phi_deidentifier

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a patient message and return agent response.
    
    Creates or continues a conversation, processes the message through
    the agent pipeline, and returns the response.
    """
    # Verify patient exists
    patient = patient_service.get_patient_by_id(request.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Get or create conversation
    if request.conversation_id:
        conversation = conversation_service.get_conversation(request.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation["patient_id"] != request.patient_id:
            raise HTTPException(status_code=403, detail="Conversation does not belong to patient")
    else:
        conversation = conversation_service.get_active_conversation(request.patient_id)
        if not conversation:
            conversation = conversation_service.create_conversation(request.patient_id)

    conversation_id = conversation["id"]

    # Store patient message
    conversation_service.add_message(
        conversation_id=conversation_id,
        role="patient",
        content=request.message,
    )

    # Get current vitals for this conversation
    current_vitals = vitals_service.get_conversation_vitals(conversation_id)
    if current_vitals:
        current_vitals = {
            "pain_level": current_vitals.get("pain_level"),
            "temperature": current_vitals.get("temperature"),
            "wound_status": current_vitals.get("wound_status"),
            "medication_adherence": bool(current_vitals.get("medication_adherence"))
            if current_vitals.get("medication_adherence") is not None
            else None,
            "mobility_status": current_vitals.get("mobility_status"),
            "appetite": current_vitals.get("appetite"),
        }

    # Process through supervisor agent
    result = await supervisor_agent.process_message(
        user_message=request.message,
        patient_id=request.patient_id,
        conversation_state=conversation,
        patient_data=patient,
        current_vitals=current_vitals,
    )

    # Store agent response
    conversation_service.add_message(
        conversation_id=conversation_id,
        role="agent",
        content=result["response"],
        agent_type=result["agent_type"],
        metadata={
            "triage": result.get("triage_result"),
            "vitals_update": result.get("vitals_update"),
        },
    )

    # Update conversation state
    completed_checklist = result["checklist_update"]
    conversation_service.update_conversation(
        conversation_id=conversation_id,
        current_agent=result["agent_type"],
        completed_checklist=completed_checklist,
        escalation_needed=result.get("escalation_needed"),
        escalation_reason=result.get("escalation_reason"),
    )

    # Record vitals if updated
    vitals_update = result.get("vitals_update", {})
    if vitals_update and vitals_update.get("value") is not None:
        # Build vitals record progressively
        existing_vitals = current_vitals or {}
        new_vitals = {
            "patient_id": request.patient_id,
            "conversation_id": conversation_id,
            **existing_vitals,
        }
        
        # Update the specific vitals field
        item_id = vitals_update.get("item_id")
        value = vitals_update.get("value")
        if item_id == "pain_level":
            new_vitals["pain_level"] = value
        elif item_id == "temperature":
            new_vitals["temperature"] = value
        elif item_id == "wound_status":
            new_vitals["wound_status"] = value
        elif item_id == "medication_adherence":
            new_vitals["medication_adherence"] = value
        elif item_id == "mobility_status":
            new_vitals["mobility_status"] = value
        elif item_id == "appetite":
            new_vitals["appetite"] = value

        vitals_service.record_vitals(**new_vitals)

    # Create alert if needed
    triage = result.get("triage_result", {})
    if triage.get("red_flags"):
        for flag in triage["red_flags"]:
            alert_service.create_alert(
                patient_id=request.patient_id,
                conversation_id=conversation_id,
                severity=flag["severity"].lower(),
                alert_type="red_flag",
                title=f"Red Flag: {flag['type'].replace('_', ' ').title()}",
                description=f"Detected in patient message: '{flag['matched']}'",
                trigger_text=request.message,
            )

    # Calculate and record risk score if triage modifier
    risk_modifier = triage.get("risk_modifier", 0)
    if risk_modifier > 0:
        # Get base LACE score from patient history
        latest_risk = alert_service.get_latest_risk_score(request.patient_id)
        base_score = latest_risk["score"] if latest_risk else 50

        # Apply modifier (with cap)
        new_score = min(100, base_score + risk_modifier)
        category = (
            "CRITICAL"
            if new_score >= 85
            else "HIGH"
            if new_score >= 70
            else "MODERATE"
            if new_score >= 40
            else "LOW"
        )

        alert_service.record_risk_score(
            patient_id=request.patient_id,
            conversation_id=conversation_id,
            score=new_score,
            category=category,
            vitals_modifier=risk_modifier,
            breakdown=triage,
        )

    # Re-identify PHI in response if needed
    response_text = result["response"]
    # Note: In production, we'd want to re-identify if we used de-identified context
    # For now, responses are generated fresh so no re-identification needed

    return ChatResponse(
        conversation_id=conversation_id,
        response=response_text,
        agent_type=result["agent_type"],
        risk_score=new_score if risk_modifier > 0 else None,
        risk_category=category if risk_modifier > 0 else None,
        alert_triggered=len(triage.get("red_flags", [])) > 0,
        alert_severity=triage["red_flags"][0]["severity"].lower()
        if triage.get("red_flags")
        else None,
        escalation_needed=result.get("escalation_needed", False),
        metadata={"checklist_progress": len(completed_checklist)},
    )


@router.post("/start/{patient_id}", response_model=ChatResponse)
async def start_conversation(patient_id: str):
    """
    Start a new conversation with a patient.
    
    Returns the initial greeting message.
    """
    patient = patient_service.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Check for existing active conversation
    existing = conversation_service.get_active_conversation(patient_id)
    if existing:
        # Resume existing conversation
        messages = conversation_service.get_conversation_messages(existing["id"])
        last_agent_msg = next(
            (m for m in reversed(messages) if m["role"] == "agent"),
            None,
        )
        if last_agent_msg:
            return ChatResponse(
                conversation_id=existing["id"],
                response="We were in the middle of a check-in. Let's continue where we left off.",
                agent_type=existing.get("current_agent", "supervisor"),
            )

    # Create new conversation
    conversation = conversation_service.create_conversation(patient_id)

    # Generate initial message
    initial_msg = supervisor_agent.get_initial_message(patient)

    # Store initial message
    conversation_service.add_message(
        conversation_id=conversation["id"],
        role="agent",
        content=initial_msg,
        agent_type="supervisor",
    )

    return ChatResponse(
        conversation_id=conversation["id"],
        response=initial_msg,
        agent_type="supervisor",
    )


@router.get("/{conversation_id}/messages")
async def get_messages(conversation_id: str):
    """Get all messages in a conversation."""
    conversation = conversation_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = conversation_service.get_conversation_messages(conversation_id)
    return {"conversation": conversation, "messages": messages}


@router.post("/{conversation_id}/end")
async def end_conversation(conversation_id: str):
    """End a conversation."""
    conversation = conversation_service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Clear PHI session
    phi_deidentifier.clear_session(conversation_id)

    # End conversation
    conversation_service.end_conversation(conversation_id)

    return {"status": "completed", "conversation_id": conversation_id}
