"""
RAG (Retrieval-Augmented Generation) service for clinical knowledge retrieval.
Uses ChromaDB for vector storage of clinical guidelines and discharge summaries.
"""

import os
from typing import Optional
from config import settings

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from google import genai
from google.genai import types


class RAGService:
    """
    Retrieves relevant clinical knowledge from vector database
    to ground LLM responses in evidence-based guidelines.
    """

    def __init__(self):
        self._client = None
        self._collection = None
        self._gemini_client = None

        if CHROMADB_AVAILABLE:
            try:
                chroma_path = os.path.join(
                    os.path.dirname(__file__), "..", "data", "chroma_db"
                )
                self._client = chromadb.PersistentClient(path=chroma_path)
                self._collection = self._client.get_or_create_collection(
                    name="clinical_knowledge",
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception as e:
                print(f"Warning: ChromaDB initialization failed: {e}")

        if settings.GOOGLE_API_KEY:
            self._gemini_client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    def index_document(
        self, doc_id: str, content: str, metadata: Optional[dict] = None
    ) -> bool:
        """
        Index a document for retrieval.

        Args:
            doc_id: Unique identifier for the document
            content: Text content to index
            metadata: Optional metadata (e.g., type, patient_id, category)

        Returns:
            True if successful, False otherwise
        """
        if not self._collection:
            return False

        try:
            # Split content into chunks
            chunks = self._chunk_text(content)
            
            # Generate embeddings for each chunk
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}_chunk_{i}"
                chunk_metadata = metadata or {}
                chunk_metadata["chunk_index"] = i
                chunk_metadata["parent_doc_id"] = doc_id

                self._collection.add(
                    ids=[chunk_id],
                    documents=[chunk],
                    metadatas=[chunk_metadata],
                )
            return True
        except Exception as e:
            print(f"Error indexing document: {e}")
            return False

    def query(
        self,
        query_text: str,
        n_results: int = None,
        filter_metadata: Optional[dict] = None,
    ) -> list[dict]:
        """
        Query the knowledge base for relevant documents.

        Args:
            query_text: The search query
            n_results: Number of results to return (default from settings)
            filter_metadata: Optional metadata filters

        Returns:
            List of {"content": str, "metadata": dict, "distance": float}
        """
        if not self._collection:
            return []

        n_results = n_results or settings.RAG_TOP_K

        try:
            where = filter_metadata if filter_metadata else None
            results = self._collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where,
            )

            documents = []
            for i, doc in enumerate(results["documents"][0]):
                documents.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                })

            return documents
        except Exception as e:
            print(f"Error querying RAG: {e}")
            return []

    def get_discharge_guidance(
        self, patient_id: str, discharge_summary_id: str, question: str
    ) -> Optional[str]:
        """
        Get discharge-specific guidance for a patient question.
        
        Args:
            patient_id: Patient identifier
            discharge_summary_id: Type of discharge (e.g., 'cardiac_surgery')
            question: The patient's question

        Returns:
            Relevant guidance text or None
        """
        if not self._collection:
            return self._get_fallback_guidance(discharge_summary_id, question)

        # Query for discharge-specific content
        results = self.query(
            query_text=question,
            n_results=3,
            filter_metadata={"discharge_type": discharge_summary_id},
        )

        if not results:
            # Try without filter
            results = self.query(
                query_text=question,
                n_results=3,
            )

        if not results:
            return self._get_fallback_guidance(discharge_summary_id, question)

        # Filter by confidence threshold
        relevant = [
            r for r in results
            if r["distance"] < (1 - settings.RAG_CONFIDENCE_THRESHOLD)
        ]

        if not relevant:
            return self._get_fallback_guidance(discharge_summary_id, question)

        # Combine top results
        combined = "\n\n".join([r["content"] for r in relevant[:2]])
        return combined

    def generate_rag_response(
        self,
        patient_id: str,
        discharge_summary_id: str,
        question: str,
        patient_context: str,
    ) -> str:
        """
        Generate a RAG-grounded response to a patient question.

        Args:
            patient_id: Patient identifier
            discharge_summary_id: Type of discharge
            question: Patient's question
            patient_context: Relevant patient history

        Returns:
            Generated response grounded in clinical guidelines
        """
        # Retrieve relevant context
        context = self.get_discharge_guidance(
            patient_id, discharge_summary_id, question
        )

        if not self._gemini_client:
            return self._generate_fallback_response(question, context)

        prompt = f"""You are a post-discharge nurse helping a patient understand their recovery.
Use ONLY the provided clinical context to answer the patient's question.
If the information is not in the context, say you'll need to check with their care team.

Patient Context:
{patient_context}

Clinical Guidelines:
{context or 'No specific guidelines available for this question.'}

Patient Question: {question}

Guidelines for your response:
1. Be warm, empathetic, and conversational
2. Base your answer ONLY on the clinical guidelines provided
3. Do NOT make up information or give medical advice beyond the guidelines
4. If unsure, direct them to contact their care team
5. Keep responses concise (2-3 sentences max)

Response:"""

        try:
            response = self._gemini_client.models.generate_content(
                model=settings.LLM_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=300,
                ),
            )
            return response.text.strip()
        except Exception as e:
            print(f"Error generating RAG response: {e}")
            return self._generate_fallback_response(question, context)

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into chunks for indexing."""
        chunk_size = settings.RAG_CHUNK_SIZE
        overlap = settings.RAG_CHUNK_OVERLAP
        chunks = []
        
        # Split by paragraphs first
        paragraphs = text.split("\n\n")
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text]

    def _get_fallback_guidance(
        self, discharge_summary_id: str, question: str
    ) -> Optional[str]:
        """Fallback when RAG is unavailable."""
        # Load from markdown files directly
        try:
            base_path = os.path.join(os.path.dirname(__file__), "..", "data")
            
            # Try discharge summary first
            if discharge_summary_id:
                summary_path = os.path.join(
                    base_path, "discharge_summaries", f"{discharge_summary_id}.md"
                )
                if os.path.exists(summary_path):
                    with open(summary_path, "r") as f:
                        return f.read()
            
            # Try clinical guidelines
            guidelines_path = os.path.join(base_path, "clinical_guidelines.md")
            if os.path.exists(guidelines_path):
                with open(guidelines_path, "r") as f:
                    return f.read()
                    
        except Exception:
            pass
        
        return None

    def _generate_fallback_response(
        self, question: str, context: Optional[str]
    ) -> str:
        """Generate a safe fallback response."""
        if context:
            return (
                "Based on your discharge instructions, I can help with that. "
                "Let me check the details and get back to you, or you can "
                "refer to your discharge paperwork for specific guidance."
            )
        return (
            "That's a great question. I want to make sure you get accurate "
            "information. Let me flag this for your care team to review, "
            "or you can call the office at your convenience."
        )

    def index_clinical_guidelines(self) -> int:
        """
        Index all clinical guidelines and discharge summaries.
        Returns count of documents indexed.
        """
        count = 0
        base_path = os.path.join(os.path.dirname(__file__), "..", "data")
        
        # Index clinical guidelines
        guidelines_path = os.path.join(base_path, "clinical_guidelines.md")
        if os.path.exists(guidelines_path):
            with open(guidelines_path, "r") as f:
                content = f.read()
            if self.index_document(
                "clinical_guidelines",
                content,
                {"type": "guidelines", "category": "general"},
            ):
                count += 1

        # Index discharge summaries
        summaries_path = os.path.join(base_path, "discharge_summaries")
        if os.path.exists(summaries_path):
            for filename in os.listdir(summaries_path):
                if filename.endswith(".md"):
                    filepath = os.path.join(summaries_path, filename)
                    with open(filepath, "r") as f:
                        content = f.read()
                    discharge_type = filename.replace(".md", "")
                    if self.index_document(
                        f"discharge_{discharge_type}",
                        content,
                        {"type": "discharge_summary", "discharge_type": discharge_type},
                    ):
                        count += 1

        return count


# Singleton
rag_service = RAGService()
