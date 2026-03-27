"""
Deterministic fit scorer.

No LLM calls here. Scores are calculated from structured profile + job data
using weighted heuristics. This keeps scoring transparent, fast, and testable.

Score composition (weights sum to 100):
  skills         35%
  experience     20%
  must_have      20%
  work_mode      10%
  location       10%
  salary          5%

Red flags can reduce the total by up to 30 points.

Verdicts:
  80-100 → Strong Match
  60-79  → Possible Match
  40-59  → Weak Match
  0-39   → Not Recommended
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.profile import CandidateProfile
    from app.models.job import Job


WEIGHTS = {
    "skills": 35,
    "experience": 20,
    "must_have": 20,
    "work_mode": 10,
    "location": 10,
    "salary": 5,
}

VERDICT_THRESHOLDS = [
    (80, "Strong Match"),
    (60, "Possible Match"),
    (40, "Weak Match"),
    (0, "Not Recommended"),
]


@dataclass
class ScoringResult:
    fit_score: int
    fit_verdict: str
    score_breakdown: dict[str, int]
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    triggered_red_flags: list[str] = field(default_factory=list)
    met_must_have: list[str] = field(default_factory=list)
    unmet_must_have: list[str] = field(default_factory=list)


def score_fit(profile: "CandidateProfile", job: "Job") -> ScoringResult:
    """Calculate deterministic fit score between a profile and a job."""

    breakdown: dict[str, int] = {}

    # 1. Skills
    skills_score, matched_skills, missing_skills = _score_skills(profile, job)
    breakdown["skills"] = skills_score

    # 2. Experience
    exp_score = _score_experience(profile, job)
    breakdown["experience"] = exp_score

    # 3. Must-have criteria
    must_score, met_must, unmet_must = _score_must_have(profile, job)
    breakdown["must_have"] = must_score

    # 4. Work mode
    work_mode_score = _score_work_mode(profile, job)
    breakdown["work_mode"] = work_mode_score

    # 5. Location / work auth
    location_score = _score_location(profile, job)
    breakdown["location"] = location_score

    # 6. Salary
    salary_score = _score_salary(profile, job)
    breakdown["salary"] = salary_score

    # Weighted composite
    raw_score = sum(
        (score / 100) * WEIGHTS[key]
        for key, score in breakdown.items()
    )

    # Red flag penalty
    triggered_red_flags = _check_red_flags(profile, job)
    red_flag_penalty = min(30, len(triggered_red_flags) * 10)
    final_score = max(0, round(raw_score - red_flag_penalty))

    breakdown["red_flags"] = max(0, 100 - len(triggered_red_flags) * 33)

    verdict = _verdict(final_score)

    return ScoringResult(
        fit_score=final_score,
        fit_verdict=verdict,
        score_breakdown=breakdown,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        triggered_red_flags=triggered_red_flags,
        met_must_have=met_must,
        unmet_must_have=unmet_must,
    )


# ─── Component scorers ────────────────────────────────────────────────────────

def _score_skills(profile: "CandidateProfile", job: "Job") -> tuple[int, list[str], list[str]]:
    """Score skill overlap between profile skills and job requirements."""
    if not profile.skills:
        return 50, [], []  # can't penalise if no profile skills provided

    profile_skills_lower = {s.lower().strip() for s in profile.skills}
    job_text = _job_skill_corpus(job).lower()

    matched = []
    missing = []

    for skill in profile.skills:
        if _skill_in_text(skill.lower(), job_text):
            matched.append(skill)

    # From job requirements, find what we're missing
    for req in job.requirements:
        req_lower = req.lower()
        if not any(_skill_in_text(s.lower(), req_lower) for s in profile.skills):
            # Only surface skills-like requirements (short phrases)
            if len(req.split()) <= 8:
                missing.append(req)

    total_job_skills = max(1, len(job.requirements) or 5)
    score = round((len(matched) / max(1, len(profile.skills))) * 100)
    # Penalise if many job requirements not met
    coverage_penalty = max(0, len(missing) - 3) * 5
    score = max(0, min(100, score - coverage_penalty))

    return score, matched[:20], missing[:20]


def _score_experience(profile: "CandidateProfile", job: "Job") -> int:
    if profile.years_of_experience is None:
        return 60  # neutral — no profile data

    required = job.required_experience_years
    if required is None:
        return 75  # no requirement stated — slight positive

    candidate_yoe = profile.years_of_experience

    if candidate_yoe >= required:
        overshoot = candidate_yoe - required
        # Over-qualified by >10 years can be a mild negative
        if overshoot > 10:
            return 75
        return 100
    else:
        shortfall = required - candidate_yoe
        if shortfall <= 1:
            return 80  # within 1 year — still plausible
        elif shortfall <= 3:
            return 55
        elif shortfall <= 5:
            return 30
        else:
            return 10


def _score_must_have(profile: "CandidateProfile", job: "Job") -> tuple[int, list[str], list[str]]:
    if not profile.must_have:
        return 75, [], []  # no criteria set — neutral

    job_text = (
        (job.description or "") + " " +
        " ".join(job.requirements or []) + " " +
        (job.title or "") + " " +
        (job.company or "")
    ).lower()

    met = [c for c in profile.must_have if c.lower() in job_text]
    unmet = [c for c in profile.must_have if c.lower() not in job_text]

    score = round((len(met) / len(profile.must_have)) * 100) if profile.must_have else 100
    return score, met, unmet


def _score_work_mode(profile: "CandidateProfile", job: "Job") -> int:
    pref = (profile.work_mode_preference or "any").lower()
    job_mode = (job.work_mode or "").lower()

    if pref == "any" or not job_mode:
        return 80  # neutral — unknown or no preference
    if pref == job_mode:
        return 100
    # Partial matches
    if pref == "hybrid" and job_mode in ("remote", "onsite"):
        return 60
    if pref == "remote" and job_mode == "hybrid":
        return 50
    if pref == "remote" and job_mode == "onsite":
        return 10
    if pref == "onsite" and job_mode == "remote":
        return 50
    return 50


def _score_location(profile: "CandidateProfile", job: "Job") -> int:
    # If job is remote, location doesn't matter much
    if (job.work_mode or "").lower() == "remote":
        return 100

    if not profile.location or not job.location:
        return 70  # unknown — can't penalise

    profile_loc_lower = profile.location.lower()
    job_loc_lower = job.location.lower()

    # Simple token overlap check
    profile_tokens = set(re.split(r"[\s,/]+", profile_loc_lower))
    job_tokens = set(re.split(r"[\s,/]+", job_loc_lower))
    overlap = profile_tokens & job_tokens

    if overlap:
        return 100

    # Work auth check — if job mentions a country not in candidate's auth list
    if profile.work_auth_countries:
        auth_lower = [c.lower() for c in profile.work_auth_countries]
        for token in job_tokens:
            if len(token) > 2 and not any(token in a for a in auth_lower):
                return 40  # possible auth issue

    return 60  # different location but no auth conflict detected


def _score_salary(profile: "CandidateProfile", job: "Job") -> int:
    if profile.salary_min is None or job.salary_max is None:
        return 75  # unknown — neutral

    # Job max must meet candidate minimum
    if job.salary_max >= profile.salary_min:
        if profile.salary_max and job.salary_min and job.salary_min >= profile.salary_max:
            return 100  # job pays above candidate target
        return 85
    else:
        gap_pct = (profile.salary_min - job.salary_max) / profile.salary_min * 100
        if gap_pct <= 10:
            return 60
        elif gap_pct <= 25:
            return 30
        else:
            return 0


def _check_red_flags(profile: "CandidateProfile", job: "Job") -> list[str]:
    if not profile.red_flags:
        return []

    job_text = (
        (job.description or "") + " " +
        (job.title or "") + " " +
        (job.company or "") + " " +
        " ".join(job.requirements or [])
    ).lower()

    triggered = [flag for flag in profile.red_flags if flag.lower() in job_text]
    return triggered


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _job_skill_corpus(job: "Job") -> str:
    return " ".join(filter(None, [
        job.description or "",
        " ".join(job.requirements or []),
        " ".join(job.responsibilities or []),
        job.title or "",
    ]))


def _skill_in_text(skill: str, text: str) -> bool:
    """Check if a skill appears in text with word-boundary awareness."""
    # Exact match or as a standalone word/phrase
    escaped = re.escape(skill)
    return bool(re.search(rf"\b{escaped}\b", text, re.IGNORECASE))


def _verdict(score: int) -> str:
    for threshold, label in VERDICT_THRESHOLDS:
        if score >= threshold:
            return label
    return "Not Recommended"
