from datetime import datetime
from typing import Literal
from pydantic import BaseModel, EmailStr, HttpUrl, Field, field_validator


WorkModePreference = Literal["remote", "hybrid", "onsite", "any"]


class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    location: str | None = Field(None, max_length=255)
    linkedin_url: str | None = Field(None, max_length=500)
    portfolio_url: str | None = Field(None, max_length=500)
    github_url: str | None = Field(None, max_length=500)

    resume_text: str | None = None
    years_of_experience: float | None = Field(None, ge=0, le=60)
    summary: str | None = None

    skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)

    target_roles: list[str] = Field(default_factory=list)
    target_industries: list[str] = Field(default_factory=list)
    target_companies: list[str] = Field(default_factory=list)

    salary_min: int | None = Field(None, ge=0)
    salary_max: int | None = Field(None, ge=0)
    salary_currency: str = Field(default="EUR", max_length=10)
    work_auth_countries: list[str] = Field(default_factory=list)
    work_mode_preference: WorkModePreference | None = None

    must_have: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    notes: str | None = None


class ProfileUpdate(ProfileCreate):
    name: str | None = None  # make name optional for partial updates


class ProfileResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    name: str
    email: str | None
    phone: str | None
    location: str | None
    linkedin_url: str | None
    portfolio_url: str | None
    github_url: str | None
    resume_text: str | None
    years_of_experience: float | None
    summary: str | None
    skills: list[str]
    certifications: list[str]
    languages: list[str]
    target_roles: list[str]
    target_industries: list[str]
    target_companies: list[str]
    salary_min: int | None
    salary_max: int | None
    salary_currency: str
    work_auth_countries: list[str]
    work_mode_preference: str | None
    must_have: list[str]
    nice_to_have: list[str]
    red_flags: list[str]
    is_active: bool
    notes: str | None

    model_config = {"from_attributes": True}
