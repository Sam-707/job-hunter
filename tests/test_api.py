"""
API integration tests using an in-memory SQLite database.
No LLM calls are made (no API key in test environment).
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="module")
async def test_engine():
    eng = create_async_engine(TEST_DB_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def test_db(test_engine):
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(test_engine):
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


SAMPLE_PROFILE_PAYLOAD = {
    "name": "Test User",
    "email": "test@example.com",
    "location": "Berlin, Germany",
    "years_of_experience": 5,
    "skills": ["Python", "FastAPI", "PostgreSQL"],
    "target_roles": ["Backend Engineer"],
    "work_mode_preference": "hybrid",
    "work_auth_countries": ["Germany"],
    "salary_min": 70000,
    "salary_max": 90000,
    "salary_currency": "EUR",
    "must_have": ["Python"],
    "red_flags": ["MLM"],
}


# ─── Health ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ─── Profile CRUD ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_profile(client):
    resp = await client.post("/api/v1/profile/", json=SAMPLE_PROFILE_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test User"
    assert data["skills"] == ["Python", "FastAPI", "PostgreSQL"]
    assert "id" in data


@pytest.mark.asyncio
async def test_create_profile_validation_error(client):
    resp = await client.post("/api/v1/profile/", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_active_profile(client):
    await client.post("/api/v1/profile/", json=SAMPLE_PROFILE_PAYLOAD)
    resp = await client.get("/api/v1/profile/active")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test User"


@pytest.mark.asyncio
async def test_profile_not_found(client):
    resp = await client.get("/api/v1/profile/nonexistent-id")
    assert resp.status_code == 404


# ─── Job submission ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_job_text(client):
    # Create profile first
    await client.post("/api/v1/profile/", json=SAMPLE_PROFILE_PAYLOAD)

    job_text = (
        "Senior Python Developer at Startup GmbH in Berlin. "
        "Hybrid work. €75,000 - €90,000. "
        "Requirements: Python, FastAPI, PostgreSQL. 3+ years experience."
    )
    resp = await client.post("/api/v1/jobs/", json={
        "text": job_text,
        "run_analysis": False,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["input_type"] == "text"
    assert "id" in data


@pytest.mark.asyncio
async def test_submit_job_requires_url_or_text(client):
    resp = await client.post("/api/v1/jobs/", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_submit_job_not_both(client):
    resp = await client.post("/api/v1/jobs/", json={
        "url": "https://example.com",
        "text": "some text",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_jobs(client):
    resp = await client.get("/api/v1/jobs/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_job_not_found(client):
    resp = await client.get("/api/v1/jobs/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_job_status(client):
    await client.post("/api/v1/profile/", json=SAMPLE_PROFILE_PAYLOAD)
    job_resp = await client.post("/api/v1/jobs/", json={
        "text": "Python developer role at startup. Hybrid Berlin.",
        "run_analysis": False,
    })
    job_id = job_resp.json()["id"]

    update_resp = await client.patch(f"/api/v1/jobs/{job_id}/status", json={
        "status": "applied",
        "notes": "Applied via company website",
    })
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "applied"
