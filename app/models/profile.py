import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Identity
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Experience
    resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    years_of_experience: Mapped[float | None] = mapped_column(nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Skills & Credentials — stored as JSON arrays
    skills: Mapped[list] = mapped_column(JSON, default=list)
    certifications: Mapped[list] = mapped_column(JSON, default=list)
    languages: Mapped[list] = mapped_column(JSON, default=list)

    # Targets
    target_roles: Mapped[list] = mapped_column(JSON, default=list)
    target_industries: Mapped[list] = mapped_column(JSON, default=list)
    target_companies: Mapped[list] = mapped_column(JSON, default=list)

    # Preferences
    salary_min: Mapped[int | None] = mapped_column(nullable=True)
    salary_max: Mapped[int | None] = mapped_column(nullable=True)
    salary_currency: Mapped[str] = mapped_column(String(10), default="EUR")
    work_auth_countries: Mapped[list] = mapped_column(JSON, default=list)
    work_mode_preference: Mapped[str | None] = mapped_column(String(50), nullable=True)  # remote|hybrid|onsite|any

    # Fit criteria
    must_have: Mapped[list] = mapped_column(JSON, default=list)
    nice_to_have: Mapped[list] = mapped_column(JSON, default=list)
    red_flags: Mapped[list] = mapped_column(JSON, default=list)

    # Meta
    is_active: Mapped[bool] = mapped_column(default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
