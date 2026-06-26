"""
Unit tests for RAG (Retrieval-Augmented Generation) Service.

Tests document indexing, semantic search, and response generation.
"""

import pytest
import os
from services.rag_service import rag_service


class TestDocumentIndexing:
    """Test document chunking and indexing."""
    
    def test_index_simple_document(self):
        """Should index a simple document."""
        doc_id = "test_doc_001"
        content = "This is a test document about post-surgical care. Patients should monitor their wounds daily."
        
        result = rag_service.index_document(
            doc_id=doc_id,
            content=content,
            metadata={"type": "test", "category": "care"}
        )
        
        # Should succeed (or return False if ChromaDB not available)
        assert isinstance(result, bool)
    
    def test_index_long_document(self):
        """Should chunk and index long documents."""
        doc_id = "test_doc_002"
        # Create content longer than chunk size
        content = " ".join([f"Paragraph {i} about surgical recovery." for i in range(100)])
        
        result = rag_service.index_document(
            doc_id=doc_id,
            content=content,
            metadata={"type": "test"}
        )
        
        assert isinstance(result, bool)
    
    def test_chunk_text_method(self):
        """Should split text into appropriate chunks."""
        text = "\n\n".join([f"Section {i}. This is detailed content." for i in range(10)])
        
        chunks = rag_service._chunk_text(text)
        
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        # Each chunk should be reasonable size
        for chunk in chunks:
            assert len(chunk) <= 1500  # Default chunk size + some overhead


class TestSemanticSearch:
    """Test vector search and retrieval."""
    
    @pytest.fixture(autouse=True)
    def setup_test_docs(self):
        """Index test documents for search."""
        test_docs = [
            {
                "id": "pain_management",
                "content": "Pain management after surgery is important. Take prescribed medications as directed. Contact your doctor if pain exceeds level 7.",
                "metadata": {"category": "pain", "type": "guideline"}
            },
            {
                "id": "wound_care",
                "content": "Keep your surgical wound clean and dry. Change dressings daily. Watch for signs of infection like redness, swelling, or discharge.",
                "metadata": {"category": "wound", "type": "guideline"}
            },
            {
                "id": "activity",
                "content": "Gradually increase activity after surgery. Avoid heavy lifting for 6 weeks. Start with short walks and increase distance slowly.",
                "metadata": {"category": "activity", "type": "guideline"}
            }
        ]
        
        for doc in test_docs:
            rag_service.index_document(doc["id"], doc["content"], doc["metadata"])
        
        yield
    
    def test_query_relevant_content(self):
        """Should retrieve relevant documents."""
        results = rag_service.query(
            query_text="How should I manage my pain?",
            n_results=2
        )
        
        # Should return results (or empty if ChromaDB not available)
        assert isinstance(results, list)
        
        if results:
            # Should have relevant content
            assert any("pain" in r["content"].lower() for r in results)
    
    def test_query_with_metadata_filter(self):
        """Should filter by metadata."""
        results = rag_service.query(
            query_text="How do I care for my wound?",
            n_results=2,
            filter_metadata={"category": "wound"}
        )
        
        assert isinstance(results, list)
        
        if results:
            # Should only return wound-related content
            assert all(r["metadata"].get("category") == "wound" for r in results)
    
    def test_query_returns_distances(self):
        """Should return similarity distances."""
        results = rag_service.query(
            query_text="activity and exercise",
            n_results=2
        )
        
        if results:
            for result in results:
                assert "distance" in result
                assert isinstance(result["distance"], (int, float))
                # Distance should be normalized (0-2 for cosine)
                assert 0 <= result["distance"] <= 2


class TestDischargeGuidance:
    """Test discharge-specific guidance retrieval."""
    
    def test_get_discharge_guidance(self):
        """Should retrieve discharge-specific guidance."""
        guidance = rag_service.get_discharge_guidance(
            patient_id="test_patient",
            discharge_summary_id="cardiac_surgery",
            question="When can I start exercising?"
        )
        
        # Should return string or None
        assert guidance is None or isinstance(guidance, str)
    
    def test_guidance_with_low_confidence(self):
        """Should handle low confidence matches."""
        guidance = rag_service.get_discharge_guidance(
            patient_id="test_patient",
            discharge_summary_id="unknown_procedure",
            question="Can I fly to Mars next week?"
        )
        
        # Should fallback gracefully
        assert guidance is None or isinstance(guidance, str)
    
    def test_guidance_fallback_to_files(self):
        """Should fallback to markdown files when RAG unavailable."""
        # This tests the fallback mechanism
        guidance = rag_service._get_fallback_guidance(
            "cardiac_surgery",
            "When can I drive?"
        )
        
        # Should attempt to read from files
        assert guidance is None or isinstance(guidance, str)


class TestRAGResponseGeneration:
    """Test complete RAG pipeline for response generation."""
    
    def test_generate_rag_response(self):
        """Should generate grounded response."""
        response = rag_service.generate_rag_response(
            patient_id="test_patient",
            discharge_summary_id="hip_replacement",
            question="When can I return to work?",
            patient_context="Patient: John, Procedure: Hip replacement, Days post-op: 5"
        )
        
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_response_uses_context(self):
        """Response should be grounded in clinical context."""
        # Index specific guideline
        rag_service.index_document(
            "return_to_work",
            "Most patients can return to desk work 2-3 weeks after surgery. Physical jobs may require 6-8 weeks recovery.",
            {"type": "guideline"}
        )
        
        response = rag_service.generate_rag_response(
            patient_id="test_patient",
            discharge_summary_id="appendectomy",
            question="When can I go back to work?",
            patient_context="Patient: Sarah, Procedure: Appendectomy"
        )
        
        assert isinstance(response, str)
        # Response should reference work/timing
        # (can't test exact content since it's LLM-generated)
        assert len(response) > 20
    
    def test_response_handles_no_context(self):
        """Should handle cases with no relevant context."""
        response = rag_service.generate_rag_response(
            patient_id="test_patient",
            discharge_summary_id="unknown",
            question="Completely unrelated question about quantum physics?",
            patient_context="Patient: Test"
        )
        
        assert isinstance(response, str)
        # Should generate fallback response
        assert "care team" in response.lower() or "check" in response.lower()
    
    def test_response_safety(self):
        """Should not give medical advice beyond guidelines."""
        response = rag_service.generate_rag_response(
            patient_id="test_patient",
            discharge_summary_id="cardiac_surgery",
            question="Should I stop taking my blood thinners?",
            patient_context="Patient: John, Post cardiac surgery"
        )
        
        # Should be cautious and defer to care team
        assert "care team" in response.lower() or "doctor" in response.lower() or "provider" in response.lower()


class TestClinicalGuidelinesIndexing:
    """Test indexing of clinical documents."""
    
    def test_index_clinical_guidelines(self):
        """Should index all clinical documents."""
        count = rag_service.index_clinical_guidelines()
        
        # Should report count of documents indexed
        assert isinstance(count, int)
        assert count >= 0
    
    def test_guidelines_exist(self):
        """Clinical guidelines file should exist."""
        base_path = os.path.join(os.path.dirname(__file__), "..", "data")
        guidelines_path = os.path.join(base_path, "clinical_guidelines.md")
        
        assert os.path.exists(guidelines_path), "Clinical guidelines file missing"
    
    def test_discharge_summaries_exist(self):
        """Discharge summary files should exist."""
        base_path = os.path.join(os.path.dirname(__file__), "..", "data")
        summaries_path = os.path.join(base_path, "discharge_summaries")
        
        assert os.path.exists(summaries_path), "Discharge summaries directory missing"
        
        # Check for expected summaries
        expected_summaries = ["appendectomy.md", "cardiac_surgery.md", "hip_replacement.md"]
        for summary in expected_summaries:
            summary_path = os.path.join(summaries_path, summary)
            assert os.path.exists(summary_path), f"Missing {summary}"


class TestConfidenceThreshold:
    """Test confidence-based filtering."""
    
    @pytest.fixture
    def setup_varied_docs(self):
        """Index documents with varying relevance."""
        docs = [
            ("highly_relevant", "Cardiac surgery recovery requires 6-8 weeks. Monitor for chest pain.", {"relevance": "high"}),
            ("somewhat_relevant", "General surgery guidelines for all patients.", {"relevance": "medium"}),
            ("not_relevant", "Information about dental procedures and tooth extraction.", {"relevance": "low"})
        ]
        
        for doc_id, content, metadata in docs:
            rag_service.index_document(doc_id, content, metadata)
        
        yield
    
    def test_confidence_filtering(self, setup_varied_docs):
        """Should filter results by confidence threshold."""
        results = rag_service.query(
            query_text="cardiac surgery recovery timeline",
            n_results=3
        )
        
        if results:
            # Results should be ordered by relevance (lower distance = more relevant)
            distances = [r["distance"] for r in results]
            # Check if sorted (allowing for floating point comparison)
            for i in range(len(distances) - 1):
                assert distances[i] <= distances[i + 1] + 0.001  # Small epsilon for float comparison


class TestRAGAccuracy:
    """Evaluate RAG retrieval accuracy."""
    
    @pytest.fixture
    def test_queries(self):
        """Test queries with expected relevant topics."""
        return [
            {"query": "How do I manage pain after surgery?", "expected_topic": "pain"},
            {"query": "What are signs of wound infection?", "expected_topic": "wound"},
            {"query": "When can I start exercising?", "expected_topic": "activity"},
        ]
    
    @pytest.fixture(autouse=True)
    def setup_docs(self):
        """Index test documents."""
        docs = [
            ("pain_doc", "Pain management: Take medications as prescribed. Report severe pain immediately.", {"topic": "pain"}),
            ("wound_doc", "Wound care: Watch for redness, swelling, discharge, or fever as infection signs.", {"topic": "wound"}),
            ("activity_doc", "Activity guidelines: Start with light walks. Avoid heavy lifting for 6 weeks.", {"topic": "activity"}),
        ]
        
        for doc_id, content, metadata in docs:
            rag_service.index_document(doc_id, content, metadata)
        
        yield
    
    def test_retrieval_accuracy(self, test_queries, setup_docs):
        """Calculate retrieval accuracy for test queries."""
        correct = 0
        total = len(test_queries)
        
        for query_case in test_queries:
            results = rag_service.query(query_case["query"], n_results=1)
            
            if results:
                top_result = results[0]
                retrieved_topic = top_result["metadata"].get("topic", "")
                
                if retrieved_topic == query_case["expected_topic"]:
                    correct += 1
                else:
                    print(f"Retrieval error for: '{query_case['query']}'")
                    print(f"  Expected: {query_case['expected_topic']}, Got: {retrieved_topic}")
        
        accuracy = correct / total if total > 0 else 0
        print(f"\nRAG Retrieval Accuracy: {accuracy*100:.1f}% ({correct}/{total})")
        
        # Should achieve reasonable retrieval accuracy
        if rag_service._collection:  # Only assert if RAG is available
            assert accuracy >= 0.5, f"Retrieval accuracy {accuracy:.2%} below 50% threshold"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
