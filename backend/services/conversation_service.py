"""
Conversation service layer - handles conversation and message management.
"""

import json
import uuid
from datetime import datetime
from typing import Optional
from database import get_db
from models.conversation import Conversation, Message, ChatRequest, ChatResponse


class ConversationService:
    """Service for conversation and message operations."""

    def create_conversation(
        self, patient_id: str, call_type: str = "daily_checkin"
    ) -> dict:
        """Create a new conversation for a patient."""
        conversation_id = str(uuid.uuid4())
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO conversations (id, patient_id, call_type, status)
                VALUES (?, ?, ?, 'active')
                """,
                (conversation_id, patient_id, call_type),
            )
        return self.get_conversation(conversation_id)

    def get_conversation(self, conversation_id: str) -> Optional[dict]:
        """Get a conversation by ID."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_active_conversation(self, patient_id: str) -> Optional[dict]:
        """Get the active conversation for a patient."""
        with get_db() as conn:
            row = conn.execute(
                """
                SELECT * FROM conversations 
                WHERE patient_id = ? AND status = 'active'
                ORDER BY started_at DESC LIMIT 1
                """,
                (patient_id,),
            ).fetchone()
            return dict(row) if row else None

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        agent_type: Optional[str] = None,
        deidentified_content: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Add a message to a conversation."""
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO messages (conversation_id, role, content, deidentified_content, agent_type, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    role,
                    content,
                    deidentified_content,
                    agent_type,
                    json.dumps(metadata or {}),
                ),
            )
            message_id = cursor.lastrowid

        return self.get_message(message_id)

    def get_message(self, message_id: int) -> Optional[dict]:
        """Get a message by ID."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM messages WHERE id = ?", (message_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_conversation_messages(
        self, conversation_id: str, limit: int = 50
    ) -> list[dict]:
        """Get all messages for a conversation."""
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT * FROM messages 
                WHERE conversation_id = ? 
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (conversation_id, limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def update_conversation(
        self,
        conversation_id: str,
        current_agent: Optional[str] = None,
        completed_checklist: Optional[list] = None,
        escalation_needed: Optional[bool] = None,
        escalation_reason: Optional[str] = None,
        status: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> Optional[dict]:
        """Update conversation state."""
        updates = []
        params = []

        if current_agent:
            updates.append("current_agent = ?")
            params.append(current_agent)
        if completed_checklist is not None:
            updates.append("completed_checklist = ?")
            params.append(json.dumps(completed_checklist))
        if escalation_needed is not None:
            updates.append("escalation_needed = ?")
            params.append(1 if escalation_needed else 0)
        if escalation_reason:
            updates.append("escalation_reason = ?")
            params.append(escalation_reason)
        if status:
            updates.append("status = ?")
            params.append(status)
        if summary:
            updates.append("summary = ?")
            params.append(summary)

        if not updates:
            return self.get_conversation(conversation_id)

        params.append(conversation_id)
        with get_db() as conn:
            conn.execute(
                f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?",
                params,
            )

        return self.get_conversation(conversation_id)

    def end_conversation(self, conversation_id: str, summary: Optional[str] = None) -> Optional[dict]:
        """End a conversation."""
        with get_db() as conn:
            conn.execute(
                """
                UPDATE conversations 
                SET status = 'completed', ended_at = datetime('now'), summary = ?
                WHERE id = ?
                """,
                (summary, conversation_id),
            )
        return self.get_conversation(conversation_id)

    def get_conversations_by_patient(self, patient_id: str) -> list[dict]:
        """Get all conversations for a patient."""
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT * FROM conversations 
                WHERE patient_id = ? 
                ORDER BY started_at DESC
                """,
                (patient_id,),
            ).fetchall()
            return [dict(row) for row in rows]


# Singleton
conversation_service = ConversationService()
