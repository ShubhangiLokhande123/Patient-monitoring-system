"""
Agent 5: Clinical Triage & Red Flag Detection Agent

Runs on every patient utterance to detect critical symptoms,
calculate risk scores, and trigger escalation when needed.
"""

import re
import json
from typing import Optional
from google import genai
from google.genai import types
from config import settings


# Red flag keyword patterns organized by severity
RED_FLAG_PATTERNS = {
    "EMERGENCY": {
        "chest_pain": [
            r"chest\s*pain",
            r"chest\s*pressure",
            r"chest\s*tight",
            r"squeezing\s*(in|my)\s*chest",
            r"heart\s*attack",
        ],
        "breathing": [
            r"can'?t\s*breathe",
            r"shortness\s*of\s*breath",
            r"difficulty\s*breathing",
            r"hard\s*to\s*breathe",
            r"gasping",
            r"struggling\s*to\s*breathe",
        ],
        "stroke": [
            r"face\s*droop",
            r"arm\s*weak",
            r"slurred\s*speech",
            r"can'?t\s*(speak|talk)",
            r"numb\s*(one\s*side|left|right)",
            r"vision\s*(change|loss|blurr)",
        ],
        "bleeding": [
            r"won'?t\s*stop\s*bleeding",
            r"uncontroll\w*\s*bleed",
            r"heavy\s*bleeding",
            r"soaked?\s*(through|bandage|dressing)",
        ],
        "consciousness": [
            r"passed?\s*out",
            r"fainted",
            r"unconscious",
            r"black\w*\s*out",
            r"can'?t\s*stay\s*awake",
        ],
        "severe_pain": [
            r"worst\s*pain\s*(ever|of\s*my\s*life)",
            r"pain\s*(is\s*)?(a\s*)?10",
            r"excruciating",
            r"unbearable\s*pain",
        ],
        "blood_clot": [
            r"cough\w*\s*(up\s*)?blood",
            r"leg\s*(is\s*)?(very\s*)?swollen.*red",
            r"calf\s*(pain|swelling|red)",
            r"sudden\s*leg\s*(pain|swelling)",
        ],
    },
    "URGENT": {
        "fever": [
            r"fever",
            r"temperature\s*(is\s*)?(over|above)\s*10[1-9]",
            r"10[1-9](\.\d+)?\s*(degree|°)",
            r"feel\w*\s*(very\s*)?hot",
            r"chills\s*and\s*shak",
        ],
        "wound": [
            r"wound\s*(is\s*)?(red|swollen|draining|oozing)",
            r"incision\s*(is\s*)?(red|open|leaking)",
            r"pus\s*(from|coming)",
            r"wound\s*smell",
            r"infection",
        ],
        "worsening_pain": [
            r"pain\s*(is\s*)?(getting\s*)?worse",
            r"pain\s*(is\s*)?(a\s*)?[7-9]",
            r"more\s*pain\s*than\s*(yesterday|before)",
            r"new\s*pain",
        ],
        "vomiting": [
            r"can'?t\s*keep\s*(anything|food|water)\s*down",
            r"vomit\w*\s*(all\s*day|constantly|non.?stop)",
            r"throwing\s*up\s*(everything|a\s*lot)",
            r"persistent\s*nausea",
        ],
        "confusion": [
            r"(feel|feeling)\s*confused",
            r"can'?t\s*(think|concentrate|remember)",
            r"disoriented",
            r"don'?t\s*know\s*where\s*i\s*am",
        ],
        "swelling": [
            r"(leg|arm|ankle|foot)\s*(is\s*)?(very\s*)?swollen",
            r"sudden\s*swelling",
            r"gained\s*(\d+\s*)?pounds?\s*(overnight|today)",
            r"weight\s*gain",
        ],
    },
}


class ClinicalTriageAgent:
    """
    Background agent that analyzes every patient utterance for red flags
    and calculates real-time risk scores.
    """

    def __init__(self):
        self._client = None
        if settings.GOOGLE_API_KEY:
            self._client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    def analyze_utterance(
        self,
        text: str,
        patient_data: Optional[dict] = None,
        current_vitals: Optional[dict] = None,
    ) -> dict:
        """
        Analyze a patient utterance for red flags and urgency.

        Returns:
            {
                "urgency": "EMERGENCY" | "URGENT" | "ROUTINE" | "SELF_CARE",
                "red_flags": [{"type": str, "category": str, "matched": str}],
                "risk_modifier": int,
                "escalation_needed": bool,
                "escalation_reason": str | None,
                "triage_note": str,
            }
        """
        # Step 1: Pattern-based red flag detection
        red_flags = self._detect_red_flags(text)

        # Step 2: Determine urgency from detected flags
        urgency = self._classify_urgency(red_flags)

        # Step 3: Calculate risk modifier from current conversation
        risk_modifier = self._calculate_risk_modifier(
            red_flags, current_vitals
        )

        # Step 4: Determine if escalation is needed
        escalation_needed = urgency in ("EMERGENCY", "URGENT")
        escalation_reason = None
        if urgency == "EMERGENCY":
            flag_types = [f["type"] for f in red_flags]
            escalation_reason = (
                f"Emergency red flag detected: {', '.join(flag_types)}. "
                f"Immediate clinical assessment required."
            )
        elif urgency == "URGENT":
            flag_types = [f["type"] for f in red_flags]
            escalation_reason = (
                f"Urgent symptoms reported: {', '.join(flag_types)}. "
                f"Clinician callback recommended within 4 hours."
            )

        # Step 5: Generate triage note
        triage_note = self._generate_triage_note(
            red_flags, urgency, current_vitals
        )

        return {
            "urgency": urgency,
            "red_flags": red_flags,
            "risk_modifier": risk_modifier,
            "escalation_needed": escalation_needed,
            "escalation_reason": escalation_reason,
            "triage_note": triage_note,
        }

    def _detect_red_flags(self, text: str) -> list[dict]:
        """Scan text against red flag patterns."""
        flags = []
        text_lower = text.lower()

        for severity, categories in RED_FLAG_PATTERNS.items():
            for category, patterns in categories.items():
                for pattern in patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        flags.append(
                            {
                                "type": category,
                                "severity": severity,
                                "matched": match.group(),
                                "pattern": pattern,
                            }
                        )
                        break  # One match per category is enough

        return flags

    def _classify_urgency(self, red_flags: list[dict]) -> str:
        """Classify overall urgency from detected red flags."""
        if not red_flags:
            return "SELF_CARE"

        severities = {f["severity"] for f in red_flags}
        if "EMERGENCY" in severities:
            return "EMERGENCY"
        if "URGENT" in severities:
            return "URGENT"
        return "ROUTINE"

    def _calculate_risk_modifier(
        self,
        red_flags: list[dict],
        current_vitals: Optional[dict] = None,
    ) -> int:
        """Calculate risk score modifier from current findings."""
        modifier = 0

        # Red flag modifiers
        for flag in red_flags:
            if flag["severity"] == "EMERGENCY":
                modifier += 25
            elif flag["severity"] == "URGENT":
                modifier += 10

        # Vitals-based modifiers
        if current_vitals:
            pain = current_vitals.get("pain_level")
            if pain is not None and pain >= 7:
                modifier += 10

            temp = current_vitals.get("temperature")
            if temp is not None:
                if temp > 101:
                    modifier += 25
                elif temp > 100.4:
                    modifier += 15

            if current_vitals.get("medication_adherence") == 0:
                modifier += 15

            if current_vitals.get("wound_status") in (
                "concerning",
                "infected",
                "red",
                "draining",
            ):
                modifier += 10

            if current_vitals.get("mobility_status") in (
                "unable",
                "bedbound",
            ):
                modifier += 10

        return min(modifier, 50)  # Cap modifier at 50

    def _generate_triage_note(
        self,
        red_flags: list[dict],
        urgency: str,
        current_vitals: Optional[dict] = None,
    ) -> str:
        """Generate a clinical triage note summarizing findings."""
        if not red_flags:
            return "No red flags detected. Patient interaction is routine."

        note_parts = [f"Triage Level: {urgency}"]
        note_parts.append(
            f"Red Flags Detected ({len(red_flags)}):"
        )
        for flag in red_flags:
            note_parts.append(
                f"  - [{flag['severity']}] {flag['type']}: "
                f"matched '{flag['matched']}'"
            )

        if urgency == "EMERGENCY":
            note_parts.append(
                "\nACTION REQUIRED: Immediate clinical escalation. "
                "Patient should be assessed by medical professional or "
                "directed to emergency services."
            )
        elif urgency == "URGENT":
            note_parts.append(
                "\nACTION REQUIRED: Clinician callback recommended "
                "within 4 hours. Monitor for symptom progression."
            )

        return "\n".join(note_parts)

    async def get_llm_triage_assessment(
        self, text: str, patient_context: str
    ) -> Optional[dict]:
        """
        Use LLM for nuanced triage assessment beyond keyword matching.
        Fallback/supplement to pattern-based detection.
        """
        if not self._client:
            return None

        prompt = f"""You are a clinical triage assistant. Analyze the following patient statement for any concerning symptoms or red flags.

Patient Context: {patient_context}

Patient Statement: "{text}"

Respond in JSON format:
{{
    "concerning": true/false,
    "symptoms_identified": ["list of symptoms"],
    "urgency_assessment": "EMERGENCY|URGENT|ROUTINE|SELF_CARE",
    "reasoning": "brief clinical reasoning"
}}

Only respond with JSON, no other text."""

        try:
            response = self._client.models.generate_content(
                model=settings.LLM_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=500,
                ),
            )
            text_response = response.text.strip()
            # Clean markdown code fences if present
            if text_response.startswith("```"):
                text_response = text_response.split("\n", 1)[-1]
                text_response = text_response.rsplit("```", 1)[0]
            return json.loads(text_response)
        except Exception:
            return None


# Singleton instance
clinical_triage_agent = ClinicalTriageAgent()
