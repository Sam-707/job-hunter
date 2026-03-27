from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.job import JobSubmitRequest, JobStatusUpdate, JobResponse, JobListItem
from app.schemas.analysis import AnalysisResponse
from app.services import job_service, profile_service, analysis_service
from app.utils.errors import NotFoundError, BadRequestError
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/", response_model=JobResponse, status_code=201)
async def submit_job(
    request: JobSubmitRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a job for analysis. Accepts either a URL or raw text.

    If `run_analysis=true` (default), analysis runs immediately (synchronous).
    The response includes the job record. Fetch `/jobs/{id}/analysis` for results.
    """
    # Resolve profile
    profile_id = request.profile_id
    if not profile_id:
        profile = await profile_service.get_active_profile(db)
        if not profile:
            raise BadRequestError(
                "No active profile found. Create a profile at POST /api/v1/profile first."
            )
        profile_id = profile.id
    else:
        profile = await profile_service.get_profile(db, profile_id)
        if not profile:
            raise NotFoundError("Profile", profile_id)

    # Override request profile_id so job gets linked
    request_data = request.model_copy(update={"profile_id": profile_id})
    job = await job_service.submit_job(db, request_data)

    # Run analysis
    if request.run_analysis:
        try:
            await analysis_service.run_analysis(db, job, profile)
        except Exception as e:
            # Analysis failure should not fail the job submission
            logger.error("analysis_failed_on_submit", job_id=job.id, error=str(e))

    # Re-fetch to include analysis relationship
    job = await job_service.get_job(db, job.id)
    return job


@router.get("/", response_model=list[JobListItem])
async def list_jobs(
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all tracked jobs with summary info."""
    jobs = await job_service.list_jobs(db, status=status, limit=limit, offset=offset)
    items = []
    for job in jobs:
        analysis = job.analysis
        items.append(JobListItem(
            id=job.id,
            created_at=job.created_at,
            title=job.title,
            company=job.company,
            location=job.location,
            status=job.status,
            fit_score=analysis.fit_score if analysis else None,
            fit_verdict=analysis.fit_verdict if analysis else None,
        ))
    return items


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get full job record."""
    job = await job_service.get_job(db, job_id)
    if not job:
        raise NotFoundError("Job", job_id)
    return job


@router.get("/{job_id}/analysis", response_model=AnalysisResponse)
async def get_analysis(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get the fit analysis for a job."""
    job = await job_service.get_job(db, job_id)
    if not job:
        raise NotFoundError("Job", job_id)
    analysis = await analysis_service.get_analysis(db, job_id)
    if not analysis:
        raise NotFoundError("Analysis", job_id)
    return analysis


@router.post("/{job_id}/analyze", response_model=AnalysisResponse)
async def rerun_analysis(
    job_id: str,
    profile_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Re-run analysis for a job (e.g. after updating the profile)."""
    job = await job_service.get_job(db, job_id)
    if not job:
        raise NotFoundError("Job", job_id)

    pid = profile_id or job.profile_id
    if not pid:
        profile = await profile_service.get_active_profile(db)
        if not profile:
            raise BadRequestError("No profile found to analyze against.")
    else:
        profile = await profile_service.get_profile(db, pid)
        if not profile:
            raise NotFoundError("Profile", pid)

    return await analysis_service.run_analysis(db, job, profile)


@router.patch("/{job_id}/status", response_model=JobResponse)
async def update_status(
    job_id: str,
    update: JobStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update job tracking status and optional notes/deadline."""
    job = await job_service.update_job_status(db, job_id, update)
    if not job:
        raise NotFoundError("Job", job_id)
    return job


@router.delete("/{job_id}", status_code=204)
async def delete_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a job and its analysis."""
    deleted = await job_service.delete_job(db, job_id)
    if not deleted:
        raise NotFoundError("Job", job_id)
