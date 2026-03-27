import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Input — what was submitted
    input_type: Mapped[str] = mapped_column(String(20))  # url | text
    input_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)  # full page content before parsing

    # Extracted / normalized job data
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    company: Mapped[str | None] = mapped_column(String(500), nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(100), nullable=True)  # full-time|part-time|contract
    work_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)  # remote|hybrid|onsite
    salary_raw: Mapped[str | None] = mapped_column(String(200), nullable=True)
    salary_min: Mapped[int | None] = mapped_column(nullable=True)
    salary_max: Mapped[int | None] = mapped_column(nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    application_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)  # cleaned full description

    # Structured extraction results (may be partial)
    requirements: Mapped[list] = mapped_column(JSON, default=list)
    responsibilities: Mapped[list] = mapped_column(JSON, default=list)
    nice_to_have: Mapped[list] = mapped_column(JSON, default=list)
    required_experience_years: Mapped[float | None] = mapped_column(nullable=True)

    # Extraction metadata
    extraction_method: Mapped[str | None] = mapped_column(String(50), nullable=True)  # trafilatura|bs4|raw|manual
    extraction_confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)  # high|medium|low

    # Tracking
    status: Mapped[str] = mapped_column(String(50), default="to_review")
    # Statuses: to_review | good_fit | applied | interviewing | rejected | archived
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # FK
    profile_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("candidate_profiles.id"), nullable=True)

    # Relationships
    analysis: Mapped["JobAnalysis | None"] = relationship("JobAnalysis", back_populates="job", uselist=False)
