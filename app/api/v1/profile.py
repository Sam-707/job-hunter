from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.profile import ProfileCreate, ProfileUpdate, ProfileResponse
from app.services import profile_service
from app.utils.errors import NotFoundError

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.post("/", response_model=ProfileResponse, status_code=201)
async def create_profile(data: ProfileCreate, db: AsyncSession = Depends(get_db)):
    """Create the candidate profile."""
    return await profile_service.create_profile(db, data)


@router.get("/", response_model=list[ProfileResponse])
async def list_profiles(db: AsyncSession = Depends(get_db)):
    """List all candidate profiles."""
    return await profile_service.list_profiles(db)


@router.get("/active", response_model=ProfileResponse)
async def get_active_profile(db: AsyncSession = Depends(get_db)):
    """Get the current active profile."""
    profile = await profile_service.get_active_profile(db)
    if not profile:
        raise HTTPException(status_code=404, detail="No active profile found. Create one first.")
    return profile


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(profile_id: str, db: AsyncSession = Depends(get_db)):
    """Get a profile by ID."""
    profile = await profile_service.get_profile(db, profile_id)
    if not profile:
        raise NotFoundError("Profile", profile_id)
    return profile


@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_profile(profile_id: str, data: ProfileUpdate, db: AsyncSession = Depends(get_db)):
    """Update a profile."""
    profile = await profile_service.update_profile(db, profile_id, data)
    if not profile:
        raise NotFoundError("Profile", profile_id)
    return profile


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(profile_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a profile."""
    deleted = await profile_service.delete_profile(db, profile_id)
    if not deleted:
        raise NotFoundError("Profile", profile_id)
