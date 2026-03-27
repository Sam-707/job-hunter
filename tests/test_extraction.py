"""
Tests for job text parsing and field extraction.
No network calls — pure unit tests.
"""
import pytest
from app.extractors.text_parser import parse_job_text
from app.extractors.url_extractor import _find_salary, _parse_text_to_fields


# ─── Text parser ─────────────────────────────────────────────────────────────

def test_parse_returns_high_confidence_for_rich_text():
    text = """
    Senior Python Developer — Startup GmbH, Berlin

    We are looking for a Python developer with 3+ years of experience.

    Requirements:
    - Python proficiency
    - FastAPI or Django
    - PostgreSQL experience
    - Docker

    Responsibilities:
    - Build and maintain APIs
    - Write tests

    We offer €75,000 - €90,000 per year. Hybrid work model.
    """
    result = parse_job_text(text)
    assert result["extraction_confidence"] in ("high", "medium")
    assert result["description"] is not None
    assert len(result["description"]) > 50


def test_parse_detects_remote_work_mode():
    text = "This is a fully remote position. Work from home anywhere in Europe."
    result = parse_job_text(text)
    assert result["work_mode"] == "remote"


def test_parse_detects_hybrid():
    text = "We offer a hybrid work model — 3 days in office, 2 days remote."
    result = parse_job_text(text)
    assert result["work_mode"] == "hybrid"


def test_parse_detects_onsite():
    text = "This role is fully onsite at our Munich office. Relocation required."
    result = parse_job_text(text)
    assert result["work_mode"] == "onsite"


def test_parse_detects_employment_type_fulltime():
    text = "This is a full-time permanent position based in Berlin."
    result = parse_job_text(text)
    assert result["employment_type"] == "full-time"


def test_parse_detects_contract():
    text = "6-month contract role. Possible extension. Freelance welcome."
    result = parse_job_text(text)
    assert result["employment_type"] == "contract"


def test_parse_detects_experience_years():
    text = "We require 5+ years of professional experience in software development."
    result = parse_job_text(text)
    assert result["required_experience_years"] == 5.0


def test_parse_short_text_returns_low_confidence():
    text = "Software job"
    result = parse_job_text(text)
    assert result["extraction_confidence"] in ("low", "medium")


def test_parse_empty_text():
    result = parse_job_text("")
    assert result["extraction_confidence"] == "low"


# ─── Salary extraction ────────────────────────────────────────────────────────

def test_salary_eur_range():
    result = _find_salary("Salary: €70,000 - €90,000 per year")
    assert result is not None
    assert result["currency"] == "EUR"
    assert result["min"] == 70_000
    assert result["max"] == 90_000


def test_salary_usd():
    result = _find_salary("Compensation: $120,000 - $150,000")
    assert result is not None
    assert result["currency"] == "USD"
    assert result["min"] == 120_000


def test_salary_k_notation():
    result = _find_salary("We pay 80k - 100k based on experience")
    assert result is not None
    assert result["min"] == 80_000


def test_salary_none_if_not_present():
    result = _find_salary("Great team, exciting challenges, competitive salary")
    assert result is None


# ─── Field parsing ────────────────────────────────────────────────────────────

def test_field_extraction_finds_requirements():
    text = """
    Requirements:
    - Python 3.8+
    - Experience with REST APIs
    - PostgreSQL knowledge

    Responsibilities:
    - Build features
    - Review code
    """
    result = _parse_text_to_fields(text)
    assert len(result["requirements"]) >= 1
    assert len(result["responsibilities"]) >= 1
