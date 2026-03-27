"""Initial schema — candidate_profiles, jobs, job_analyses

Revision ID: 0001
Revises:
Create Date: 2026-03-27
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "candidate_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=True),
        sa.Column("portfolio_url", sa.String(500), nullable=True),
        sa.Column("github_url", sa.String(500), nullable=True),
        sa.Column("resume_text", sa.Text, nullable=True),
        sa.Column("years_of_experience", sa.Float, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("skills", sa.JSON, nullable=False),
        sa.Column("certifications", sa.JSON, nullable=False),
        sa.Column("languages", sa.JSON, nullable=False),
        sa.Column("target_roles", sa.JSON, nullable=False),
        sa.Column("target_industries", sa.JSON, nullable=False),
        sa.Column("target_companies", sa.JSON, nullable=False),
        sa.Column("salary_min", sa.Integer, nullable=True),
        sa.Column("salary_max", sa.Integer, nullable=True),
        sa.Column("salary_currency", sa.String(10), nullable=False, server_default="EUR"),
        sa.Column("work_auth_countries", sa.JSON, nullable=False),
        sa.Column("work_mode_preference", sa.String(50), nullable=True),
        sa.Column("must_have", sa.JSON, nullable=False),
        sa.Column("nice_to_have", sa.JSON, nullable=False),
        sa.Column("red_flags", sa.JSON, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("notes", sa.Text, nullable=True),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("input_type", sa.String(20), nullable=False),
        sa.Column("input_url", sa.Text, nullable=True),
        sa.Column("input_text", sa.Text, nullable=True),
        sa.Column("raw_content", sa.Text, nullable=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("company", sa.String(500), nullable=True),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column("employment_type", sa.String(100), nullable=True),
        sa.Column("work_mode", sa.String(50), nullable=True),
        sa.Column("salary_raw", sa.String(200), nullable=True),
        sa.Column("salary_min", sa.Integer, nullable=True),
        sa.Column("salary_max", sa.Integer, nullable=True),
        sa.Column("salary_currency", sa.String(10), nullable=True),
        sa.Column("application_link", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("requirements", sa.JSON, nullable=False),
        sa.Column("responsibilities", sa.JSON, nullable=False),
        sa.Column("nice_to_have", sa.JSON, nullable=False),
        sa.Column("required_experience_years", sa.Float, nullable=True),
        sa.Column("extraction_method", sa.String(50), nullable=True),
        sa.Column("extraction_confidence", sa.String(20), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="to_review"),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("profile_id", sa.String(36), sa.ForeignKey("candidate_profiles.id"), nullable=True),
    )

    op.create_table(
        "job_analyses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("jobs.id"), nullable=False, unique=True),
        sa.Column("profile_id", sa.String(36), sa.ForeignKey("candidate_profiles.id"), nullable=False),
        sa.Column("fit_score", sa.Integer, nullable=False),
        sa.Column("fit_verdict", sa.String(50), nullable=False),
        sa.Column("score_breakdown", sa.JSON, nullable=False),
        sa.Column("matching_qualifications", sa.JSON, nullable=False),
        sa.Column("missing_qualifications", sa.JSON, nullable=False),
        sa.Column("transferable_strengths", sa.JSON, nullable=False),
        sa.Column("experience_alignment", sa.Text, nullable=True),
        sa.Column("salary_alignment", sa.Text, nullable=True),
        sa.Column("location_alignment", sa.Text, nullable=True),
        sa.Column("risks_and_red_flags", sa.JSON, nullable=False),
        sa.Column("job_summary", sa.Text, nullable=True),
        sa.Column("resume_tailoring_suggestions", sa.JSON, nullable=False),
        sa.Column("cover_letter_draft", sa.Text, nullable=True),
        sa.Column("suggested_answers", sa.JSON, nullable=False),
        sa.Column("application_checklist", sa.JSON, nullable=False),
        sa.Column("missing_info_checklist", sa.JSON, nullable=False),
        sa.Column("llm_model_used", sa.String(100), nullable=True),
        sa.Column("llm_analysis_raw", sa.Text, nullable=True),
    )

    # Indexes
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_profile_id", "jobs", ["profile_id"])
    op.create_index("ix_jobs_created_at", "jobs", ["created_at"])
    op.create_index("ix_profiles_is_active", "candidate_profiles", ["is_active"])


def downgrade() -> None:
    op.drop_table("job_analyses")
    op.drop_table("jobs")
    op.drop_table("candidate_profiles")
