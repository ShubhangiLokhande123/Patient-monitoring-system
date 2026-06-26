"""
Unit tests for Clinical Triage Agent

Tests red flag detection, urgency classification, and risk scoring.
"""

import pytest
from agents.clinical_triage import clinical_triage_agent


class TestRedFlagDetection:
    """Test pattern-based red flag detection."""
    
    def test_emergency_chest_pain(self):
        """Should detect emergency: chest pain."""
        result = clinical_triage_agent.analyze_utterance(
            "I have severe chest pain and pressure"
        )
        assert result["urgency"] == "EMERGENCY"
        assert any(flag["type"] == "chest_pain" for flag in result["red_flags"])
        assert result["escalation_needed"] is True
    
    def test_emergency_breathing(self):
        """Should detect emergency: difficulty breathing."""
        result = clinical_triage_agent.analyze_utterance(
            "I can't breathe properly, struggling to catch my breath"
        )
        assert result["urgency"] == "EMERGENCY"
        assert any(flag["type"] == "breathing" for flag in result["red_flags"])
    
    def test_emergency_stroke(self):
        """Should detect emergency: stroke symptoms."""
        result = clinical_triage_agent.analyze_utterance(
            "My face is drooping on one side and I can't speak clearly"
        )
        assert result["urgency"] == "EMERGENCY"
        assert any(flag["type"] == "stroke" for flag in result["red_flags"])
    
    def test_emergency_bleeding(self):
        """Should detect emergency: uncontrolled bleeding."""
        result = clinical_triage_agent.analyze_utterance(
            "The wound won't stop bleeding, it's soaked through the bandage"
        )
        assert result["urgency"] == "EMERGENCY"
        assert any(flag["type"] == "bleeding" for flag in result["red_flags"])
    
    def test_urgent_fever(self):
        """Should detect urgent: high fever."""
        result = clinical_triage_agent.analyze_utterance(
            "I have a fever of 102 degrees"
        )
        assert result["urgency"] == "URGENT"
        assert any(flag["type"] == "fever" for flag in result["red_flags"])
        assert result["escalation_needed"] is True
    
    def test_urgent_wound_infection(self):
        """Should detect urgent: wound infection signs."""
        result = clinical_triage_agent.analyze_utterance(
            "My wound is red and swollen with pus coming out"
        )
        assert result["urgency"] == "URGENT"
        assert any(flag["type"] == "wound" for flag in result["red_flags"])
    
    def test_urgent_high_pain(self):
        """Should detect urgent: worsening pain."""
        result = clinical_triage_agent.analyze_utterance(
            "My pain is getting worse, it's about an 8 now"
        )
        assert result["urgency"] == "URGENT"
        assert any(flag["type"] == "worsening_pain" for flag in result["red_flags"])
    
    def test_no_red_flags_routine(self):
        """Should classify as routine with mild symptoms."""
        result = clinical_triage_agent.analyze_utterance(
            "I'm feeling a bit tired but overall okay"
        )
        assert result["urgency"] in ("ROUTINE", "SELF_CARE")
        assert len(result["red_flags"]) == 0
        assert result["escalation_needed"] is False
    
    def test_multiple_red_flags(self):
        """Should detect multiple red flags in one message."""
        result = clinical_triage_agent.analyze_utterance(
            "I have chest pain and I'm short of breath"
        )
        assert result["urgency"] == "EMERGENCY"
        assert len(result["red_flags"]) >= 2


class TestRiskScoring:
    """Test risk score calculation."""
    
    def test_high_pain_modifier(self):
        """Should add +10 for pain level >= 7."""
        vitals = {"pain_level": 8}
        result = clinical_triage_agent.analyze_utterance(
            "My pain is an 8",
            current_vitals=vitals
        )
        assert result["risk_modifier"] >= 10
    
    def test_high_fever_modifier(self):
        """Should add +25 for temperature > 101°F."""
        vitals = {"temperature": 101.5}
        result = clinical_triage_agent.analyze_utterance(
            "I have a fever",
            current_vitals=vitals
        )
        assert result["risk_modifier"] >= 25
    
    def test_moderate_fever_modifier(self):
        """Should add +15 for temperature > 100.4°F."""
        vitals = {"temperature": 100.8}
        result = clinical_triage_agent.analyze_utterance(
            "I feel hot",
            current_vitals=vitals
        )
        assert result["risk_modifier"] >= 15
    
    def test_medication_nonadherence_modifier(self):
        """Should add +15 for not taking medications."""
        vitals = {"medication_adherence": False}
        result = clinical_triage_agent.analyze_utterance(
            "I forgot to take my medications",
            current_vitals=vitals
        )
        assert result["risk_modifier"] >= 15
    
    def test_wound_concern_modifier(self):
        """Should add +10 for wound concerns."""
        vitals = {"wound_status": "concerning"}
        result = clinical_triage_agent.analyze_utterance(
            "My wound looks bad",
            current_vitals=vitals
        )
        assert result["risk_modifier"] >= 10
    
    def test_combined_modifiers(self):
        """Should accumulate multiple risk modifiers."""
        vitals = {
            "pain_level": 8,
            "temperature": 101.5,
            "medication_adherence": False
        }
        result = clinical_triage_agent.analyze_utterance(
            "I'm in a lot of pain and have a fever",
            current_vitals=vitals
        )
        # 10 (pain) + 25 (fever) + 15 (meds) = 50 (capped at 50)
        assert result["risk_modifier"] >= 40


class TestTriageNotes:
    """Test triage note generation."""
    
    def test_emergency_note_includes_action(self):
        """Emergency notes should include action required."""
        result = clinical_triage_agent.analyze_utterance(
            "I'm having chest pain"
        )
        assert "EMERGENCY" in result["triage_note"]
        assert "ACTION REQUIRED" in result["triage_note"]
        assert "Immediate clinical escalation" in result["triage_note"]
    
    def test_urgent_note_includes_timeframe(self):
        """Urgent notes should include callback timeframe."""
        result = clinical_triage_agent.analyze_utterance(
            "I have a fever of 102"
        )
        assert "URGENT" in result["triage_note"]
        assert "within 4 hours" in result["triage_note"]
    
    def test_routine_note_no_escalation(self):
        """Routine notes should not mention escalation."""
        result = clinical_triage_agent.analyze_utterance(
            "I'm feeling okay, just a bit tired"
        )
        assert "No red flags detected" in result["triage_note"]


# Evaluation metrics
class TestTriageAccuracy:
    """Evaluate triage accuracy against labeled test cases."""
    
    @pytest.fixture
    def test_cases(self):
        """Ground truth labeled test cases."""
        return [
            # Emergency cases
            {"text": "severe chest pain", "expected": "EMERGENCY"},
            {"text": "can't breathe", "expected": "EMERGENCY"},
            {"text": "passed out", "expected": "EMERGENCY"},
            {"text": "coughing up blood", "expected": "EMERGENCY"},
            
            # Urgent cases
            {"text": "fever of 102 degrees", "expected": "URGENT"},
            {"text": "wound is red and draining pus", "expected": "URGENT"},
            {"text": "pain is getting worse", "expected": "URGENT"},
            {"text": "can't keep food down", "expected": "URGENT"},
            
            # Routine/Self-care cases
            {"text": "feeling a bit tired", "expected": "SELF_CARE"},
            {"text": "when can I drive?", "expected": "SELF_CARE"},
            {"text": "pain is manageable", "expected": "SELF_CARE"},
        ]
    
    def test_classification_accuracy(self, test_cases):
        """Calculate classification accuracy."""
        correct = 0
        total = len(test_cases)
        
        for case in test_cases:
            result = clinical_triage_agent.analyze_utterance(case["text"])
            if result["urgency"] == case["expected"]:
                correct += 1
            else:
                print(f"Misclassified: '{case['text']}'")
                print(f"  Expected: {case['expected']}, Got: {result['urgency']}")
        
        accuracy = correct / total
        print(f"\nTriage Accuracy: {accuracy*100:.1f}% ({correct}/{total})")
        
        # Should achieve at least 80% accuracy
        assert accuracy >= 0.80, f"Accuracy {accuracy:.2%} below 80% threshold"
    
    def test_emergency_recall(self, test_cases):
        """Emergency cases should never be missed (high recall)."""
        emergency_cases = [c for c in test_cases if c["expected"] == "EMERGENCY"]
        detected = 0
        
        for case in emergency_cases:
            result = clinical_triage_agent.analyze_utterance(case["text"])
            if result["urgency"] == "EMERGENCY":
                detected += 1
        
        recall = detected / len(emergency_cases)
        print(f"Emergency Recall: {recall*100:.1f}%")
        
        # Must catch all emergency cases (100% recall)
        assert recall >= 1.0, "Missed emergency case - CRITICAL FAILURE"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
