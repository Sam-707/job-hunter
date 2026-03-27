import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, JSON, ForeignKey, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JobAnalysis(Base):
    __tablename__ = "job_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # FK
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), unique=True)
    profile_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id"))

    # Fit scoring — deterministic
    fit_score: Mapped[int] = mapped_column(Integer)  # 0-100
    fit_verdict: Mapped[str] = mapped_column(String(50))  # Strong Match | Possible Match | Weak Match | Not Recommended
    score_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    # score_breakdown keys: skills, experience, location, salary, work_mode, must_have, red_flags

    # Fit explanation — LLM generated
    matching_qualifications: Mapped[list] = mapped_column(JSON, default=list)
    missing_qualifications: Mapped[list] = mapped_column(JSON, default=list)
    transferable_strengths: Mapped[list] = mapped_column(JSON, default=list)
    experience_alignment: Mapped[str | None] = mapped_column(Text, nullable=True)
    salary_alignment: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_alignment: Mapped[str | None] = mapped_column(Text, nullable=True)
    risks_and_red_flags: Mapped[list] = mapped_column(JSON, default=list)

    # Application support — LLM generated
    job_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    resume_tailoring_suggestions: Mapped[list] = mapped_column(JSON, default=list)
    cover_letter_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_answers: Mapped[list] = mapped_column(JSON, default=list)
    application_checklist: Mapped[list] = mapped_column(JSON, default=list)
    missing_info_checklist: Mapped[list] = mapped_column(JSON, default=list)

    # LLM metadata
    llm_model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    llm_analysis_raw: Mapped[str | None] = mapped_column(Text, nullable=True)  # raw LLM response for debugging

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="analysis")
