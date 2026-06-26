"""
Supervisor Agent - Orchestrates the conversation flow between specialized agents.

Coordinates:
1. PHI Deidentifier (sanitizes input)
2. Vitals Intake Agent (collects structured data)
3. Clinical Triage Agent (detects red flags)
4. Discharge Coach (answers questions via RAG)
"""

import json
from typing import Optional
from google import genai
from google.genai import types
from config import settings
from agents.phi_deidentifier import phi_deidentifier
from agents.vitals_intake import vitals_intake_agent, VITALS_CHECKLIST
from agents.clinical_triage import clinical_triage_agent
from services.rag_service import rag_service


class SupervisorAgent:
    """
    Main orchestrator that coordinates all specialized agents.
    Manages conversation state and routing logic.
    """

    def __init__(self):
        self._client = None
        if settings.GOOGLE_API_KEY:
            self._client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    async def process_message(
        self,
        user_message: str,
        patient_id: str,
        conversation_state: dict,
        patient_data: dict,
        current_vitals: Optional[dict] = None,
    ) -> dict:
        """
        Process a user message through the agent pipeline.

        Args:
            user_message: Raw patient message
            patient_id: Patient identifier
            conversation_state: Current conversation state from DB
            patient_data: Patient record
            current_vitals: Vitals collected during this conversation

        Returns:
            {
                "response": str,
                "agent_type": str,
                "checklist_update": list,
                "vitals_update": dict,
                "triage_result": dict,
                "escalation_needed": bool,
                "escalation_reason": str | None,
            }
        """
        conversation_id = conversation_state.get("id")
        completed_checklist = conversation_state.get("completed_checklist", [])
        if isinstance(completed_checklist, str):
            completed_checklist = json.loads(completed_checklist)

        # Step 1: De-identify PHI
        deidentified_msg, phi_mapping = phi_deidentifier.deidentify(
            user_message, conversation_id
        )

        # Step 2: Run clinical triage on the message (always)
        triage_result = clinical_triage_agent.analyze_utterance(
            deidentified_msg, patient_data, current_vitals
        )

        # Step 3: Determine conversation intent and route accordingly
        intent = await self._classify_intent(deidentified_msg, completed_checklist)

        # Step 4: Route to appropriate agent
        if triage_result["urgency"] == "EMERGENCY":
            # Immediate escalation - don't continue normal flow
            response = await self._generate_emergency_response(
                triage_result, patient_data
            )
            return {
                "response": response,
                "agent_type": "triage",
                "checklist_update": completed_checklist,
                "vitals_update": {},
                "triage_result": triage_result,
                "escalation_needed": True,
                "escalation_reason": triage_result["escalation_reason"],
            }

        if intent == "vitals_collection" and len(completed_checklist) < len(VITALS_CHECKLIST):
            # Continue vitals intake
            result = await self._handle_vitals_collection(
                deidentified_msg,
                completed_checklist,
                patient_data,
                conversation_id,
            )
            result["triage_result"] = triage_result
            result["escalation_needed"] = triage_result["urgency"] in ("EMERGENCY", "URGENT")
            result["escalation_reason"] = triage_result.get("escalation_reason")
            return result

        elif intent == "question":
            # Answer question using RAG
            response = await self._handle_question(
                deidentified_msg,
                patient_data,
                conversation_id,
            )
            return {
                "response": response,
                "agent_type": "discharge_coach",
                "checklist_update": completed_checklist,
                "vitals_update": {},
                "triage_result": triage_result,
                "escalation_needed": triage_result["urgency"] == "URGENT",
                "escalation_reason": triage_result.get("escalation_reason"),
            }

        else:
            # General conversation or vitals complete
            next_question = vitals_intake_agent.get_next_question(
                completed_checklist, patient_data.get("first_name", "there")
            )
            
            if next_question:
                # Start or continue vitals collection
                result = await self._handle_vitals_collection(
                    None,  # No user response yet, just getting started
                    completed_checklist,
                    patient_data,
                    conversation_id,
                    ask_first=True,
                )
                result["triage_result"] = triage_result
                return result
            else:
                # Vitals complete, just chat
                response = await self._generate_conversational_response(
                    deidentified_msg, patient_data, triage_result
                )
                return {
                    "response": response,
                    "agent_type": "supervisor",
                    "checklist_update": completed_checklist,
                    "vitals_update": {},
                    "triage_result": triage_result,
                    "escalation_needed": False,
                    "escalation_reason": None,
                }

    async def _classify_intent(
        self, message: str, completed_checklist: list
    ) -> str:
        """Classify user intent: vitals_collection, question, or general."""
        if not message:
            return "vitals_collection"

        message_lower = message.lower().strip()

        # Question detection
        question_indicators = [
            "can i", "should i", "when can", "how do", "what about",
            "is it okay", "am i allowed", "do i need", "why",
            "what if", "how long", "how much", "?"
        ]
        if any(indicator in message_lower for indicator in question_indicators):
            return "question"

        # Check if we're mid-vitals-collection
        if len(completed_checklist) < len(VITALS_CHECKLIST):
            # Check if this looks like an answer to a vitals question
            answer_indicators = [
                str(i) for i in range(1, 11)  # Numbers 1-10 for pain scale
            ] + ["yes", "no", "good", "fine", "okay", "better", "worse"]

            # Simple heuristic: if message is short and has answer-like content
            words = message_lower.split()
            if len(words) <= 10 and any(word in message_lower for word in answer_indicators):
                return "vitals_collection"

        return "general"

    async def _handle_vitals_collection(
        self,
        user_message: Optional[str],
        completed_checklist: list,
        patient_data: dict,
        conversation_id: str,
        ask_first: bool = False,
    ) -> dict:
        """Handle vitals intake flow."""
        patient_name = patient_data.get("first_name", "there")

        if ask_first or not user_message:
            # Start vitals collection
            next_question = vitals_intake_agent.get_next_question(
                completed_checklist, patient_name
            )
            if next_question:
                response = (
                    f"Hi {patient_name}, I'm calling from your care team to check in "
                    f"on your recovery. Let me ask you a few quick questions. "
                    f"{next_question['question']}"
                )
                return {
                    "response": response,
                    "agent_type": "vitals",
                    "checklist_update": completed_checklist,
                    "vitals_update": {},
                    "current_checklist_item": next_question["id"],
                }

        # Find the current checklist item (first incomplete one)
        current_item = None
        for item in VITALS_CHECKLIST:
            if item["id"] not in completed_checklist:
                current_item = item
                break

        if not current_item:
            # All vitals collected
            response = (
                f"Thank you, {patient_name}. That completes our daily check-in. "
                f"Your care team will review your responses. Is there anything "
                f"else you'd like to discuss?"
            )
            return {
                "response": response,
                "agent_type": "supervisor",
                "checklist_update": completed_checklist,
                "vitals_update": {},
            }

        # Extract vitals from response
        extracted = await vitals_intake_agent.extract_vitals_from_response(
            user_message, current_item["id"]
        )

        # Update checklist
        new_checklist = completed_checklist + [current_item["id"]]

        # Get next question
        next_question = vitals_intake_agent.get_next_question(new_checklist, patient_name)

        # Generate empathetic response
        response = await vitals_intake_agent.generate_empathetic_response(
            current_item["id"], extracted, next_question, patient_name
        )

        return {
            "response": response,
            "agent_type": "vitals",
            "checklist_update": new_checklist,
            "vitals_update": {
                "item_id": current_item["id"],
                "value": extracted.get("value"),
                "confidence": extracted.get("confidence", 0.0),
                "raw": extracted.get("raw"),
            },
        }

    async def _handle_question(
        self,
        message: str,
        patient_data: dict,
        conversation_id: str,
    ) -> str:
        """Handle patient question using RAG."""
        discharge_summary_id = patient_data.get("discharge_summary_id")
        patient_context = (
            f"Patient: {patient_data.get('first_name', '')} "
            f"Procedure: {patient_data.get('procedure_name', '')} "
            f"Discharged: {patient_data.get('discharge_date', '')}"
        )

        response = rag_service.generate_rag_response(
            patient_id=patient_data.get("id"),
            discharge_summary_id=discharge_summary_id,
            question=message,
            patient_context=patient_context,
        )

        return response

    async def _generate_emergency_response(
        self, triage_result: dict, patient_data: dict
    ) -> str:
        """Generate response for emergency situation."""
        name = patient_data.get("first_name", "there")
        
        if triage_result["urgency"] == "EMERGENCY":
            return (
                f"{name}, what you're describing sounds serious and needs immediate "
                f"attention. I'm going to connect you with emergency services right away. "
                f"If you're able, please call 911 or have someone take you to the nearest "
                f"emergency room immediately. Do not wait. I'm also alerting your care team "
                f"right now."
            )
        else:
            return (
                f"{name}, I'm concerned about what you're telling me. This needs to be "
                f"reviewed by your care team within the next few hours. I'm flagging this "
                f"as urgent and someone from your care team will reach out to you shortly. "
                f"If things get worse before then, please call 911 or go to the emergency room."
            )

    async def _generate_conversational_response(
        self, message: str, patient_data: dict, triage_result: dict
    ) -> str:
        """Generate a general conversational response."""
        if not self._client:
            return self._generate_scripted_response(message, patient_data)

        prompt = f"""You are a caring post-discharge nurse on a check-in call.
The patient just said: "{message}"

Patient context:
- Name: {patient_data.get('first_name', 'Patient')}
- Procedure: {patient_data.get('procedure_name', 'surgery')}
- Days since discharge: Based on {patient_data.get('discharge_date', 'recently')}

Generate a brief (1-2 sentences), warm, empathetic response.
- Do NOT give medical advice
- Do NOT prescribe or diagnose
- If they need help, suggest contacting their care team
- Keep it conversational and caring

Response:"""

        try:
            response = self._client.models.generate_content(
                model=settings.LLM_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=150,
                ),
            )
            return response.text.strip()
        except Exception:
            return self._generate_scripted_response(message, patient_data)

    def _generate_scripted_response(self, message: str, patient_data: dict) -> str:
        """Fallback scripted response."""
        name = patient_data.get("first_name", "there")
        return (
            f"Thank you for sharing that with me, {name}. "
            f"If you have any questions about your recovery, I'm here to help. "
            f"Is there anything specific you'd like to discuss?"
        )

    def get_initial_message(self, patient_data: dict) -> str:
        """Generate the opening message for a new conversation."""
        name = patient_data.get("first_name", "there")
        return (
            f"Hello, this is your care team's automated follow-up system. "
            f"Am I speaking with {name}? I'd like to ask you a few quick questions "
            f"about how you're recovering from your {patient_data.get('procedure_name', 'procedure')}."
        )


# Singleton
supervisor_agent = SupervisorAgent()
