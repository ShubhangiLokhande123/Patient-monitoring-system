"""
Alert service layer - handles alerts and risk scores.
"""

import json
from datetime import datetime
from typing import Optional
from database import get_db
from models.alerts import Alert, RiskScore, AlertUpdate, DashboardStats


class AlertService:
    """Service for alerts and risk scores."""

    def create_alert(
        self,
        patient_id: str,
        severity: str,
        alert_type: str,
        title: str,
        description: str,
        conversation_id: Optional[str] = None,
        trigger_text: Optional[str] = None,
    ) -> dict:
        """Create a new alert."""
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO alerts (
                    patient_id, conversation_id, severity, alert_type,
                    title, description, trigger_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    patient_id,
                    conversation_id,
                    severity,
                    alert_type,
                    title,
                    description,
                    trigger_text,
                ),
            )
            alert_id = cursor.lastrowid

        return self.get_alert(alert_id)

    def get_alert(self, alert_id: int) -> Optional[dict]:
        """Get an alert by ID."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM alerts WHERE id = ?", (alert_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_patient_alerts(
        self, patient_id: str, status: Optional[str] = None
    ) -> list[dict]:
        """Get alerts for a patient."""
        with get_db() as conn:
            if status:
                rows = conn.execute(
                    """
                    SELECT * FROM alerts 
                    WHERE patient_id = ? AND status = ?
                    ORDER BY created_at DESC
                    """,
                    (patient_id, status),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM alerts 
                    WHERE patient_id = ?
                    ORDER BY created_at DESC
                    """,
                    (patient_id,),
                ).fetchall()
            return [dict(row) for row in rows]

    def get_all_alerts(
        self, status: Optional[str] = None, severity: Optional[str] = None
    ) -> list[dict]:
        """Get all alerts, optionally filtered."""
        with get_db() as conn:
            query = "SELECT a.*, p.first_name, p.last_name, p.diagnosis FROM alerts a JOIN patients p ON a.patient_id = p.id"
            conditions = []
            params = []

            if status:
                conditions.append("a.status = ?")
                params.append(status)
            if severity:
                conditions.append("a.severity = ?")
                params.append(severity)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY a.created_at DESC"

            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def acknowledge_alert(
        self, alert_id: int, acknowledged_by: str = "clinician"
    ) -> Optional[dict]:
        """Acknowledge an alert."""
        with get_db() as conn:
            conn.execute(
                """
                UPDATE alerts 
                SET status = 'acknowledged', 
                    acknowledged_by = ?, 
                    acknowledged_at = datetime('now')
                WHERE id = ?
                """,
                (acknowledged_by, alert_id),
            )
        return self.get_alert(alert_id)

    def dismiss_alert(
        self, alert_id: int, acknowledged_by: str = "clinician"
    ) -> Optional[dict]:
        """Dismiss an alert."""
        with get_db() as conn:
            conn.execute(
                """
                UPDATE alerts 
                SET status = 'dismissed', 
                    acknowledged_by = ?, 
                    acknowledged_at = datetime('now')
                WHERE id = ?
                """,
                (acknowledged_by, alert_id),
            )
        return self.get_alert(alert_id)

    def record_risk_score(
        self,
        patient_id: str,
        score: int,
        category: str,
        conversation_id: Optional[str] = None,
        lace_l: int = 0,
        lace_a: int = 0,
        lace_c: int = 0,
        lace_e: int = 0,
        vitals_modifier: int = 0,
        breakdown: Optional[dict] = None,
    ) -> dict:
        """Record a risk score for a patient."""
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO risk_scores (
                    patient_id, conversation_id, score, category,
                    lace_l, lace_a, lace_c, lace_e, vitals_modifier, breakdown
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    patient_id,
                    conversation_id,
                    score,
                    category,
                    lace_l,
                    lace_a,
                    lace_c,
                    lace_e,
                    vitals_modifier,
                    json.dumps(breakdown or {}),
                ),
            )
            score_id = cursor.lastrowid

        return self.get_risk_score(score_id)

    def get_risk_score(self, score_id: int) -> Optional[dict]:
        """Get a risk score by ID."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM risk_scores WHERE id = ?", (score_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_latest_risk_score(self, patient_id: str) -> Optional[dict]:
        """Get the most recent risk score for a patient."""
        with get_db() as conn:
            row = conn.execute(
                """
                SELECT * FROM risk_scores 
                WHERE patient_id = ? 
                ORDER BY calculated_at DESC LIMIT 1
                """,
                (patient_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_risk_score_history(
        self, patient_id: str, limit: int = 10
    ) -> list[dict]:
        """Get risk score history for a patient."""
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT * FROM risk_scores 
                WHERE patient_id = ? 
                ORDER BY calculated_at DESC
                LIMIT ?
                """,
                (patient_id, limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_dashboard_stats(self) -> DashboardStats:
        """Get dashboard statistics."""
        with get_db() as conn:
            active_patients = conn.execute(
                "SELECT COUNT(*) FROM patients WHERE status = 'active'"
            ).fetchone()[0]

            calls_today = conn.execute(
                """
                SELECT COUNT(*) FROM conversations 
                WHERE date(started_at) = date('now')
                """
            ).fetchone()[0]

            avg_risk = conn.execute(
                """
                SELECT AVG(score) FROM risk_scores 
                WHERE id IN (
                    SELECT MAX(id) FROM risk_scores GROUP BY patient_id
                )
                """
            ).fetchone()[0] or 0.0

            pending_alerts = conn.execute(
                "SELECT COUNT(*) FROM alerts WHERE status = 'active'"
            ).fetchone()[0]

            high_risk = conn.execute(
                """
                SELECT COUNT(DISTINCT patient_id) FROM risk_scores 
                WHERE score >= 70 AND id IN (
                    SELECT MAX(id) FROM risk_scores GROUP BY patient_id
                )
                """
            ).fetchone()[0]

            escalations_today = conn.execute(
                """
                SELECT COUNT(*) FROM conversations 
                WHERE escalation_needed = 1 AND date(started_at) = date('now')
                """
            ).fetchone()[0]

            # Risk distribution
            distribution = {"LOW": 0, "MODERATE": 0, "HIGH": 0, "CRITICAL": 0}
            rows = conn.execute(
                """
                SELECT category, COUNT(*) as count FROM (
                    SELECT category, patient_id FROM risk_scores 
                    WHERE id IN (
                        SELECT MAX(id) FROM risk_scores GROUP BY patient_id
                    )
                ) GROUP BY category
                """
            ).fetchall()
            for row in rows:
                distribution[row["category"]] = row["count"]

            return DashboardStats(
                active_patients=active_patients,
                calls_today=calls_today,
                avg_risk_score=round(avg_risk, 1),
                pending_alerts=pending_alerts,
                high_risk_patients=high_risk,
                escalations_today=escalations_today,
                risk_distribution=distribution,
            )


# Singleton
alert_service = AlertService()
