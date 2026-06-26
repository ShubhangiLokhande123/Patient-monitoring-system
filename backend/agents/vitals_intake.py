"""
Agent 3: Vitals & Intake Agent

Follows a structured checklist to collect daily monitoring data
from patients through natural conversation. Extracts structured
JSON from natural language responses.
"""

import json
from typing import Optional
from google import genai
from google.genai import types
from config import settings


# The structured daily checklist
VITALS_CHECKLIST = [
    {
        "id": "pain_level",
        "question": "On a scale of 1 to 10, where 1 is no pain and 10 is the worst pain imaginable, how would you rate your pain right now?",
        "extract_type": "integer",
        "range": [1, 10],
    },
    {
        "id": "temperature",
        "question": "Have you been able to check your temperature today? If so, what was it?",
        "extract_type": "float",
        "optional": True,
    },
    {
        "id": "wound_status",
        "question": "How does your surgical wound look today? Any redness, swelling, or drainage?",
        "extract_type": "categorical",
        "categories": ["normal", "mild_concern", "concerning", "unknown"],
    },
    {
        "id": "medication_adherence",
        "question": "Have you been able to take all your medications as prescribed today?",
        "extract_type": "boolean",
    },
    {
        "id": "mobility_status",
        "question": "Have you been able to walk around today? How is your mobility compared to yesterday?",
        "extract_type": "categorical",
        "categories": [
            "improving",
            "stable",
            "declining",
            "unable",
            "unknown",
        ],
    },
    {
        "id": "appetite",
        "question": "How has your appetite been? Have you been eating and drinking well?",
        "extract_type": "categorical",
        "categories": ["good", "fair", "poor", "none"],
    },
]


class VitalsIntakeAgent:
    """
    Conducts structured vitals collection through empathetic conversation.
    """

    def __init__(self):
        self._client = None
        if settings.GOOGLE_API_KEY:
            self._client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    def get_next_question(
        self, completed_items: list[str], patient_name: str = "there"
    ) -> Optional[dict]:
        """
        Get the next checklist item to ask about.

        Returns:
            {"id": str, "question": str} or None if checklist is complete
        """
        for item in VITALS_CHECKLIST:
            if item["id"] not in completed_items:
                return {"id": item["id"], "question": item["question"]}
        return None

    def get_checklist_progress(self, completed_items: list[str]) -> dict:
        """Get completion progress of the vitals checklist."""
        total = len(VITALS_CHECKLIST)
        completed = len(
            [i for i in completed_items if i in [c["id"] for c in VITALS_CHECKLIST]]
        )
        return {
            "total": total,
            "completed": completed,
            "remaining": total - completed,
            "percent": round((completed / total) * 100) if total > 0 else 0,
        }

    async def extract_vitals_from_response(
        self, user_response: str, checklist_item_id: str
    ) -> dict:
        """
        Extract structured data from natural language response.

        Returns:
            {"value": extracted_value, "confidence": float, "raw": str}
        """
        item = next(
            (i for i in VITALS_CHECKLIST if i["id"] == checklist_item_id),
            None,
        )
        if not item:
            return {"value": None, "confidence": 0.0, "raw": user_response}

        if self._client:
            return await self._extract_with_llm(user_response, item)
        else:
            return self._extract_with_rules(user_response, item)

    async def _extract_with_llm(
        self, user_response: str, item: dict
    ) -> dict:
        """Use LLM to extract structured data from natural language."""
        prompt = f"""Extract the following information from the patient's response.

Question asked: "{item['question']}"
Patient's response: "{user_response}"
Expected data type: {item['extract_type']}
"""
        if item["extract_type"] == "categorical":
            prompt += f"Valid categories: {item.get('categories', [])}\n"
        if item["extract_type"] == "integer" and "range" in item:
            prompt += f"Valid range: {item['range'][0]} to {item['range'][1]}\n"

        prompt += """
Respond in JSON format only:
{
    "value": <extracted value or null if unclear>,
    "confidence": <0.0 to 1.0>,
    "interpretation": "<brief note on what you understood>"
}"""

        try:
            response = self._client.models.generate_content(
                model=settings.LLM_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=200,
                ),
            )
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1]
                text = text.rsplit("```", 1)[0]
            result = json.loads(text)
            result["raw"] = user_response
            return result
        except Exception:
            return self._extract_with_rules(user_response, item)

    def _extract_with_rules(self, user_response: str, item: dict) -> dict:
        """Fallback rule-based extraction."""
        response_lower = user_response.lower().strip()

        if item["extract_type"] == "integer":
            # Try to find a number
            import re
            numbers = re.findall(r"\b(\d+)\b", response_lower)
            if numbers:
                val = int(numbers[0])
                if "range" in item:
                    val = max(item["range"][0], min(item["range"][1], val))
                return {
                    "value": val,
                    "confidence": 0.8,
                    "raw": user_response,
                }

        elif item["extract_type"] == "float":
            import re
            numbers = re.findall(r"\b(\d+\.?\d*)\b", response_lower)
            if numbers:
                return {
                    "value": float(numbers[0]),
                    "confidence": 0.7,
                    "raw": user_response,
                }

        elif item["extract_type"] == "boolean":
            positive = ["yes", "yeah", "yep", "sure", "i did", "all of them", "took them"]
            negative = ["no", "nope", "didn't", "forgot", "missed", "couldn't"]
            for word in positive:
                if word in response_lower:
                    return {
                        "value": True,
                        "confidence": 0.8,
                        "raw": user_response,
                    }
            for word in negative:
                if word in response_lower:
                    return {
                        "value": False,
                        "confidence": 0.8,
                        "raw": user_response,
                    }

        elif item["extract_type"] == "categorical":
            categories = item.get("categories", [])
            # Simple keyword matching
            category_keywords = {
                "normal": ["normal", "fine", "good", "looks good", "okay", "no change"],
                "mild_concern": ["little", "slightly", "bit", "minor"],
                "concerning": ["red", "swollen", "draining", "infected", "pus", "worse", "bad"],
                "improving": ["better", "improving", "easier", "more"],
                "stable": ["same", "no change", "stable", "about the same"],
                "declining": ["worse", "harder", "less", "declining"],
                "unable": ["can't", "unable", "not able", "haven't"],
                "good": ["good", "great", "well", "fine", "normal", "eating"],
                "fair": ["okay", "so-so", "some", "a little"],
                "poor": ["poor", "bad", "not much", "barely", "not really"],
                "none": ["nothing", "none", "haven't eaten", "can't eat"],
            }
            for cat in categories:
                keywords = category_keywords.get(cat, [])
                for kw in keywords:
                    if kw in response_lower:
                        return {
                            "value": cat,
                            "confidence": 0.7,
                            "raw": user_response,
                        }

        return {
            "value": None,
            "confidence": 0.3,
            "raw": user_response,
        }

    async def generate_empathetic_response(
        self,
        checklist_item_id: str,
        extracted_value: dict,
        next_question: Optional[dict],
        patient_name: str = "there",
    ) -> str:
        """
        Generate an empathetic acknowledgment + transition to next question.
        """
        if self._client:
            return await self._generate_with_llm(
                checklist_item_id, extracted_value, next_question, patient_name
            )
        else:
            return self._generate_scripted(
                checklist_item_id, extracted_value, next_question, patient_name
            )

    async def _generate_with_llm(
        self,
        checklist_item_id: str,
        extracted_value: dict,
        next_question: Optional[dict],
        patient_name: str,
    ) -> str:
        """Use LLM for empathetic response generation."""
        prompt = f"""You are a caring post-discharge nurse conducting a daily check-in call.
The patient just answered a question about their {checklist_item_id.replace('_', ' ')}.
Their response: "{extracted_value.get('raw', '')}"
Extracted value: {extracted_value.get('value')}

Generate a brief (1-2 sentences), warm, empathetic acknowledgment of their answer.
{"Then naturally transition to asking: " + next_question['question'] if next_question else "Then let them know that completes the daily check-in questions."}

Keep your response conversational and caring, like a nurse on a phone call. Do not use bullet points or formatting. 
Do NOT prescribe, diagnose, or give medical advice. Simply acknowledge and transition."""

        try:
            response = self._client.models.generate_content(
                model=settings.LLM_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=200,
                ),
            )
            return response.text.strip()
        except Exception:
            return self._generate_scripted(
                checklist_item_id, extracted_value, next_question, patient_name
            )

    def _generate_scripted(
        self,
        checklist_item_id: str,
        extracted_value: dict,
        next_question: Optional[dict],
        patient_name: str,
    ) -> str:
        """Fallback scripted responses."""
        ack = "Thank you for sharing that with me."

        if checklist_item_id == "pain_level":
            val = extracted_value.get("value")
            if val and val <= 3:
                ack = "That's great to hear that your pain is manageable."
            elif val and val <= 6:
                ack = "I've noted your pain level. It's important to stay on top of your pain medication."
            elif val and val >= 7:
                ack = "I'm sorry to hear your pain is that high. I'll make sure your care team is aware."

        elif checklist_item_id == "medication_adherence":
            if extracted_value.get("value") is True:
                ack = "That's wonderful that you're staying on track with your medications."
            else:
                ack = "I understand. It's really important to take your medications as prescribed. I'll note this for your care team."

        if next_question:
            return f"{ack} Now, {next_question['question']}"
        else:
            return f"{ack} That completes our daily check-in. Your care team will review your responses. Is there anything else you'd like to discuss?"


# Singleton instance
vitals_intake_agent = VitalsIntakeAgent()
