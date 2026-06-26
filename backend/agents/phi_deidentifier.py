"""
Agent 1: PHI De-identification Agent

Uses Microsoft Presidio to detect and mask Protected Health Information (PHI)
before text reaches the LLM orchestrator. Maintains a reversible mapping
per-session so responses can be re-identified for the patient.
"""

import re
import uuid
from typing import Optional

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig

    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False

from config import settings


class PHIDeidentifier:
    """Handles PHI detection, masking, and re-identification."""

    def __init__(self):
        self._analyzer = None
        self._anonymizer = None
        # Per-session mapping: {session_id: {placeholder: real_value}}
        self._session_mappings: dict[str, dict[str, str]] = {}

        if PRESIDIO_AVAILABLE:
            try:
                self._analyzer = AnalyzerEngine()
                self._anonymizer = AnonymizerEngine()
            except Exception:
                # Presidio may fail if spaCy model not downloaded — fall back to regex
                pass

    def deidentify(
        self, text: str, session_id: str
    ) -> tuple[str, dict[str, str]]:
        """
        De-identify PHI in text, returning masked text and the mapping.

        Args:
            text: Raw input text potentially containing PHI
            session_id: Session identifier for mapping storage

        Returns:
            Tuple of (de-identified text, {placeholder: real_value} mapping)
        """
        if session_id not in self._session_mappings:
            self._session_mappings[session_id] = {}

        mapping = self._session_mappings[session_id]

        if self._analyzer and self._anonymizer:
            return self._deidentify_presidio(text, session_id, mapping)
        else:
            return self._deidentify_regex(text, session_id, mapping)

    def _deidentify_presidio(
        self, text: str, session_id: str, mapping: dict
    ) -> tuple[str, dict[str, str]]:
        """Use Presidio for robust PHI detection and masking."""
        results = self._analyzer.analyze(
            text=text,
            entities=settings.PHI_ENTITIES,
            language="en",
        )

        # Sort by start position (reverse) to replace from end to start
        results = sorted(results, key=lambda x: x.start, reverse=True)

        masked_text = text
        for result in results:
            original = text[result.start : result.end]
            entity_type = result.entity_type

            # Check if we already have a mapping for this value
            existing_placeholder = None
            for ph, val in mapping.items():
                if val == original:
                    existing_placeholder = ph
                    break

            if existing_placeholder:
                placeholder = existing_placeholder
            else:
                # Create a new consistent placeholder
                count = sum(
                    1 for k in mapping if k.startswith(f"[{entity_type}")
                )
                placeholder = f"[{entity_type}_{count + 1}]"
                mapping[placeholder] = original

            masked_text = (
                masked_text[: result.start]
                + placeholder
                + masked_text[result.end :]
            )

        self._session_mappings[session_id] = mapping
        return masked_text, mapping

    def _deidentify_regex(
        self, text: str, session_id: str, mapping: dict
    ) -> tuple[str, dict[str, str]]:
        """Fallback regex-based PHI detection when Presidio is unavailable."""
        masked_text = text

        # SSN pattern
        ssn_pattern = r"\b\d{3}-\d{2}-\d{4}\b"
        for match in re.finditer(ssn_pattern, masked_text):
            original = match.group()
            placeholder = self._get_or_create_placeholder(
                mapping, "US_SSN", original
            )
            masked_text = masked_text.replace(original, placeholder, 1)

        # Phone number pattern
        phone_pattern = r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
        for match in re.finditer(phone_pattern, masked_text):
            original = match.group()
            placeholder = self._get_or_create_placeholder(
                mapping, "PHONE_NUMBER", original
            )
            masked_text = masked_text.replace(original, placeholder, 1)

        # Email pattern
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        for match in re.finditer(email_pattern, masked_text):
            original = match.group()
            placeholder = self._get_or_create_placeholder(
                mapping, "EMAIL_ADDRESS", original
            )
            masked_text = masked_text.replace(original, placeholder, 1)

        # Date pattern (various formats)
        date_pattern = r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"
        for match in re.finditer(date_pattern, masked_text):
            original = match.group()
            placeholder = self._get_or_create_placeholder(
                mapping, "DATE_TIME", original
            )
            masked_text = masked_text.replace(original, placeholder, 1)

        self._session_mappings[session_id] = mapping
        return masked_text, mapping

    def _get_or_create_placeholder(
        self, mapping: dict, entity_type: str, value: str
    ) -> str:
        """Get existing placeholder for a value or create a new one."""
        for ph, val in mapping.items():
            if val == value:
                return ph
        count = sum(1 for k in mapping if k.startswith(f"[{entity_type}"))
        placeholder = f"[{entity_type}_{count + 1}]"
        mapping[placeholder] = value
        return placeholder

    def reidentify(self, text: str, session_id: str) -> str:
        """
        Replace placeholders back with real PHI values.

        Args:
            text: De-identified text with placeholders
            session_id: Session identifier to look up the mapping

        Returns:
            Re-identified text with real values restored
        """
        mapping = self._session_mappings.get(session_id, {})
        result = text
        for placeholder, real_value in mapping.items():
            result = result.replace(placeholder, real_value)
        return result

    def get_mapping(self, session_id: str) -> dict[str, str]:
        """Get the current PHI mapping for a session."""
        return self._session_mappings.get(session_id, {})

    def clear_session(self, session_id: str):
        """Clear PHI mapping when session ends."""
        self._session_mappings.pop(session_id, None)


# Singleton instance
phi_deidentifier = PHIDeidentifier()
