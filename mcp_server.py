"""
MCP Server for Concierge Triage Agent

Exposes the triage agent functionality as MCP tools for AI assistants.
"""

import asyncio
import json
from typing import Any, Optional
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

# Import backend services
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from agents.supervisor import supervisor_agent
from agents.clinical_triage import clinical_triage_agent
from agents.vitals_intake import vitals_intake_agent
from agents.phi_deidentifier import phi_deidentifier
from services.patient_service import patient_service
from services.conversation_service import conversation_service
from services.vitals_service import vitals_service
from services.alert_service import alert_service
from services.rag_service import rag_service
from database import init_db, seed_sample_data

# Initialize database
init_db()
seed_sample_data()

# Create MCP server
server = Server("concierge-triage-agent")

@server.list_resources()
async def handle_list_resources() -> list[Resource]:
    """
    List available resources (patients, conversations, alerts).
    """
    return [
        Resource(
            uri="patients://all",
            name="All Active Patients",
            description="List of all active patients in the system",
            mimeType="application/json",
        ),
        Resource(
            uri="alerts://active",
            name="Active Alerts",
            description="All active clinical alerts requiring attention",
            mimeType="application/json",
        ),
        Resource(
            uri="guidelines://clinical",
            name="Clinical Guidelines",
            description="Post-discharge clinical guidelines and protocols",
            mimeType="text/markdown",
        ),
    ]


@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """
    Read resource content by URI.
    """
    if uri == "patients://all":
        patients = patient_service.list_patients(status="active")
        return json.dumps(patients, indent=2)
    
    elif uri == "alerts://active":
        alerts = alert_service.get_active_alerts()
        return json.dumps(alerts, indent=2)
    
    elif uri == "guidelines://clinical":
        guidelines_path = os.path.join(
            os.path.dirname(__file__), 
            "backend", "data", "clinical_guidelines.md"
        )
        with open(guidelines_path, "r") as f:
            return f.read()
    
    else:
        raise ValueError(f"Unknown resource URI: {uri}")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """
    List available MCP tools.
    """
    return [
        Tool(
            name="start_patient_conversation",
            description="Initiate a new conversation with a patient for post-discharge monitoring",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "string",
                        "description": "Patient ID (e.g., P001, P002)"
                    },
                },
                "required": ["patient_id"],
            },
        ),
        Tool(
            name="send_patient_message",
            description="Send a message to patient and receive agent response with triage analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "string",
                        "description": "Patient ID"
                    },
                    "conversation_id": {
                        "type": "string",
                        "description": "Conversation ID from start_patient_conversation"
                    },
                    "message": {
                        "type": "string",
                        "description": "Patient's message"
                    },
                },
                "required": ["patient_id", "conversation_id", "message"],
            },
        ),
        Tool(
            name="analyze_patient_message",
            description="Analyze a patient message for red flags, urgency, and risk without starting a conversation",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Patient's message to analyze"
                    },
                    "patient_context": {
                        "type": "object",
                        "description": "Patient context (diagnosis, procedure, comorbidities)",
                        "properties": {
                            "diagnosis": {"type": "string"},
                            "procedure": {"type": "string"},
                            "comorbidities": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    },
                },
                "required": ["message"],
            },
        ),
        Tool(
            name="get_patient_summary",
            description="Get comprehensive patient summary including risk score, vitals history, and alerts",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "string",
                        "description": "Patient ID"
                    },
                },
                "required": ["patient_id"],
            },
        ),
        Tool(
            name="extract_vitals",
            description="Extract structured vitals data from natural language (pain, temperature, wound status, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Natural language text containing vitals information"
                    },
                    "vitals_type": {
                        "type": "string",
                        "enum": ["pain_level", "temperature", "wound_status", "medication_adherence", "mobility_status", "appetite"],
                        "description": "Type of vital to extract"
                    },
                },
                "required": ["text", "vitals_type"],
            },
        ),
        Tool(
            name="search_clinical_guidelines",
            description="Search clinical guidelines and discharge instructions using semantic search (RAG)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'when can patient drive after surgery')"
                    },
                    "procedure_type": {
                        "type": "string",
                        "enum": ["cardiac_surgery", "hip_replacement", "appendectomy", "general"],
                        "description": "Type of procedure to filter guidelines"
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="list_active_patients",
            description="List all active patients with their risk scores and status",
            inputSchema={
                "type": "object",
                "properties": {
                    "risk_level": {
                        "type": "string",
                        "enum": ["all", "critical", "high", "moderate", "low"],
                        "description": "Filter by risk level"
                    },
                },
            },
        ),
        Tool(
            name="get_active_alerts",
            description="Get all active clinical alerts that need attention",
            inputSchema={
                "type": "object",
                "properties": {
                    "severity": {
                        "type": "string",
                        "enum": ["all", "critical", "high", "medium", "low"],
                        "description": "Filter by alert severity"
                    },
                },
            },
        ),
        Tool(
            name="deidentify_phi",
            description="Remove Protected Health Information (PHI) from text for HIPAA compliance",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text containing PHI to mask"
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Session ID for reversible masking"
                    },
                },
                "required": ["text", "session_id"],
            },
        ),
    ]



@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent]:
    """
    Handle tool execution.
    """
    if arguments is None:
        arguments = {}
    
    try:
        if name == "start_patient_conversation":
            patient_id = arguments["patient_id"]
            
            # Get patient data
            patient = patient_service.get_patient_by_id(patient_id)
            if not patient:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Patient {patient_id} not found"})
                )]
            
            # Create conversation
            conversation = conversation_service.create_conversation(patient_id)
            
            # Generate initial message
            initial_message = supervisor_agent.get_initial_message(patient)
            
            # Store initial message
            conversation_service.add_message(
                conversation_id=conversation["id"],
                role="agent",
                content=initial_message,
                agent_type="supervisor"
            )
            
            result = {
                "conversation_id": conversation["id"],
                "patient": {
                    "id": patient["id"],
                    "name": f"{patient['first_name']} {patient['last_name']}",
                    "procedure": patient.get("procedure_name"),
                    "discharge_date": patient.get("discharge_date")
                },
                "initial_message": initial_message,
                "status": "conversation_started"
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "send_patient_message":
            patient_id = arguments["patient_id"]
            conversation_id = arguments["conversation_id"]
            message = arguments["message"]
            
            # Get patient and conversation
            patient = patient_service.get_patient_by_id(patient_id)
            conversation = conversation_service.get_conversation(conversation_id)
            
            if not patient or not conversation:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": "Patient or conversation not found"})
                )]
            
            # Store patient message
            conversation_service.add_message(
                conversation_id=conversation_id,
                role="patient",
                content=message
            )
            
            # Get current vitals
            current_vitals = vitals_service.get_conversation_vitals(conversation_id)
            
            # Process through supervisor
            result = await supervisor_agent.process_message(
                user_message=message,
                patient_id=patient_id,
                conversation_state=conversation,
                patient_data=patient,
                current_vitals=current_vitals
            )
            
            # Store agent response
            conversation_service.add_message(
                conversation_id=conversation_id,
                role="agent",
                content=result["response"],
                agent_type=result["agent_type"],
                metadata={
                    "triage": result.get("triage_result"),
                    "vitals_update": result.get("vitals_update")
                }
            )
            
            # Update conversation state
            conversation_service.update_conversation(
                conversation_id=conversation_id,
                current_agent=result["agent_type"],
                completed_checklist=result["checklist_update"],
                escalation_needed=result.get("escalation_needed"),
                escalation_reason=result.get("escalation_reason")
            )
            
            # Record vitals if updated
            vitals_update = result.get("vitals_update", {})
            if vitals_update and vitals_update.get("value") is not None:
                existing_vitals = current_vitals or {}
                new_vitals = {
                    "patient_id": patient_id,
                    "conversation_id": conversation_id,
                    **existing_vitals,
                }
                
                item_id = vitals_update.get("item_id")
                value = vitals_update.get("value")
                if item_id:
                    new_vitals[item_id] = value
                
                vitals_service.record_vitals(**new_vitals)
            
            # Create alerts if needed
            triage = result.get("triage_result", {})
            if triage.get("red_flags"):
                for flag in triage["red_flags"]:
                    alert_service.create_alert(
                        patient_id=patient_id,
                        conversation_id=conversation_id,
                        severity=flag["severity"].lower(),
                        alert_type="red_flag",
                        title=f"Red Flag: {flag['type'].replace('_', ' ').title()}",
                        description=f"Detected in patient message: '{flag['matched']}'",
                        trigger_text=message
                    )
            
            response_data = {
                "conversation_id": conversation_id,
                "agent_response": result["response"],
                "agent_type": result["agent_type"],
                "triage_analysis": {
                    "urgency": triage.get("urgency"),
                    "red_flags": triage.get("red_flags", []),
                    "risk_modifier": triage.get("risk_modifier", 0),
                    "escalation_needed": result.get("escalation_needed")
                },
                "vitals_collected": result.get("vitals_update"),
                "checklist_progress": f"{len(result['checklist_update'])}/6"
            }
            
            return [TextContent(type="text", text=json.dumps(response_data, indent=2))]

        elif name == "analyze_patient_message":
            message = arguments["message"]
            patient_context = arguments.get("patient_context", {})
            
            # Analyze with clinical triage
            triage_result = clinical_triage_agent.analyze_utterance(
                message,
                patient_data=patient_context,
                current_vitals={}
            )
            
            analysis = {
                "message": message,
                "urgency": triage_result["urgency"],
                "red_flags": triage_result["red_flags"],
                "risk_modifier": triage_result["risk_modifier"],
                "escalation_needed": triage_result["escalation_needed"],
                "escalation_reason": triage_result.get("escalation_reason"),
                "triage_note": triage_result["triage_note"],
                "recommendation": "IMMEDIATE ACTION" if triage_result["urgency"] == "EMERGENCY" else "Monitor and follow up"
            }
            
            return [TextContent(type="text", text=json.dumps(analysis, indent=2))]
        
        elif name == "get_patient_summary":
            patient_id = arguments["patient_id"]
            
            # Get comprehensive summary
            summary = patient_service.get_patient_summary(patient_id)
            
            if not summary:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Patient {patient_id} not found"})
                )]
            
            return [TextContent(type="text", text=json.dumps(summary, indent=2))]
        
        elif name == "extract_vitals":
            text = arguments["text"]
            vitals_type = arguments["vitals_type"]
            
            # Map vitals type to checklist item
            from agents.vitals_intake import VITALS_CHECKLIST
            checklist_item = next(
                (item for item in VITALS_CHECKLIST if item["id"] == vitals_type),
                None
            )
            
            if not checklist_item:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Unknown vitals type: {vitals_type}"})
                )]
            
            # Extract using vitals intake agent
            extracted = vitals_intake_agent._extract_with_rules(text, checklist_item)
            
            result = {
                "vitals_type": vitals_type,
                "extracted_value": extracted.get("value"),
                "confidence": extracted.get("confidence"),
                "raw_text": text
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "search_clinical_guidelines":
            query = arguments["query"]
            procedure_type = arguments.get("procedure_type")
            
            # Search using RAG
            filter_metadata = {"discharge_type": procedure_type} if procedure_type and procedure_type != "general" else None
            
            results = rag_service.query(
                query_text=query,
                n_results=3,
                filter_metadata=filter_metadata
            )
            
            search_results = {
                "query": query,
                "procedure_filter": procedure_type,
                "results": [
                    {
                        "content": r["content"],
                        "relevance_score": 1 - r["distance"],
                        "metadata": r.get("metadata", {})
                    }
                    for r in results
                ]
            }
            
            return [TextContent(type="text", text=json.dumps(search_results, indent=2))]
        
        elif name == "list_active_patients":
            risk_level = arguments.get("risk_level", "all")
            
            # Get all active patients
            patients = patient_service.list_patients(status="active")
            
            # Enhance with risk scores
            enhanced_patients = []
            for patient in patients:
                summary = patient_service.get_patient_summary(patient["id"])
                
                patient_data = {
                    "id": patient["id"],
                    "name": f"{patient['first_name']} {patient['last_name']}",
                    "procedure": patient.get("procedure_name"),
                    "discharge_date": patient.get("discharge_date"),
                    "risk_score": summary.get("latest_risk_score"),
                    "risk_category": summary.get("latest_risk_category"),
                    "days_since_discharge": summary.get("days_since_discharge"),
                    "active_alerts": summary.get("active_alerts_count")
                }
                
                # Filter by risk level if specified
                if risk_level == "all":
                    enhanced_patients.append(patient_data)
                elif risk_level.upper() == patient_data.get("risk_category"):
                    enhanced_patients.append(patient_data)
            
            result = {
                "total_patients": len(enhanced_patients),
                "filter": risk_level,
                "patients": enhanced_patients
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "get_active_alerts":
            severity = arguments.get("severity", "all")
            
            # Get active alerts
            if severity == "all":
                alerts = alert_service.get_active_alerts()
            else:
                alerts = [
                    a for a in alert_service.get_active_alerts()
                    if a["severity"].lower() == severity.lower()
                ]
            
            result = {
                "total_alerts": len(alerts),
                "severity_filter": severity,
                "alerts": alerts
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "deidentify_phi":
            text = arguments["text"]
            session_id = arguments["session_id"]
            
            # Deidentify using PHI agent
            masked_text, phi_mapping = phi_deidentifier.deidentify(text, session_id)
            
            result = {
                "original_length": len(text),
                "masked_text": masked_text,
                "phi_entities_masked": len(phi_mapping),
                "session_id": session_id,
                "note": "Use same session_id to re-identify text"
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        else:
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Unknown tool: {name}"})
            )]
    
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({"error": str(e), "tool": name})
        )]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="concierge-triage-agent",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
