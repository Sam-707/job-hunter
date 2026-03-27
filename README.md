# Job Hunter — Backend API

API-first backend for job fit analysis. Submit a job posting URL or paste a description. Get a structured fit score, honest explanation, and ready-to-use application materials — all matched against your candidate profile.

---

## Architecture

```
app/
├── main.py                  # FastAPI app, lifespan, middleware
├── config.py                # Settings from env vars
├── database.py              # SQLAlchemy async engine + session
│
├── api/v1/
│   ├── profile.py           # CRUD endpoints for candidate profile
│   ├── jobs.py              # Job submission, tracking, status
│   └── router.py            # Mounts all v1 routes under /api/v1
│
├── models/                  # SQLAlchemy ORM models
│   ├── profile.py           # CandidateProfile
│   ├── job.py               # Job
│   └── analysis.py          # JobAnalysis
│
├── schemas/                 # Pydantic v2 request/response contracts
│   ├── profile.py
│   ├── job.py
│   └── analysis.py
│
├── services/                # Business logic orchestration
│   ├── profile_service.py
│   ├── job_service.py
│   └── analysis_service.py  # Runs scoring + LLM, persists results
│
├── extractors/              # Job content extraction
│   ├── url_extractor.py     # Fetch URL → structured fields (trafilatura + BS4)
│   └── text_parser.py       # Parse raw text → structured fields
│
├── scoring/
│   └── fit_scorer.py        # Deterministic heuristic scoring (no LLM)
│
├── llm/
│   ├── client.py            # Anthropic Claude client wrapper (swappable)
│   └── prompts.py           # All prompt templates in one place
│
└── utils/
    ├── logging.py           # structlog configuration
    └── errors.py            # HTTP exception types + handlers
```

**Separation of concerns:**
- Scoring (`fit_scorer.py`) is fully deterministic — no LLM, fully testable, inspectable
- LLM calls (`analysis_service.py`) handle explanation and material generation only
- Extraction (`extractors/`) is independent of scoring and LLM
- LLM is swappable: change `llm/client.py` to use OpenAI, Gemini, or a local model

---

## Database Schema

Three tables:

**`candidate_profiles`** — the candidate's background, preferences, and fit criteria
**`jobs`** — submitted postings: raw input, extracted data, tracking status
**`job_analyses`** — scoring results, LLM explanations, and generated materials (1:1 with jobs)

---

## Local Setup

### 1. Prerequisites
- Python 3.11+
- A Perplexity API key (optional — scoring works without it, LLM outputs will be empty)

### 2. Clone and install

```bash
cd "Job Hunter"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env — set LLM_API_KEY at minimum if you want generated analysis/materials
```

### 4. Start the server

```bash
uvicorn app.main:app --reload
```

API docs available at: `http://localhost:8000/docs`

### 5. Seed sample data (optional)

```bash
python seed.py
```

Creates a sample profile and two jobs (one good fit, one weak fit).

### 6. Run tests

```bash
pytest -v
```

---

## Railway Deploy

This repo is ready for Railway deployment as a web service.

### Required Railway variables

```bash
APP_ENV=production
APP_DEBUG=false
DATABASE_URL=${{Postgres.DATABASE_URL}}
LLM_PROVIDER=perplexity
LLM_API_KEY=pplx-...
LLM_MODEL=sonar
TELEGRAM_BOT_TOKEN=...   # only if you also run the Telegram bot separately
```

Notes:
- Railway Postgres usually injects `DATABASE_URL` as `postgresql://...`; the app converts it to the async SQLAlchemy form automatically.
- `railway.json` starts the API with `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`.
- If you want the Telegram bot on Railway too, deploy it as a separate service with start command `python run_bot.py`.

---

## API Reference

### Health

```
GET /health
```

---

### Profile

```
POST   /api/v1/profile/          Create candidate profile
GET    /api/v1/profile/          List all profiles
GET    /api/v1/profile/active    Get current active profile
GET    /api/v1/profile/{id}      Get profile by ID
PUT    /api/v1/profile/{id}      Update profile
DELETE /api/v1/profile/{id}      Delete profile
```

---

### Jobs

```
POST   /api/v1/jobs/                  Submit a job (URL or text)
GET    /api/v1/jobs/                  List all tracked jobs
GET    /api/v1/jobs/{id}              Get job details
GET    /api/v1/jobs/{id}/analysis     Get fit analysis + materials
POST   /api/v1/jobs/{id}/analyze      Re-run analysis
PATCH  /api/v1/jobs/{id}/status       Update status (applied, rejected, etc.)
DELETE /api/v1/jobs/{id}              Delete job
```

---

## Example API Calls

### Create your profile

```bash
curl -X POST http://localhost:8000/api/v1/profile/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sam Hizam",
    "email": "sam@example.com",
    "location": "Berlin, Germany",
    "years_of_experience": 5,
    "skills": ["Python", "FastAPI", "React", "PostgreSQL", "Docker"],
    "target_roles": ["Backend Engineer", "Full Stack Developer"],
    "work_mode_preference": "hybrid",
    "work_auth_countries": ["Germany", "EU"],
    "salary_min": 70000,
    "salary_max": 95000,
    "salary_currency": "EUR",
    "must_have": ["Python", "startup or product company"],
    "red_flags": ["MLM", "unpaid trial", "door-to-door"],
    "summary": "5 years building SaaS products with Python and React."
  }'
```

### Submit a job via URL

```bash
curl -X POST http://localhost:8000/api/v1/jobs/ \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://jobs.example.com/senior-python-developer",
    "run_analysis": true
  }'
```

### Submit a job via text

```bash
curl -X POST http://localhost:8000/api/v1/jobs/ \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Senior Python Developer at Startup GmbH in Berlin. Hybrid work. €75k-€90k. Requirements: Python, FastAPI, PostgreSQL. 3+ years experience.",
    "run_analysis": true
  }'
```

### Get the fit analysis

```bash
curl http://localhost:8000/api/v1/jobs/{job_id}/analysis
```

**Sample response:**
```json
{
  "fit_score": 82,
  "fit_verdict": "Strong Match",
  "score_breakdown": {
    "skills": 90,
    "experience": 100,
    "must_have": 100,
    "work_mode": 100,
    "location": 100,
    "salary": 85,
    "red_flags": 100
  },
  "matching_qualifications": ["Python expertise", "FastAPI experience", "PostgreSQL familiarity"],
  "missing_qualifications": [],
  "transferable_strengths": ["Startup experience aligns with company stage"],
  "experience_alignment": "Candidate has 5 years; role requires 3. Good fit.",
  "salary_alignment": "Job range (€75k-€90k) overlaps candidate target (€70k-€95k).",
  "location_alignment": "Both based in Berlin. Work mode matches.",
  "risks_and_red_flags": [],
  "job_summary": "A Berlin-based hybrid Python backend role at an early-stage startup...",
  "resume_tailoring_suggestions": ["Lead with FastAPI project impact in bytes served..."],
  "cover_letter_draft": "Dear Hiring Team at Startup GmbH...",
  "suggested_answers": [
    {"question": "Why do you want to work here?", "answer": "..."}
  ],
  "application_checklist": ["Update resume PDF", "Prepare portfolio link", "..."],
  "missing_info_checklist": []
}
```

### Update job tracking status

```bash
curl -X PATCH http://localhost:8000/api/v1/jobs/{job_id}/status \
  -H "Content-Type: application/json" \
  -d '{
    "status": "applied",
    "notes": "Applied via company careers page. Had a good cover letter."
  }'
```

### List jobs filtered by status

```bash
curl "http://localhost:8000/api/v1/jobs/?status=good_fit"
```

---

## Fit Scoring Logic

Scoring is **entirely deterministic** — no LLM involved, fully auditable.

| Component    | Weight | How it's calculated |
|--------------|--------|---------------------|
| Skills       | 35%    | Overlap between profile skills and job requirements (word-boundary match) |
| Experience   | 20%    | Candidate YOE vs required YOE — graceful shortfall thresholds |
| Must-Have    | 20%    | % of profile must-have criteria found in job text |
| Work Mode    | 10%    | Preference vs job's stated work mode |
| Location     | 10%    | Token overlap + work auth check |
| Salary       | 5%     | Overlap between candidate target and job salary range |

**Red flag penalty:** each triggered red flag reduces the final score by up to 10 points (capped at -30).

**Verdicts:**
- 80–100 → Strong Match
- 60–79  → Possible Match
- 40–59  → Weak Match
- 0–39   → Not Recommended

---

## Production Notes

- Switch `DATABASE_URL` to `postgresql+asyncpg://...` in `.env`
- Run migrations with Alembic: `alembic upgrade head`
- Set `APP_ENV=production` to enable JSON logging and restrict CORS
- The LLM client in `app/llm/client.py` is intentionally thin — swap it for any provider
- Scoring and extraction work fully without an API key; only explanations/materials require Claude

---

## Limitations and Assumptions

1. **URL extraction quality varies.** Some job boards (LinkedIn, Greenhouse, Lever) render content client-side with JavaScript. httpx can't run JS — extraction will fall back to raw HTML or fail cleanly. A Playwright-based extractor is a natural next step.
2. **Scoring is heuristic, not ML.** Weights are chosen by judgment, not trained on data. They can be tuned in `fit_scorer.py`.
3. **Single active profile.** MVP assumes one candidate. Multi-tenant support requires adding user auth (JWT) and scoping all queries.
4. **No application submission.** This is by design. The system gives you materials; you submit. Automation requires explicit per-job confirmation.
5. **LLM hallucination risk.** All LLM-generated content (cover letters, suggested answers) should be reviewed before use. Raw LLM output is stored in `llm_analysis_raw` for debugging.
6. **Synchronous LLM calls.** Analysis blocks the request. For high volume, move analysis to a task queue (Celery/ARQ) and poll for results.
