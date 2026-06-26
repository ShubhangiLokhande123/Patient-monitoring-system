"""
SQLite database setup with all table definitions.
Uses raw sqlite3 for zero-dependency simplicity in the prototype.
"""

import sqlite3
import json
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "concierge_triage.db")


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize all database tables."""
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS patients (
                id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                date_of_birth TEXT,
                phone TEXT,
                diagnosis TEXT NOT NULL,
                procedure_name TEXT,
                discharge_date TEXT NOT NULL,
                discharge_summary_id TEXT,
                assigned_clinician TEXT DEFAULT 'Dr. Sarah Chen',
                comorbidities TEXT DEFAULT '[]',
                length_of_stay_days INTEGER DEFAULT 3,
                admission_acuity TEXT DEFAULT 'elective',
                er_visits_prior_6m INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                call_type TEXT DEFAULT 'daily_checkin',
                started_at TEXT DEFAULT (datetime('now')),
                ended_at TEXT,
                current_agent TEXT DEFAULT 'supervisor',
                completed_checklist TEXT DEFAULT '[]',
                escalation_needed INTEGER DEFAULT 0,
                escalation_reason TEXT,
                summary TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                deidentified_content TEXT,
                agent_type TEXT,
                metadata TEXT DEFAULT '{}',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );

            CREATE TABLE IF NOT EXISTS vitals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                conversation_id TEXT,
                pain_level INTEGER,
                temperature REAL,
                wound_status TEXT,
                medication_adherence INTEGER,
                mobility_status TEXT,
                appetite TEXT,
                fluid_intake TEXT,
                additional_notes TEXT,
                recorded_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (patient_id) REFERENCES patients(id),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                conversation_id TEXT,
                severity TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                trigger_text TEXT,
                status TEXT DEFAULT 'active',
                acknowledged_by TEXT,
                acknowledged_at TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (patient_id) REFERENCES patients(id),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );

            CREATE TABLE IF NOT EXISTS risk_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                conversation_id TEXT,
                score INTEGER NOT NULL,
                category TEXT NOT NULL,
                lace_l INTEGER DEFAULT 0,
                lace_a INTEGER DEFAULT 0,
                lace_c INTEGER DEFAULT 0,
                lace_e INTEGER DEFAULT 0,
                vitals_modifier INTEGER DEFAULT 0,
                breakdown TEXT DEFAULT '{}',
                calculated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            );

            CREATE INDEX IF NOT EXISTS idx_conversations_patient 
                ON conversations(patient_id);
            CREATE INDEX IF NOT EXISTS idx_messages_conversation 
                ON messages(conversation_id);
            CREATE INDEX IF NOT EXISTS idx_alerts_patient 
                ON alerts(patient_id);
            CREATE INDEX IF NOT EXISTS idx_alerts_status 
                ON alerts(status);
            CREATE INDEX IF NOT EXISTS idx_risk_scores_patient 
                ON risk_scores(patient_id);
            CREATE INDEX IF NOT EXISTS idx_vitals_patient 
                ON vitals(patient_id);
        """
        )


def seed_sample_data():
    """Load sample patient data from JSON file."""
    sample_file = os.path.join(os.path.dirname(__file__), "data", "sample_patients.json")
    if not os.path.exists(sample_file):
        return

    with get_db() as conn:
        # Check if data already seeded
        count = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
        if count > 0:
            return

        with open(sample_file, "r") as f:
            patients = json.load(f)

        for p in patients:
            conn.execute(
                """
                INSERT INTO patients (
                    id, first_name, last_name, date_of_birth, phone,
                    diagnosis, procedure_name, discharge_date,
                    discharge_summary_id, assigned_clinician,
                    comorbidities, length_of_stay_days,
                    admission_acuity, er_visits_prior_6m, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    p["id"],
                    p["first_name"],
                    p["last_name"],
                    p["date_of_birth"],
                    p["phone"],
                    p["diagnosis"],
                    p["procedure_name"],
                    p["discharge_date"],
                    p.get("discharge_summary_id"),
                    p.get("assigned_clinician", "Dr. Sarah Chen"),
                    json.dumps(p.get("comorbidities", [])),
                    p.get("length_of_stay_days", 3),
                    p.get("admission_acuity", "elective"),
                    p.get("er_visits_prior_6m", 0),
                    p.get("status", "active"),
                ),
            )

        # Seed initial risk scores for each patient
        for p in patients:
            if "initial_risk_score" in p:
                conn.execute(
                    """
                    INSERT INTO risk_scores (
                        patient_id, score, category, breakdown
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        p["id"],
                        p["initial_risk_score"],
                        p.get("initial_risk_category", "LOW"),
                        json.dumps(p.get("risk_breakdown", {})),
                    ),
                )
