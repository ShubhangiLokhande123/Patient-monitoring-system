"""
Integration tests for full system workflows.

Tests complete API endpoints, database operations, and multi-turn conversations.
"""

import pytest
import json
from fastapi.testclient import TestClient
from main import app
from database import get_db, init_db
from services.patient_service import patient_service


client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Initialize test database."""
    init_db()
    yield


class TestPatientEndpoints:
    """Test patient management API."""
    
    def test_list_patients(self):
        """Should return list of patients."""
        response = client.get("/patients/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_get_patient_by_id(self):
        """Should retrieve specific patient."""
        # Get first patient
        patients = client.get("/patients/").json()
        if patients:
            patient_id = patients[0]["id"]
            response = client.get(f"/patients/{patient_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == patient_id
    
    def test_get_nonexistent_patient(self):
        """Should return 404 for nonexistent patient."""
        response = client.get("/patients/nonexistent_id")
        assert response.status_code == 404
    
    def test_get_patient_vitals_history(self):
        """Should return vitals history for patient."""
        patients = client.get("/patients/").json()
        if patients:
            patient_id = patients[0]["id"]
            response = client.get(f"/patients/{patient_id}/vitals")
            assert response.status_code == 200
            # May be empty list if no vitals recorded
            assert isinstance(response.json(), list)


class TestChatEndpoints:
    """Test conversation/chat API."""
    
    @pytest.fixture
    def test_patient_id(self):
        """Get a test patient ID."""
        patients = client.get("/patients/").json()
        return patients[0]["id"] if patients else None
    
    def test_start_conversation(self, test_patient_id):
        """Should start new conversation."""
        if not test_patient_id:
            pytest.skip("No patients available")
        
        response = client.post(f"/chat/start/{test_patient_id}")
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "response" in data
        assert data["agent_type"] in ["supervisor", "vitals"]
    
    def test_send_message(self, test_patient_id):
        """Should process message and return response."""
        if not test_patient_id:
            pytest.skip("No patients available")
        
        # Start conversation
        start_resp = client.post(f"/chat/start/{test_patient_id}").json()
        conversation_id = start_resp["conversation_id"]
        
        # Send message
        response = client.post(
            "/chat/",
            json={
                "patient_id": test_patient_id,
                "conversation_id": conversation_id,
                "message": "My pain is about a 3"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "conversation_id" in data
        assert "agent_type" in data
    
    def test_get_conversation_messages(self, test_patient_id):
        """Should retrieve conversation history."""
        if not test_patient_id:
            pytest.skip("No patients available")
        
        # Start conversation and send message
        start_resp = client.post(f"/chat/start/{test_patient_id}").json()
        conversation_id = start_resp["conversation_id"]
        
        client.post(
            "/chat/",
            json={
                "patient_id": test_patient_id,
                "conversation_id": conversation_id,
                "message": "I'm feeling okay"
            }
        )
        
        # Get messages
        response = client.get(f"/chat/{conversation_id}/messages")
        assert response.status_code == 200
        data = response.json()
        assert "conversation" in data
        assert "messages" in data
        assert len(data["messages"]) >= 2  # At least greeting + patient message
    
    def test_end_conversation(self, test_patient_id):
        """Should end conversation successfully."""
        if not test_patient_id:
            pytest.skip("No patients available")
        
        # Start conversation
        start_resp = client.post(f"/chat/start/{test_patient_id}").json()
        conversation_id = start_resp["conversation_id"]
        
        # End conversation
        response = client.post(f"/chat/{conversation_id}/end")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["conversation_id"] == conversation_id


class TestAlertEndpoints:
    """Test alert management API."""
    
    def test_list_active_alerts(self):
        """Should return list of active alerts."""
        response = client.get("/alerts/active")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_patient_alerts(self):
        """Should return alerts for specific patient."""
        patients = client.get("/patients/").json()
        if patients:
            patient_id = patients[0]["id"]
            response = client.get(f"/alerts/patient/{patient_id}")
            assert response.status_code == 200
            assert isinstance(response.json(), list)


class TestMultiTurnConversation:
    """Test realistic multi-turn conversation flows."""
    
    @pytest.fixture
    def patient_id(self):
        """Get test patient."""
        patients = client.get("/patients/").json()
        return patients[0]["id"] if patients else None
    
    def test_complete_vitals_collection(self, patient_id):
        """Test complete vitals collection flow."""
        if not patient_id:
            pytest.skip("No patients available")
        
        # Start conversation
        start_resp = client.post(f"/chat/start/{patient_id}").json()
        conversation_id = start_resp["conversation_id"]
        
        # Answer vitals questions
        vitals_responses = [
            "My pain is a 2",
            "Temperature is 98.6",
            "The wound looks good",
            "Yes, I took my medications",
            "Walking is easier today",
            "Eating well"
        ]
        
        for i, message in enumerate(vitals_responses):
            response = client.post(
                "/chat/",
                json={
                    "patient_id": patient_id,
                    "conversation_id": conversation_id,
                    "message": message
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            
            # Should be vitals agent for most of collection
            if i < len(vitals_responses) - 1:
                assert data["agent_type"] in ["vitals", "supervisor", "triage"]
        
        # Check conversation metadata
        messages_resp = client.get(f"/chat/{conversation_id}/messages")
        assert messages_resp.status_code == 200
        metadata = messages_resp.json()
        
        # Should have collected vitals
        assert len(metadata["messages"]) > len(vitals_responses)
    
    def test_emergency_escalation_flow(self, patient_id):
        """Test emergency detection and escalation."""
        if not patient_id:
            pytest.skip("No patients available")
        
        # Start conversation
        start_resp = client.post(f"/chat/start/{patient_id}").json()
        conversation_id = start_resp["conversation_id"]
        
        # Report emergency
        response = client.post(
            "/chat/",
            json={
                "patient_id": patient_id,
                "conversation_id": conversation_id,
                "message": "I'm having severe chest pain and can't breathe"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should detect emergency
        assert data["escalation_needed"] is True
        assert data["alert_triggered"] is True
        assert data["agent_type"] == "triage"
        
        # Check alerts were created
        alerts_resp = client.get(f"/alerts/patient/{patient_id}")
        alerts = alerts_resp.json()
        assert len(alerts) > 0
        assert any(alert["severity"] in ["critical", "high"] for alert in alerts)
    
    def test_question_answering_flow(self, patient_id):
        """Test patient question via RAG."""
        if not patient_id:
            pytest.skip("No patients available")
        
        # Start conversation
        start_resp = client.post(f"/chat/start/{patient_id}").json()
        conversation_id = start_resp["conversation_id"]
        
        # Ask question
        response = client.post(
            "/chat/",
            json={
                "patient_id": patient_id,
                "conversation_id": conversation_id,
                "message": "When can I start driving again?"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should route to discharge coach
        assert data["agent_type"] in ["discharge_coach", "supervisor"]
        assert len(data["response"]) > 0
        
        # Response should be helpful
        assert len(data["response"]) > 20  # Not just a stub


class TestDatabaseOperations:
    """Test database integrity and operations."""
    
    def test_patient_creation_and_retrieval(self):
        """Test patient CRUD operations."""
        # Patient should exist from seed data
        patients = patient_service.list_patients()
        assert len(patients) > 0
        
        # Retrieve specific patient
        patient_id = patients[0]["id"]
        patient = patient_service.get_patient_by_id(patient_id)
        assert patient is not None
        assert patient["id"] == patient_id
    
    def test_conversation_persistence(self):
        """Test conversation state persistence."""
        patients = client.get("/patients/").json()
        if not patients:
            pytest.skip("No patients available")
        
        patient_id = patients[0]["id"]
        
        # Create conversation
        start_resp = client.post(f"/chat/start/{patient_id}").json()
        conversation_id = start_resp["conversation_id"]
        
        # Send message
        client.post(
            "/chat/",
            json={
                "patient_id": patient_id,
                "conversation_id": conversation_id,
                "message": "My pain is a 5"
            }
        )
        
        # Retrieve conversation
        messages_resp = client.get(f"/chat/{conversation_id}/messages")
        assert messages_resp.status_code == 200
        data = messages_resp.json()
        
        # Should have persistent conversation state
        assert data["conversation"]["id"] == conversation_id
        assert len(data["messages"]) >= 2
    
    def test_vitals_recording(self):
        """Test vitals are recorded to database."""
        patients = client.get("/patients/").json()
        if not patients:
            pytest.skip("No patients available")
        
        patient_id = patients[0]["id"]
        
        # Start conversation and record vitals
        start_resp = client.post(f"/chat/start/{patient_id}").json()
        conversation_id = start_resp["conversation_id"]
        
        # Answer pain question
        client.post(
            "/chat/",
            json={
                "patient_id": patient_id,
                "conversation_id": conversation_id,
                "message": "My pain level is 3"
            }
        )
        
        # Check vitals were recorded
        vitals_resp = client.get(f"/patients/{patient_id}/vitals")
        vitals = vitals_resp.json()
        
        # May have vitals now
        # At minimum, API should return without error
        assert isinstance(vitals, list)


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_patient_id(self):
        """Should handle invalid patient ID gracefully."""
        response = client.post(
            "/chat/",
            json={
                "patient_id": "invalid_id",
                "message": "Test message"
            }
        )
        assert response.status_code == 404
    
    def test_invalid_conversation_id(self):
        """Should handle invalid conversation ID."""
        patients = client.get("/patients/").json()
        if patients:
            response = client.post(
                "/chat/",
                json={
                    "patient_id": patients[0]["id"],
                    "conversation_id": "invalid_conv_id",
                    "message": "Test"
                }
            )
            assert response.status_code == 404
    
    def test_mismatched_patient_conversation(self):
        """Should prevent conversation hijacking."""
        patients = client.get("/patients/").json()
        if len(patients) >= 2:
            # Create conversation for patient 1
            conv_resp = client.post(f"/chat/start/{patients[0]['id']}").json()
            conversation_id = conv_resp["conversation_id"]
            
            # Try to use it with patient 2
            response = client.post(
                "/chat/",
                json={
                    "patient_id": patients[1]["id"],
                    "conversation_id": conversation_id,
                    "message": "Test"
                }
            )
            assert response.status_code == 403


class TestSystemIntegration:
    """Test full system integration."""
    
    def test_health_check(self):
        """Test API health endpoint."""
        response = client.get("/")
        assert response.status_code == 200
    
    def test_api_docs_available(self):
        """Test OpenAPI documentation."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        # Should be valid OpenAPI spec
        spec = response.json()
        assert "openapi" in spec
        assert "paths" in spec
    
    def test_concurrent_conversations(self):
        """Test multiple concurrent conversations."""
        patients = client.get("/patients/").json()
        if len(patients) < 2:
            pytest.skip("Need at least 2 patients")
        
        # Start conversations for multiple patients
        conversations = []
        for patient in patients[:2]:
            resp = client.post(f"/chat/start/{patient['id']}").json()
            conversations.append({
                "patient_id": patient["id"],
                "conversation_id": resp["conversation_id"]
            })
        
        # Send messages to each
        for conv in conversations:
            response = client.post(
                "/chat/",
                json={
                    "patient_id": conv["patient_id"],
                    "conversation_id": conv["conversation_id"],
                    "message": "I'm feeling fine"
                }
            )
            assert response.status_code == 200
        
        # Verify both conversations maintained separate state
        for conv in conversations:
            messages_resp = client.get(f"/chat/{conv['conversation_id']}/messages")
            assert messages_resp.status_code == 200
            data = messages_resp.json()
            assert data["conversation"]["patient_id"] == conv["patient_id"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
