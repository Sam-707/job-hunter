from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import Job
from app.schemas.job import JobSubmitRequest, JobStatusUpdate, ExtractedJobData
from app.extractors.url_extractor import fetch_and_extract
from app.extractors.text_parser import parse_job_text
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def submit_job(db: AsyncSession, request: JobSubmitRequest) -> Job:
    """Accept a job submission (URL or text), extract, persist, and return."""

    if request.url:
        logger.info("job_submit_url", url=request.url)
        extracted = await fetch_and_extract(request.url)
        job = Job(
            input_type="url",
            input_url=request.url,
            raw_content=extracted.pop("raw_content", None),
            profile_id=request.profile_id,
            **_safe_extracted_fields(extracted),
        )
    else:
        logger.info("job_submit_text", text_length=len(request.text or ""))
        extracted = parse_job_text(request.text or "")
        job = Job(
            input_type="text",
            input_text=request.text,
            raw_content=None,
            profile_id=request.profile_id,
            **_safe_extracted_fields(extracted),
        )

    db.add(job)
    await db.commit()
    await db.refresh(job)
    logger.info("job_created", id=job.id, confidence=job.extraction_confidence)
    return job


async def get_job(db: AsyncSession, job_id: str) -> Job | None:
    result = await db.execute(
        select(Job)
        .where(Job.id == job_id)
        .options(selectinload(Job.analysis))
    )
    return result.scalar_one_or_none()


async def list_jobs(
    db: AsyncSession,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Job]:
    query = select(Job).options(selectinload(Job.analysis)).order_by(Job.created_at.desc())
    if status:
        query = query.where(Job.status == status)
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_job_status(db: AsyncSession, job_id: str, update: JobStatusUpdate) -> Job | None:
    job = await get_job(db, job_id)
    if not job:
        return None
    job.status = update.status
    if update.notes is not None:
        job.notes = update.notes
    if update.deadline is not None:
        job.deadline = update.deadline
    if update.status == "applied":
        job.applied_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)
    logger.info("job_status_updated", id=job_id, status=update.status)
    return job


async def delete_job(db: AsyncSession, job_id: str) -> bool:
    job = await get_job(db, job_id)
    if not job:
        return False
    await db.delete(job)
    await db.commit()
    logger.info("job_deleted", id=job_id)
    return True


def _safe_extracted_fields(extracted: dict) -> dict:
    """Filter extraction output to only Job model fields."""
    allowed = {
        "title", "company", "location", "employment_type", "work_mode",
        "salary_raw", "salary_min", "salary_max", "salary_currency",
        "application_link", "description", "requirements", "responsibilities",
        "nice_to_have", "required_experience_years",
        "extraction_method", "extraction_confidence",
    }
    return {k: v for k, v in extracted.items() if k in allowed}
