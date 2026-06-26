"""
Unit and integration tests for Supervisor Agent

Tests conversation orchestration, intent classification, agent routing,
and end-to-end conversation flows.
"""

import pytest
from agents.supervisor import supervisor_agent
from agents.vitals_intake import VITALS_CHECKLIST


class TestIntentClassification:
    """Test intent classification logic."""
    
    @pytest.mark.asyncio
    async def test_question_detection_with_question_mark(self):
        """Should detect questions with question marks."""
        intent = await supervisor_agent._classify_intent(
            "Can I take a shower?", []
        )
        assert intent == "question"
    
    @pytest.mark.asyncio
    async def test_question_detection_with_indicators(self):
        """Should detect questions with indicator words."""
        questions = [
            "when can I drive",
            "should I take my medicine with food",
            "how do I change the dressing",
            "is it okay to exercise",
            "what about swimming"
        ]
        for q in questions:
            intent = await supervisor_agent._classify_intent(q, [])
            assert intent == "question", f"Failed to detect question: {q}"
    
    @pytest.mark.asyncio
    async def test_vitals_collection_mid_checklist(self):
        """Should classify as vitals_collection when checklist incomplete."""
        # Simulate mid-checklist with answer-like content
        intent = await supervisor_agent._classify_intent(
            "It's about a 5", ["pain_level"]
        )
        assert intent == "vitals_collection"
    
    @pytest.mark.asyncio
    async def test_vitals_collection_yes_no_answer(self):
        """Should classify yes/no as vitals_collection when incomplete."""
        intent = await supervisor_agent._classify_intent(
            "yes", ["pain_level", "temperature"]
        )
        assert intent == "vitals_collection"
    
    @pytest.mark.asyncio
    async def test_general_when_checklist_complete(self):
        """Should classify as general when checklist complete."""
        all_items = [item["id"] for item in VITALS_CHECKLIST]
        intent = await supervisor_agent._classify_intent(
            "I'm feeling better", all_items
        )
        assert intent == "general"


class TestConversationOrchestration:
    """Test message routing through agent pipeline."""
    
    @pytest.fixture
    def sample_patient(self):
        """Sample patient data."""
        return {
            "id": "test_patient_001",
            "first_name": "Test",
            "last_name": "Patient",
            "procedure_name": "hip replacement",
            "discharge_date": "2024-06-20",
            "discharge_summary_id": "hip_replacement"
        }
    
    @pytest.fixture
    def empty_conversation(self):
        """Empty conversation state."""
        return {
            "id": "conv_001",
            "patient_id": "test_patient_001",
            "status": "active",
            "completed_checklist": []
        }
    
    @pytest.mark.asyncio
    async def test_emergency_immediate_escalation(self, sample_patient, empty_conversation):
        """Emergency messages should trigger immediate escalation."""
        result = await supervisor_agent.process_message(
            user_message="I'm having severe chest pain",
            patient_id=sample_patient["id"],
            conversation_state=empty_conversation,
            patient_data=sample_patient
        )
        
        assert result["escalation_needed"] is True
        assert result["agent_type"] == "triage"
        assert "EMERGENCY" in result["triage_result"]["urgency"]
        assert "emergency" in result["response"].lower() or "911" in result["response"]
    
    @pytest.mark.asyncio
    async def test_urgent_escalation_flag(self, sample_patient, empty_conversation):
        """Urgent conditions should flag escalation."""
        result = await supervisor_agent.process_message(
            user_message="I have a fever of 102 degrees",
            patient_id=sample_patient["id"],
            conversation_state=empty_conversation,
            patient_data=sample_patient
        )
        
        assert result["escalation_needed"] is True
        assert result["triage_result"]["urgency"] in ["URGENT", "EMERGENCY"]
    
    @pytest.mark.asyncio
    async def test_vitals_collection_flow(self, sample_patient, empty_conversation):
        """Should initiate vitals collection for first message."""
        result = await supervisor_agent.process_message(
            user_message="I'm doing okay",
            patient_id=sample_patient["id"],
            conversation_state=empty_conversation,
            patient_data=sample_patient
        )
        
        assert result["agent_type"] == "vitals"
        assert "pain" in result["response"].lower()
        assert len(result["checklist_update"]) == 0  # Just asked first question
    
    @pytest.mark.asyncio
    async def test_vitals_extraction_and_progression(self, sample_patient, empty_conversation):
        """Should extract vitals and progress through checklist."""
        # Simulate answering pain level question
        conversation_with_progress = {
            **empty_conversation,
            "completed_checklist": []  # Starting fresh
        }
        
        result = await supervisor_agent.process_message(
            user_message="My pain is about a 3",
            patient_id=sample_patient["id"],
            conversation_state=conversation_with_progress,
            patient_data=sample_patient
        )
        
        assert result["agent_type"] == "vitals"
        assert len(result["checklist_update"]) == 1
        assert result["checklist_update"][0] == "pain_level"
        assert result["vitals_update"]["value"] is not None
        
        # Response should ask next question
        assert "temperature" in result["response"].lower()
    
    @pytest.mark.asyncio
    async def test_checklist_completion(self, sample_patient, empty_conversation):
        """Should recognize when checklist is complete."""
        all_items = [item["id"] for item in VITALS_CHECKLIST]
        completed_conversation = {
            **empty_conversation,
            "completed_checklist": all_items
        }
        
        result = await supervisor_agent.process_message(
            user_message="Everything is good",
            patient_id=sample_patient["id"],
            conversation_state=completed_conversation,
            patient_data=sample_patient
        )
        
        # Should not be vitals agent anymore
        assert result["agent_type"] in ["supervisor", "discharge_coach", "triage"]
    
    @pytest.mark.asyncio
    async def test_question_routing_to_rag(self, sample_patient, empty_conversation):
        """Questions should be routed to discharge coach (RAG)."""
        result = await supervisor_agent.process_message(
            user_message="When can I start driving again?",
            patient_id=sample_patient["id"],
            conversation_state=empty_conversation,
            patient_data=sample_patient
        )
        
        assert result["agent_type"] == "discharge_coach"
        assert len(result["response"]) > 0


class TestPHIDeidentification:
    """Test PHI handling in conversation flow."""
    
    @pytest.fixture
    def sample_patient(self):
        return {
            "id": "test_patient_002",
            "first_name": "Jane",
            "last_name": "Doe",
            "procedure_name": "appendectomy",
            "discharge_date": "2024-06-22"
        }
    
    @pytest.fixture
    def conversation(self):
        return {
            "id": "conv_phi_test",
            "patient_id": "test_patient_002",
            "status": "active",
            "completed_checklist": ["pain_level"]
        }
    
    @pytest.mark.asyncio
    async def test_phi_deidentification_in_pipeline(self, sample_patient, conversation):
        """PHI should be deidentified before processing."""
        message_with_phi = "My SSN is 123-45-6789 and my pain is 7"
        
        result = await supervisor_agent.process_message(
            user_message=message_with_phi,
            patient_id=sample_patient["id"],
            conversation_state=conversation,
            patient_data=sample_patient
        )
        
        # Should still process the message successfully
        assert result["response"] is not None
        # SSN should not appear in triage results
        assert "123-45-6789" not in str(result["triage_result"])


class TestRiskModifierCalculation:
    """Test risk score modifications based on vitals."""
    
    @pytest.fixture
    def sample_patient(self):
        return {
            "id": "test_patient_003",
            "first_name": "Robert",
            "procedure_name": "cardiac surgery",
            "discharge_date": "2024-06-21"
        }
    
    @pytest.fixture
    def conversation(self):
        return {
            "id": "conv_risk_test",
            "patient_id": "test_patient_003",
            "status": "active",
            "completed_checklist": []
        }
    
    @pytest.mark.asyncio
    async def test_high_pain_increases_risk(self, sample_patient, conversation):
        """High pain level should increase risk modifier."""
        result = await supervisor_agent.process_message(
            user_message="My pain is a 9",
            patient_id=sample_patient["id"],
            conversation_state=conversation,
            patient_data=sample_patient,
            current_vitals={"pain_level": 9}
        )
        
        assert result["triage_result"]["risk_modifier"] > 0
    
    @pytest.mark.asyncio
    async def test_fever_increases_risk(self, sample_patient, conversation):
        """High fever should increase risk modifier."""
        result = await supervisor_agent.process_message(
            user_message="I have a fever",
            patient_id=sample_patient["id"],
            conversation_state=conversation,
            patient_data=sample_patient,
            current_vitals={"temperature": 101.8}
        )
        
        assert result["triage_result"]["risk_modifier"] >= 25
    
    @pytest.mark.asyncio
    async def test_multiple_risk_factors_accumulate(self, sample_patient, conversation):
        """Multiple risk factors should accumulate."""
        result = await supervisor_agent.process_message(
            user_message="I have pain and fever and forgot my meds",
            patient_id=sample_patient["id"],
            conversation_state=conversation,
            patient_data=sample_patient,
            current_vitals={
                "pain_level": 8,
                "temperature": 101.5,
                "medication_adherence": False
            }
        )
        
        # Should have significant risk modifier
        assert result["triage_result"]["risk_modifier"] >= 40


class TestInitialMessage:
    """Test conversation initialization."""
    
    def test_initial_message_personalization(self):
        """Initial message should be personalized."""
        patient = {
            "first_name": "Emily",
            "procedure_name": "knee surgery"
        }
        
        message = supervisor_agent.get_initial_message(patient)
        
        assert "Emily" in message
        assert "knee surgery" in message.lower()
    
    def test_initial_message_structure(self):
        """Initial message should be welcoming and clear."""
        patient = {
            "first_name": "John",
            "procedure_name": "hip replacement"
        }
        
        message = supervisor_agent.get_initial_message(patient)
        
        # Should introduce purpose
        assert "care team" in message.lower() or "follow-up" in message.lower()
        # Should mention questions
        assert "question" in message.lower()


class TestEndToEndConversationFlow:
    """Test complete conversation scenarios."""
    
    @pytest.fixture
    def patient(self):
        return {
            "id": "e2e_patient_001",
            "first_name": "Sarah",
            "last_name": "Johnson",
            "procedure_name": "appendectomy",
            "discharge_date": "2024-06-23",
            "discharge_summary_id": "appendectomy"
        }
    
    @pytest.mark.asyncio
    async def test_normal_vitals_collection_flow(self, patient):
        """Test complete normal vitals collection."""
        conversation = {
            "id": "e2e_conv_001",
            "patient_id": patient["id"],
            "status": "active",
            "completed_checklist": []
        }
        
        # Simulate answering all 6 vitals questions
        vitals_answers = [
            ("My pain is a 2", "pain_level"),
            ("98.6 degrees", "temperature"),
            ("The wound looks good", "wound_status"),
            ("Yes, I took all my medications", "medication_adherence"),
            ("Walking is getting easier", "mobility_status"),
            ("Eating well", "appetite")
        ]
        
        for answer, expected_item in vitals_answers:
            result = await supervisor_agent.process_message(
                user_message=answer,
                patient_id=patient["id"],
                conversation_state=conversation,
                patient_data=patient
            )
            
            assert result["agent_type"] == "vitals"
            assert expected_item in result["checklist_update"]
            
            # Update conversation state
            conversation["completed_checklist"] = result["checklist_update"]
        
        # After all questions, should complete
        assert len(conversation["completed_checklist"]) == 6
        assert result["escalation_needed"] is False
    
    @pytest.mark.asyncio
    async def test_emergency_interrupts_vitals(self, patient):
        """Emergency should interrupt vitals collection."""
        conversation = {
            "id": "e2e_conv_002",
            "patient_id": patient["id"],
            "status": "active",
            "completed_checklist": ["pain_level"]  # Mid-collection
        }
        
        # Patient reports emergency mid-checklist
        result = await supervisor_agent.process_message(
            user_message="I can't breathe properly",
            patient_id=patient["id"],
            conversation_state=conversation,
            patient_data=patient
        )
        
        # Should immediately escalate regardless of checklist position
        assert result["escalation_needed"] is True
        assert result["agent_type"] == "triage"
        assert "911" in result["response"] or "emergency" in result["response"].lower()


# Evaluation metrics
class TestSupervisorAccuracy:
    """Evaluate supervisor routing accuracy."""
    
    @pytest.fixture
    def test_cases(self):
        """Ground truth for routing decisions."""
        return [
            {"message": "My pain is a 5", "expected_agent": "vitals", "checklist": []},
            {"message": "When can I drive?", "expected_agent": "discharge_coach", "checklist": []},
            {"message": "I'm having chest pain", "expected_agent": "triage", "checklist": []},
            {"message": "Everything is fine", "expected_agent": "supervisor", "checklist": [item["id"] for item in VITALS_CHECKLIST]},
        ]
    
    @pytest.fixture
    def sample_patient(self):
        return {
            "id": "eval_patient",
            "first_name": "Test",
            "procedure_name": "surgery",
            "discharge_date": "2024-06-20"
        }
    
    @pytest.mark.asyncio
    async def test_routing_accuracy(self, test_cases, sample_patient):
        """Calculate routing accuracy."""
        correct = 0
        total = len(test_cases)
        
        for case in test_cases:
            conversation = {
                "id": f"eval_conv_{hash(case['message'])}",
                "patient_id": sample_patient["id"],
                "status": "active",
                "completed_checklist": case["checklist"]
            }
            
            result = await supervisor_agent.process_message(
                user_message=case["message"],
                patient_id=sample_patient["id"],
                conversation_state=conversation,
                patient_data=sample_patient
            )
            
            if result["agent_type"] == case["expected_agent"]:
                correct += 1
            else:
                print(f"Routing error: '{case['message']}'")
                print(f"  Expected: {case['expected_agent']}, Got: {result['agent_type']}")
        
        accuracy = correct / total
        print(f"\nSupervisor Routing Accuracy: {accuracy*100:.1f}% ({correct}/{total})")
        
        # Should achieve high routing accuracy
        assert accuracy >= 0.75, f"Routing accuracy {accuracy:.2%} below 75% threshold"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
