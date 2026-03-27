import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app
from app.models import CandidateProfile, Job


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DB_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine):
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def sample_profile() -> CandidateProfile:
    return CandidateProfile(
        id="test-profile-001",
        name="Test Candidate",
        location="Berlin, Germany",
        years_of_experience=5.0,
        skills=["Python", "FastAPI", "React", "PostgreSQL", "Docker"],
        target_roles=["Backend Engineer", "Full Stack Developer"],
        work_mode_preference="hybrid",
        work_auth_countries=["Germany", "EU"],
        salary_min=70_000,
        salary_max=90_000,
        salary_currency="EUR",
        must_have=["Python", "startup"],
        red_flags=["MLM", "unpaid trial"],
    )


@pytest.fixture
def sample_job_good_fit() -> Job:
    return Job(
        id="test-job-good",
        input_type="text",
        title="Senior Python Developer",
        company="Acme GmbH",
        location="Berlin, Germany",
        work_mode="hybrid",
        employment_type="full-time",
        salary_min=75_000,
        salary_max=90_000,
        salary_currency="EUR",
        description="Python FastAPI startup Berlin hybrid",
        requirements=["Python", "FastAPI", "PostgreSQL", "Docker", "3+ years experience"],
        responsibilities=["Build APIs", "Code review"],
        required_experience_years=3.0,
    )


@pytest.fixture
def sample_job_weak_fit() -> Job:
    return Job(
        id="test-job-weak",
        input_type="text",
        title="Senior Java Architect",
        company="Enterprise Corp",
        location="Frankfurt, Germany",
        work_mode="onsite",
        employment_type="full-time",
        salary_min=50_000,
        salary_max=60_000,
        salary_currency="EUR",
        description="Java Spring Boot enterprise banking onsite",
        requirements=["Java", "Spring Boot", "Oracle DB", "10+ years", "TOGAF certification"],
        responsibilities=["Architect enterprise systems"],
        required_experience_years=10.0,
    )
