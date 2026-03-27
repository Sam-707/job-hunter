from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import get_settings
from app.database import init_db
from app.utils.errors import validation_exception_handler, generic_exception_handler
from app.utils.logging import configure_logging, get_logger

settings = get_settings()
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", env=settings.app_env, db=settings.database_url[:40])
    await init_db()
    logger.info("database_ready")
    yield
    logger.info("shutdown")


app = FastAPI(
    title="Job Hunter API",
    description=(
        "Submit job postings (URL or text), get fit analysis against your profile, "
        "and generate tailored application materials."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — open for dev, restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.is_production else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Routes
app.include_router(api_router)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": "1.0.0", "env": settings.app_env}
