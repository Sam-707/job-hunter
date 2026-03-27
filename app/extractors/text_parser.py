"""
Parse raw job description text (no URL) into structured fields.
Reuses the field-extraction logic from url_extractor.
"""
from typing import Any
from app.extractors.url_extractor import _parse_text_to_fields


def parse_job_text(text: str) -> dict[str, Any]:
    """Parse free-form job description text into structured extraction result."""
    if not text or len(text.strip()) < 30:
        return {
            "description": text,
            "extraction_method": "manual_text",
            "extraction_confidence": "low",
            "requirements": [],
            "responsibilities": [],
            "nice_to_have": [],
        }

    result = _parse_text_to_fields(text)
    result["description"] = text.strip()
    result["extraction_method"] = "manual_text"
    result["extraction_confidence"] = "high" if len(text) > 300 else "medium"
    result["raw_content"] = None  # no HTML to store
    return result
