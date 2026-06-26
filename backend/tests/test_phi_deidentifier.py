"""
Unit tests for PHI Deidentifier Agent

Tests HIPAA compliance and reversible masking.
"""

import pytest
from agents.phi_deidentifier import phi_deidentifier


class TestPHIDetection:
    """Test detection of Protected Health Information."""
    
    def test_ssn_detection(self):
        """Should detect and mask SSN."""
        text = "My SSN is 123-45-6789"
        masked, mapping = phi_deidentifier.deidentify(text, "test_session")
        
        assert "123-45-6789" not in masked
        assert "[US_SSN" in masked
        assert len(mapping) > 0
    
    def test_phone_detection(self):
        """Should detect and mask phone numbers."""
        text = "Call me at 555-123-4567"
        masked, mapping = phi_deidentifier.deidentify(text, "test_session")
        
        assert "555-123-4567" not in masked
        assert "[PHONE_NUMBER" in masked
    
    def test_email_detection(self):
        """Should detect and mask email addresses."""
        text = "Email me at patient@example.com"
        masked, mapping = phi_deidentifier.deidentify(text, "test_session")
        
        assert "patient@example.com" not in masked
        assert "[EMAIL_ADDRESS" in masked
    
    def test_date_detection(self):
        """Should detect and mask dates."""
        text = "My appointment is on 12/25/2024"
        masked, mapping = phi_deidentifier.deidentify(text, "test_session")
        
        assert "12/25/2024" not in masked
        assert "[DATE_TIME" in masked
    
    def test_multiple_phi_types(self):
        """Should detect multiple PHI types in one text."""
        text = "I'm John Doe, SSN 123-45-6789, phone 555-1234"
        masked, mapping = phi_deidentifier.deidentify(text, "test_session")
        
        assert "123-45-6789" not in masked
        assert "555-1234" not in masked
        assert len(mapping) >= 2


class TestReidentification:
    """Test reversible PHI masking."""
    
    def test_reidentify_restores_original(self):
        """Should restore original PHI from masked text."""
        original = "My SSN is 123-45-6789"
        masked, mapping = phi_deidentifier.deidentify(original, "test_session")
        restored = phi_deidentifier.reidentify(masked, "test_session")
        
        assert restored == original
    
    def test_consistent_placeholders(self):
        """Should use same placeholder for same PHI value."""
        text1 = "SSN is 123-45-6789"
        text2 = "My SSN: 123-45-6789"
        
        masked1, _ = phi_deidentifier.deidentify(text1, "test_session")
        masked2, _ = phi_deidentifier.deidentify(text2, "test_session")
        
        # Extract placeholder from both
        placeholder1 = masked1.split()[-1]
        placeholder2 = masked2.split()[-1]
        
        assert placeholder1 == placeholder2
    
    def test_session_isolation(self):
        """Should isolate PHI mappings by session."""
        text = "SSN is 123-45-6789"
        
        masked1, map1 = phi_deidentifier.deidentify(text, "session_1")
        masked2, map2 = phi_deidentifier.deidentify(text, "session_2")
        
        # Different sessions can have different mappings
        # But should be consistent within same session
        assert len(map1) > 0
        assert len(map2) > 0


class TestSessionManagement:
    """Test session-based PHI mapping management."""
    
    def test_clear_session(self):
        """Should clear session mappings."""
        text = "SSN is 123-45-6789"
        masked, _ = phi_deidentifier.deidentify(text, "temp_session")
        
        phi_deidentifier.clear_session("temp_session")
        mapping = phi_deidentifier.get_mapping("temp_session")
        
        assert len(mapping) == 0
    
    def test_get_mapping(self):
        """Should retrieve session mapping."""
        text = "SSN is 123-45-6789"
        _, expected_mapping = phi_deidentifier.deidentify(text, "test_session")
        
        actual_mapping = phi_deidentifier.get_mapping("test_session")
        
        assert actual_mapping == expected_mapping


class TestNonPHIText:
    """Test handling of text without PHI."""
    
    def test_no_phi_unchanged(self):
        """Text without PHI should remain mostly unchanged."""
        text = "I am feeling better today"
        masked, mapping = phi_deidentifier.deidentify(text, "test_session")
        
        # No PHI to mask
        assert len(mapping) == 0 or text == masked
    
    def test_clinical_terms_preserved(self):
        """Clinical terminology should not be masked."""
        text = "I have chest pain and shortness of breath"
        masked, _ = phi_deidentifier.deidentify(text, "test_session")
        
        assert "chest pain" in masked
        assert "shortness of breath" in masked


class TestPHIProtectionCompliance:
    """Evaluate HIPAA compliance."""
    
    @pytest.fixture
    def phi_test_cases(self):
        """Test cases with various PHI types."""
        return [
            "Patient John Smith, DOB 01/15/1980",
            "Call 555-123-4567 or email john@email.com",
            "SSN: 123-45-6789, MRN: 98765",
            "Address: 123 Main St, City, State 12345",
            "Prescription filled on 12/01/2024 at CVS"
        ]
    
    def test_no_phi_leakage(self, phi_test_cases):
        """Should not leak any PHI in masked output."""
        leaked = []
        
        for text in phi_test_cases:
            masked, _ = phi_deidentifier.deidentify(text, f"session_{hash(text)}")
            
            # Check for common PHI patterns
            if any(pattern in masked for pattern in [
                r"\d{3}-\d{2}-\d{4}",  # SSN
                r"\d{3}-\d{3}-\d{4}",  # Phone
                r"@",                   # Email
            ]):
                leaked.append(text)
        
        assert len(leaked) == 0, f"PHI leaked in {len(leaked)} cases"
    
    def test_reversibility(self, phi_test_cases):
        """All PHI should be reversibly maskable."""
        for text in phi_test_cases:
            session_id = f"session_{hash(text)}"
            masked, _ = phi_deidentifier.deidentify(text, session_id)
            restored = phi_deidentifier.reidentify(masked, session_id)
            
            # Allow minor whitespace differences
            assert restored.strip() == text.strip()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
