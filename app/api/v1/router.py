from fastapi import APIRouter
from app.api.v1 import profile, jobs

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(profile.router)
api_router.include_router(jobs.router)
