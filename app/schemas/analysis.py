from datetime import datetime
from pydantic import BaseModel, Field


class ScoreBreakdown(BaseModel):
    skills: int = Field(0, ge=0, le=100, description="Skills overlap score")
    experience: int = Field(0, ge=0, le=100, description="Experience alignment score")
    location: int = Field(0, ge=0, le=100, description="Location/work-auth score")
    salary: int = Field(0, ge=0, le=100, description="Salary alignment score")
    work_mode: int = Field(0, ge=0, le=100, description="Work mode preference match")
    must_have: int = Field(0, ge=0, le=100, description="Must-have criteria met")
    red_flags: int = Field(0, ge=0, le=100, description="Red flag penalty (100 = no red flags)")


class AnalysisResponse(BaseModel):
    id: str
    created_at: datetime
    job_id: str
    profile_id: str

    # Deterministic scoring
    fit_score: int
    fit_verdict: str
    score_breakdown: dict

    # LLM explanation
    matching_qualifications: list[str]
    missing_qualifications: list[str]
    transferable_strengths: list[str]
    experience_alignment: str | None
    salary_alignment: str | None
    location_alignment: str | None
    risks_and_red_flags: list[str]

    # Application support
    job_summary: str | None
    resume_tailoring_suggestions: list[str]
    cover_letter_draft: str | None
    suggested_answers: list[dict]
    application_checklist: list[str]
    missing_info_checklist: list[str]

    llm_model_used: str | None

    model_config = {"from_attributes": True}
