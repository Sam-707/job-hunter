"""
All LLM prompt templates live here.
Keeping them in one file makes them easy to audit, iterate, and version.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.profile import CandidateProfile
    from app.models.job import Job
    from app.scoring.fit_scorer import ScoringResult


ANALYSIS_SYSTEM = """You are a senior career advisor and hiring expert.
Your job is to give honest, specific, and actionable analysis of how well a candidate matches a job.
Do not produce vague encouragements or filler. Be direct and truthful even when the news is bad.
Always respond in valid JSON matching the schema you are given."""

MATERIALS_SYSTEM = """You are a professional career coach and expert resume/cover letter writer.
Produce concrete, tailored content — not generic templates.
Mirror the language and keywords from the job posting.
Always respond in valid JSON matching the schema you are given."""


def build_analysis_prompt(
    profile: "CandidateProfile",
    job: "Job",
    scoring: "ScoringResult",
) -> str:
    profile_text = _profile_summary(profile)
    job_text = _job_summary(job)
    score_text = _score_summary(scoring)

    return f"""Analyze the candidate-job fit based on the structured data below.

## Candidate Profile
{profile_text}

## Job Posting
{job_text}

## Deterministic Scoring (already computed)
{score_text}

## Your Task
Return a JSON object with EXACTLY these keys:
{{
  "matching_qualifications": ["<specific matching qualification>", ...],
  "missing_qualifications": ["<specific missing qualification>", ...],
  "transferable_strengths": ["<strength that transfers despite not being exact match>", ...],
  "experience_alignment": "<1-2 sentences: how candidate experience aligns or doesn't>",
  "salary_alignment": "<1-2 sentences: salary match analysis, or null if salary data missing>",
  "location_alignment": "<1 sentence: location/remote/auth analysis>",
  "risks_and_red_flags": ["<specific risk or red flag>", ...]
}}

Rules:
- Be specific. Name actual skills, technologies, or requirements from the posting.
- Be honest. If the candidate is underqualified, say so clearly.
- Do not repeat the score. Focus on the human explanation.
- If data is missing, note it briefly and move on.
- Each list should have 2-6 items. Empty lists are fine if there is nothing honest to say.
"""


def build_materials_prompt(
    profile: "CandidateProfile",
    job: "Job",
    scoring: "ScoringResult",
) -> str:
    profile_text = _profile_summary(profile)
    job_text = _job_summary(job)

    return f"""Generate application support materials for this candidate applying to this job.

## Candidate Profile
{profile_text}

## Job Posting
{job_text}

## Fit Score
{scoring.fit_score}/100 — {scoring.fit_verdict}

## Your Task
Return a JSON object with EXACTLY these keys:
{{
  "job_summary": "<2-3 sentence plain-language summary of what this job actually is>",
  "resume_tailoring_suggestions": [
    "<specific suggestion: e.g. 'Add X bullet under Y role showing Z result'>",
    ...
  ],
  "cover_letter_draft": "<full cover letter draft, 3-4 paragraphs, tailored to this specific role>",
  "suggested_answers": [
    {{
      "question": "<common application question>",
      "answer": "<tailored answer, 2-4 sentences>"
    }},
    ...
  ],
  "application_checklist": [
    "<action item: e.g. 'Upload resume as PDF'>",
    ...
  ],
  "missing_info_checklist": [
    "<thing candidate should gather before applying: e.g. 'Get reference from X'>",
    ...
  ]
}}

Rules:
- Cover letter must open with a specific hook about this role/company, not a generic opener.
- Resume suggestions must reference specific sections or bullets — not vague advice.
- Include 3-5 suggested_answers for the most common questions for this role type.
- Application checklist: 4-8 concrete action steps.
- Missing info checklist: only include if genuinely missing.
"""


# ─── Formatters ──────────────────────────────────────────────────────────────

def _profile_summary(p: "CandidateProfile") -> str:
    lines = [
        f"Name: {p.name}",
        f"Location: {p.location or 'Not specified'}",
        f"Years of Experience: {p.years_of_experience or 'Not specified'}",
        f"Skills: {', '.join(p.skills) if p.skills else 'Not specified'}",
        f"Target Roles: {', '.join(p.target_roles) if p.target_roles else 'Not specified'}",
        f"Work Mode Preference: {p.work_mode_preference or 'Any'}",
        f"Work Authorization: {', '.join(p.work_auth_countries) if p.work_auth_countries else 'Not specified'}",
        f"Salary Target: {_salary_str(p.salary_min, p.salary_max, p.salary_currency)}",
        f"Must-Have Criteria: {', '.join(p.must_have) if p.must_have else 'None set'}",
        f"Red Flags: {', '.join(p.red_flags) if p.red_flags else 'None set'}",
    ]
    if p.summary:
        lines.append(f"\nProfessional Summary:\n{p.summary}")
    if p.resume_text:
        lines.append(f"\nResume (excerpt):\n{p.resume_text[:2000]}")
    return "\n".join(lines)


def _job_summary(j: "Job") -> str:
    lines = [
        f"Title: {j.title or 'Unknown'}",
        f"Company: {j.company or 'Unknown'}",
        f"Location: {j.location or 'Unknown'}",
        f"Work Mode: {j.work_mode or 'Unknown'}",
        f"Employment Type: {j.employment_type or 'Unknown'}",
        f"Salary: {j.salary_raw or _salary_str(j.salary_min, j.salary_max, j.salary_currency) or 'Not specified'}",
        f"Required Experience: {j.required_experience_years or 'Not specified'} years",
    ]
    if j.requirements:
        lines.append(f"\nRequirements:\n" + "\n".join(f"- {r}" for r in j.requirements[:15]))
    if j.responsibilities:
        lines.append(f"\nResponsibilities:\n" + "\n".join(f"- {r}" for r in j.responsibilities[:10]))
    if j.description:
        lines.append(f"\nFull Description (excerpt):\n{j.description[:2000]}")
    return "\n".join(lines)


def _score_summary(s: "ScoringResult") -> str:
    lines = [f"Overall: {s.fit_score}/100 — {s.fit_verdict}"]
    for key, val in s.score_breakdown.items():
        lines.append(f"  {key}: {val}/100")
    if s.triggered_red_flags:
        lines.append(f"Triggered Red Flags: {', '.join(s.triggered_red_flags)}")
    if s.unmet_must_have:
        lines.append(f"Unmet Must-Have Criteria: {', '.join(s.unmet_must_have)}")
    return "\n".join(lines)


def _salary_str(low: int | None, high: int | None, currency: str | None) -> str:
    if not low and not high:
        return "Not specified"
    currency = currency or ""
    if low and high:
        return f"{currency}{low:,} - {currency}{high:,}"
    if low:
        return f"{currency}{low:,}+"
    return f"Up to {currency}{high:,}"
