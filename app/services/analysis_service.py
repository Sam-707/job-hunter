"""
Orchestrates the full analysis pipeline:
1. Deterministic scoring (fast, no LLM)
2. LLM explanation + application materials generation
3. Persists JobAnalysis record
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import JobAnalysis
from app.models.job import Job
from app.models.profile import CandidateProfile
from app.scoring.fit_scorer import score_fit
from app.llm.client import get_llm_client, LLMError
from app.llm.prompts import (
    ANALYSIS_SYSTEM,
    MATERIALS_SYSTEM,
    build_analysis_prompt,
    build_materials_prompt,
)
from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def run_analysis(
    db: AsyncSession,
    job: Job,
    profile: CandidateProfile,
) -> JobAnalysis:
    """Run full fit analysis. Returns (and persists) JobAnalysis."""

    # Delete any existing analysis for this job
    existing = await db.execute(
        select(JobAnalysis).where(JobAnalysis.job_id == job.id)
    )
    old = existing.scalar_one_or_none()
    if old:
        await db.delete(old)
        await db.flush()

    # 1. Deterministic scoring
    scoring = score_fit(profile, job)
    logger.info(
        "scoring_complete",
        job_id=job.id,
        score=scoring.fit_score,
        verdict=scoring.fit_verdict,
    )

    # 2. LLM explanation
    analysis_data = _empty_analysis_data()
    materials_data = _empty_materials_data()
    llm_raw = None

    if settings.has_llm_api_key:
        client = get_llm_client()
        try:
            analysis_data = client.complete_json(
                ANALYSIS_SYSTEM,
                build_analysis_prompt(profile, job, scoring),
            )
            logger.info("llm_analysis_complete", job_id=job.id)
        except LLMError as e:
            logger.error("llm_analysis_failed", job_id=job.id, error=str(e))
            analysis_data["_error"] = str(e)

        try:
            materials_data = client.complete_json(
                MATERIALS_SYSTEM,
                build_materials_prompt(profile, job, scoring),
            )
            logger.info("llm_materials_complete", job_id=job.id)
        except LLMError as e:
            logger.error("llm_materials_failed", job_id=job.id, error=str(e))
            materials_data["_error"] = str(e)
    else:
        logger.warning("llm_skipped_no_api_key", job_id=job.id)

    # 3. Build and persist analysis record
    analysis = JobAnalysis(
        job_id=job.id,
        profile_id=profile.id,

        # Scoring
        fit_score=scoring.fit_score,
        fit_verdict=scoring.fit_verdict,
        score_breakdown=scoring.score_breakdown,

        # LLM explanation
        matching_qualifications=_list_field(analysis_data, "matching_qualifications"),
        missing_qualifications=_list_field(analysis_data, "missing_qualifications"),
        transferable_strengths=_list_field(analysis_data, "transferable_strengths"),
        experience_alignment=_str_field(analysis_data, "experience_alignment"),
        salary_alignment=_str_field(analysis_data, "salary_alignment"),
        location_alignment=_str_field(analysis_data, "location_alignment"),
        risks_and_red_flags=_list_field(analysis_data, "risks_and_red_flags"),

        # Application materials
        job_summary=_str_field(materials_data, "job_summary"),
        resume_tailoring_suggestions=_list_field(materials_data, "resume_tailoring_suggestions"),
        cover_letter_draft=_str_field(materials_data, "cover_letter_draft"),
        suggested_answers=_list_field(materials_data, "suggested_answers"),
        application_checklist=_list_field(materials_data, "application_checklist"),
        missing_info_checklist=_list_field(materials_data, "missing_info_checklist"),

        llm_model_used=settings.llm_model if settings.has_llm_api_key else None,
        llm_analysis_raw=str(analysis_data)[:10_000],
    )

    db.add(analysis)

    # Update job status if it's still "to_review" and score is good
    if job.status == "to_review" and scoring.fit_score >= 60:
        job.status = "good_fit"

    await db.commit()
    await db.refresh(analysis)
    logger.info("analysis_saved", job_id=job.id, analysis_id=analysis.id)
    return analysis


async def get_analysis(db: AsyncSession, job_id: str) -> JobAnalysis | None:
    result = await db.execute(select(JobAnalysis).where(JobAnalysis.job_id == job_id))
    return result.scalar_one_or_none()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _empty_analysis_data() -> dict:
    return {
        "matching_qualifications": [],
        "missing_qualifications": [],
        "transferable_strengths": [],
        "experience_alignment": None,
        "salary_alignment": None,
        "location_alignment": None,
        "risks_and_red_flags": [],
    }


def _empty_materials_data() -> dict:
    return {
        "job_summary": None,
        "resume_tailoring_suggestions": [],
        "cover_letter_draft": None,
        "suggested_answers": [],
        "application_checklist": [],
        "missing_info_checklist": [],
    }


def _list_field(data: dict, key: str) -> list:
    val = data.get(key, [])
    return val if isinstance(val, list) else []


def _str_field(data: dict, key: str) -> str | None:
    val = data.get(key)
    return str(val) if val and not isinstance(val, (list, dict)) else None
