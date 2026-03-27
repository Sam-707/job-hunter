from datetime import datetime
from typing import Literal
from pydantic import BaseModel, HttpUrl, Field, model_validator


JobStatus = Literal["to_review", "good_fit", "applied", "interviewing", "rejected", "archived"]


class JobSubmitRequest(BaseModel):
    """Accepts either a URL or raw text. Exactly one must be provided."""
    url: str | None = Field(None, description="Job posting URL")
    text: str | None = Field(None, description="Raw job description text")
    profile_id: str | None = Field(None, description="Profile to analyze against. Uses active profile if omitted.")
    run_analysis: bool = Field(True, description="Run fit analysis immediately after extraction")

    @model_validator(mode="after")
    def exactly_one_input(self) -> "JobSubmitRequest":
        if not self.url and not self.text:
            raise ValueError("Provide either 'url' or 'text'.")
        if self.url and self.text:
            raise ValueError("Provide only one of 'url' or 'text', not both.")
        return self


class JobStatusUpdate(BaseModel):
    status: JobStatus
    notes: str | None = None
    deadline: datetime | None = None


class ExtractedJobData(BaseModel):
    title: str | None = None
    company: str | None = None
    location: str | None = None
    employment_type: str | None = None
    work_mode: str | None = None
    salary_raw: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    application_link: str | None = None
    description: str | None = None
    requirements: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    required_experience_years: float | None = None
    extraction_method: str | None = None
    extraction_confidence: str | None = None


class JobResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    input_type: str
    input_url: str | None
    status: str
    title: str | None
    company: str | None
    location: str | None
    employment_type: str | None
    work_mode: str | None
    salary_raw: str | None
    salary_min: int | None
    salary_max: int | None
    salary_currency: str | None
    application_link: str | None
    description: str | None
    requirements: list
    responsibilities: list
    nice_to_have: list
    required_experience_years: float | None
    extraction_method: str | None
    extraction_confidence: str | None
    deadline: datetime | None
    notes: str | None
    applied_at: datetime | None
    profile_id: str | None

    model_config = {"from_attributes": True}


class JobListItem(BaseModel):
    id: str
    created_at: datetime
    title: str | None
    company: str | None
    location: str | None
    status: str
    fit_score: int | None = None
    fit_verdict: str | None = None

    model_config = {"from_attributes": True}
