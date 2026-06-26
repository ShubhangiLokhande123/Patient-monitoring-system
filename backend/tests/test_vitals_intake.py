"""
Unit tests for Vitals Intake Agent

Tests structured data extraction from natural language.
"""

import pytest
from agents.vitals_intake import vitals_intake_agent


class TestPainLevelExtraction:
    """Test extraction of pain levels (1-10 scale)."""
    
    def test_explicit_number(self):
        """Should extract explicit pain numbers."""
        result = vitals_intake_agent._extract_with_rules(
            "My pain is about a 7",
            {"id": "pain_level", "extract_type": "integer", "range": [1, 10]}
        )
        assert result["value"] == 7
        assert result["confidence"] >= 0.7
    
    def test_range_clamping(self):
        """Should clamp values to valid range."""
        result = vitals_intake_agent._extract_with_rules(
            "It's like a 15 out of 10",
            {"id": "pain_level", "extract_type": "integer", "range": [1, 10]}
        )
        assert result["value"] == 10  # Clamped to max
    
    def test_multiple_numbers(self):
        """Should extract first number when multiple present."""
        result = vitals_intake_agent._extract_with_rules(
            "I'd say 5 or 6, definitely not a 10",
            {"id": "pain_level", "extract_type": "integer", "range": [1, 10]}
        )
        assert result["value"] in [5, 6]


class TestTemperatureExtraction:
    """Test extraction of temperature readings."""
    
    def test_decimal_temperature(self):
        """Should extract decimal temperatures."""
        result = vitals_intake_agent._extract_with_rules(
            "It was 99.2 degrees",
            {"id": "temperature", "extract_type": "float"}
        )
        assert result["value"] == 99.2
        assert result["confidence"] >= 0.7
    
    def test_whole_number_temperature(self):
        """Should handle whole number temperatures."""
        result = vitals_intake_agent._extract_with_rules(
            "My temperature is 101",
            {"id": "temperature", "extract_type": "float"}
        )
        assert result["value"] == 101.0


class TestBooleanExtraction:
    """Test extraction of yes/no responses."""
    
    def test_affirmative_responses(self):
        """Should detect affirmative responses."""
        for response in ["yes", "yeah", "yep", "I did", "took them all"]:
            result = vitals_intake_agent._extract_with_rules(
                response,
                {"id": "medication_adherence", "extract_type": "boolean"}
            )
            assert result["value"] is True
    
    def test_negative_responses(self):
        """Should detect negative responses."""
        for response in ["no", "nope", "forgot", "didn't take them", "missed a dose"]:
            result = vitals_intake_agent._extract_with_rules(
                response,
                {"id": "medication_adherence", "extract_type": "boolean"}
            )
            assert result["value"] is False


class TestCategoricalExtraction:
    """Test extraction of categorical values."""
    
    def test_wound_status_normal(self):
        """Should classify normal wound status."""
        result = vitals_intake_agent._extract_with_rules(
            "It looks good, no problems",
            {
                "id": "wound_status",
                "extract_type": "categorical",
                "categories": ["normal", "mild_concern", "concerning", "unknown"]
            }
        )
        assert result["value"] == "normal"
    
    def test_wound_status_concerning(self):
        """Should classify concerning wound status."""
        result = vitals_intake_agent._extract_with_rules(
            "It's red and swollen",
            {
                "id": "wound_status",
                "extract_type": "categorical",
                "categories": ["normal", "mild_concern", "concerning", "unknown"]
            }
        )
        assert result["value"] == "concerning"
    
    def test_mobility_improving(self):
        """Should classify improving mobility."""
        result = vitals_intake_agent._extract_with_rules(
            "Walking is getting easier each day",
            {
                "id": "mobility_status",
                "extract_type": "categorical",
                "categories": ["improving", "stable", "declining", "unable", "unknown"]
            }
        )
        assert result["value"] == "improving"
    
    def test_appetite_categories(self):
        """Should classify appetite levels."""
        test_cases = [
            ("Eating well", "good"),
            ("Not eating much", "poor"),
            ("About the same as yesterday", "fair"),
            ("Haven't eaten anything", "none")
        ]
        
        for text, expected in test_cases:
            result = vitals_intake_agent._extract_with_rules(
                text,
                {
                    "id": "appetite",
                    "extract_type": "categorical",
                    "categories": ["good", "fair", "poor", "none"]
                }
            )
            assert result["value"] == expected


class TestChecklistProgress:
    """Test checklist progression."""
    
    def test_empty_checklist(self):
        """Should return first item for empty checklist."""
        next_q = vitals_intake_agent.get_next_question([], "Patient")
        assert next_q is not None
        assert next_q["id"] == "pain_level"
    
    def test_partial_checklist(self):
        """Should return next uncompleted item."""
        next_q = vitals_intake_agent.get_next_question(
            ["pain_level", "temperature"],
            "Patient"
        )
        assert next_q is not None
        assert next_q["id"] == "wound_status"
    
    def test_complete_checklist(self):
        """Should return None when checklist complete."""
        all_items = [
            "pain_level", "temperature", "wound_status",
            "medication_adherence", "mobility_status", "appetite"
        ]
        next_q = vitals_intake_agent.get_next_question(all_items, "Patient")
        assert next_q is None
    
    def test_progress_calculation(self):
        """Should calculate correct progress percentage."""
        progress = vitals_intake_agent.get_checklist_progress(
            ["pain_level", "temperature", "wound_status"]
        )
        assert progress["total"] == 6
        assert progress["completed"] == 3
        assert progress["remaining"] == 3
        assert progress["percent"] == 50


class TestExtractionAccuracy:
    """Evaluate extraction accuracy against labeled test cases."""
    
    @pytest.fixture
    def pain_test_cases(self):
        """Ground truth for pain level extraction."""
        return [
            {"text": "my pain is a 3", "expected": 3},
            {"text": "about a 7 out of 10", "expected": 7},
            {"text": "pain level is 5", "expected": 5},
            {"text": "I'd say 8", "expected": 8},
        ]
    
    @pytest.fixture
    def boolean_test_cases(self):
        """Ground truth for yes/no extraction."""
        return [
            {"text": "yes I took them", "expected": True},
            {"text": "no I forgot", "expected": False},
            {"text": "I did", "expected": True},
            {"text": "didn't take them", "expected": False},
        ]
    
    def test_pain_extraction_accuracy(self, pain_test_cases):
        """Calculate pain extraction accuracy."""
        correct = 0
        for case in pain_test_cases:
            result = vitals_intake_agent._extract_with_rules(
                case["text"],
                {"id": "pain_level", "extract_type": "integer", "range": [1, 10]}
            )
            if result["value"] == case["expected"]:
                correct += 1
        
        accuracy = correct / len(pain_test_cases)
        print(f"Pain Extraction Accuracy: {accuracy*100:.1f}%")
        assert accuracy >= 0.75  # Should achieve 75%+ accuracy
    
    def test_boolean_extraction_accuracy(self, boolean_test_cases):
        """Calculate boolean extraction accuracy."""
        correct = 0
        for case in boolean_test_cases:
            result = vitals_intake_agent._extract_with_rules(
                case["text"],
                {"id": "medication_adherence", "extract_type": "boolean"}
            )
            if result["value"] == case["expected"]:
                correct += 1
        
        accuracy = correct / len(boolean_test_cases)
        print(f"Boolean Extraction Accuracy: {accuracy*100:.1f}%")
        assert accuracy >= 0.75


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
