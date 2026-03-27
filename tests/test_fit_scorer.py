"""
Tests for the deterministic fit scorer.
These tests do NOT require a database or LLM call.
"""
import pytest
from app.models.profile import CandidateProfile
from app.models.job import Job
from app.scoring.fit_scorer import (
    score_fit,
    _score_skills,
    _score_experience,
    _score_work_mode,
    _score_salary,
    _check_red_flags,
    _verdict,
)


def make_profile(**kwargs) -> CandidateProfile:
    defaults = dict(
        id="p1",
        name="Test",
        skills=["Python", "FastAPI", "React"],
        years_of_experience=5.0,
        work_mode_preference="hybrid",
        work_auth_countries=["Germany"],
        location="Berlin, Germany",
        salary_min=70_000,
        salary_max=90_000,
        salary_currency="EUR",
        must_have=["Python"],
        red_flags=["MLM", "unpaid trial"],
        target_roles=[],
        target_industries=[],
        target_companies=[],
        certifications=[],
        languages=[],
        nice_to_have=[],
    )
    defaults.update(kwargs)
    return CandidateProfile(**defaults)


def make_job(**kwargs) -> Job:
    defaults = dict(
        id="j1",
        input_type="text",
        title="Python Developer",
        company="Startup GmbH",
        location="Berlin, Germany",
        work_mode="hybrid",
        employment_type="full-time",
        salary_min=72_000,
        salary_max=88_000,
        salary_currency="EUR",
        description="Python FastAPI startup Berlin hybrid",
        requirements=["Python", "FastAPI", "3+ years"],
        responsibilities=[],
        nice_to_have=[],
        required_experience_years=3.0,
    )
    defaults.update(kwargs)
    return Job(**defaults)


# ─── Verdict thresholds ───────────────────────────────────────────────────────

def test_verdict_strong_match():
    assert _verdict(80) == "Strong Match"
    assert _verdict(100) == "Strong Match"
    assert _verdict(85) == "Strong Match"


def test_verdict_possible_match():
    assert _verdict(60) == "Possible Match"
    assert _verdict(75) == "Possible Match"
    assert _verdict(79) == "Possible Match"


def test_verdict_weak_match():
    assert _verdict(40) == "Weak Match"
    assert _verdict(55) == "Weak Match"


def test_verdict_not_recommended():
    assert _verdict(39) == "Not Recommended"
    assert _verdict(0) == "Not Recommended"


# ─── Skills scoring ───────────────────────────────────────────────────────────

def test_skills_full_overlap():
    profile = make_profile(skills=["Python", "FastAPI"])
    job = make_job(requirements=["Python", "FastAPI"], description="Python FastAPI")
    score, matched, missing = _score_skills(profile, job)
    assert score > 80
    assert "Python" in matched or "FastAPI" in matched


def test_skills_no_overlap():
    profile = make_profile(skills=["Java", "Spring"])
    job = make_job(
        requirements=["Python", "FastAPI", "React", "PostgreSQL", "Docker"],
        description="Python FastAPI React PostgreSQL Docker",
    )
    score, matched, missing = _score_skills(profile, job)
    assert score < 30


def test_skills_no_profile_skills_returns_neutral():
    profile = make_profile(skills=[])
    job = make_job()
    score, matched, missing = _score_skills(profile, job)
    assert score == 50  # neutral when profile has no skills


# ─── Experience scoring ──────────────────────────────────────────────────────

def test_experience_exactly_meets_requirement():
    profile = make_profile(years_of_experience=5.0)
    job = make_job(required_experience_years=5.0)
    assert _score_experience(profile, job) == 100


def test_experience_exceeds_by_small_margin():
    profile = make_profile(years_of_experience=7.0)
    job = make_job(required_experience_years=5.0)
    assert _score_experience(profile, job) == 100


def test_experience_short_by_1_year():
    profile = make_profile(years_of_experience=4.0)
    job = make_job(required_experience_years=5.0)
    score = _score_experience(profile, job)
    assert 70 <= score <= 85


def test_experience_very_underqualified():
    profile = make_profile(years_of_experience=1.0)
    job = make_job(required_experience_years=10.0)
    assert _score_experience(profile, job) < 20


def test_experience_no_requirement_stated():
    profile = make_profile(years_of_experience=5.0)
    job = make_job(required_experience_years=None)
    assert _score_experience(profile, job) == 75


def test_experience_no_profile_data():
    profile = make_profile(years_of_experience=None)
    job = make_job(required_experience_years=5.0)
    assert _score_experience(profile, job) == 60  # neutral


# ─── Work mode scoring ────────────────────────────────────────────────────────

def test_work_mode_exact_match():
    profile = make_profile(work_mode_preference="hybrid")
    job = make_job(work_mode="hybrid")
    assert _score_work_mode(profile, job) == 100


def test_work_mode_remote_preferred_but_onsite():
    profile = make_profile(work_mode_preference="remote")
    job = make_job(work_mode="onsite")
    assert _score_work_mode(profile, job) <= 15


def test_work_mode_any_preference_neutral():
    profile = make_profile(work_mode_preference="any")
    job = make_job(work_mode="onsite")
    assert _score_work_mode(profile, job) == 80


# ─── Salary scoring ───────────────────────────────────────────────────────────

def test_salary_good_alignment():
    profile = make_profile(salary_min=70_000, salary_max=90_000)
    job = make_job(salary_min=75_000, salary_max=90_000)
    assert _score_salary(profile, job) >= 80


def test_salary_job_pays_too_low():
    profile = make_profile(salary_min=90_000, salary_max=120_000)
    job = make_job(salary_min=50_000, salary_max=65_000)
    assert _score_salary(profile, job) < 40


def test_salary_missing_data_neutral():
    profile = make_profile(salary_min=None, salary_max=None)
    job = make_job(salary_min=None, salary_max=None)
    assert _score_salary(profile, job) == 75


# ─── Red flags ────────────────────────────────────────────────────────────────

def test_red_flag_triggered():
    profile = make_profile(red_flags=["MLM", "unpaid trial"])
    job = make_job(description="Join our MLM network and earn commissions")
    triggered = _check_red_flags(profile, job)
    assert "MLM" in triggered


def test_no_red_flags():
    profile = make_profile(red_flags=["MLM", "unpaid trial"])
    job = make_job(description="Build great Python APIs at our startup")
    triggered = _check_red_flags(profile, job)
    assert triggered == []


def test_red_flag_reduces_total_score():
    profile = make_profile(red_flags=["MLM"])
    good_job = make_job(description="Python startup hybrid Berlin")
    bad_job = make_job(description="Python startup MLM Berlin")
    good_result = score_fit(profile, good_job)
    bad_result = score_fit(profile, bad_job)
    assert good_result.fit_score > bad_result.fit_score


# ─── Full integration score ───────────────────────────────────────────────────

def test_strong_match_produces_high_score():
    profile = make_profile(
        skills=["Python", "FastAPI", "PostgreSQL"],
        years_of_experience=5.0,
        work_mode_preference="hybrid",
        salary_min=70_000,
        salary_max=90_000,
        must_have=["Python"],
        red_flags=[],
    )
    job = make_job(
        description="Python FastAPI startup Berlin hybrid",
        requirements=["Python", "FastAPI"],
        required_experience_years=3.0,
        work_mode="hybrid",
        salary_min=75_000,
        salary_max=88_000,
    )
    result = score_fit(profile, job)
    assert result.fit_score >= 60
    assert result.fit_verdict in ("Strong Match", "Possible Match")


def test_weak_match_produces_low_score():
    profile = make_profile(
        skills=["Python", "FastAPI"],
        years_of_experience=2.0,
        work_mode_preference="remote",
        salary_min=80_000,
        must_have=["remote"],
        red_flags=[],
    )
    job = make_job(
        description="Java Spring enterprise onsite",
        requirements=["Java", "Spring Boot", "Oracle", "8+ years", "TOGAF"],
        required_experience_years=8.0,
        work_mode="onsite",
        salary_min=40_000,
        salary_max=55_000,
    )
    result = score_fit(profile, job)
    assert result.fit_score <= 50


def test_scoring_result_has_breakdown():
    profile = make_profile()
    job = make_job()
    result = score_fit(profile, job)
    assert "skills" in result.score_breakdown
    assert "experience" in result.score_breakdown
    assert "work_mode" in result.score_breakdown
    assert "salary" in result.score_breakdown
    assert 0 <= result.fit_score <= 100
