from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import CandidateProfile
from app.schemas.profile import ProfileCreate, ProfileUpdate
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def create_profile(db: AsyncSession, data: ProfileCreate) -> CandidateProfile:
    profile = CandidateProfile(**data.model_dump())
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    logger.info("profile_created", id=profile.id, name=profile.name)
    return profile


async def get_profile(db: AsyncSession, profile_id: str) -> CandidateProfile | None:
    result = await db.execute(select(CandidateProfile).where(CandidateProfile.id == profile_id))
    return result.scalar_one_or_none()


async def get_active_profile(db: AsyncSession) -> CandidateProfile | None:
    """Return the most recently created active profile."""
    result = await db.execute(
        select(CandidateProfile)
        .where(CandidateProfile.is_active == True)
        .order_by(CandidateProfile.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_profiles(db: AsyncSession) -> list[CandidateProfile]:
    result = await db.execute(select(CandidateProfile).order_by(CandidateProfile.created_at.desc()))
    return list(result.scalars().all())


async def update_profile(db: AsyncSession, profile_id: str, data: ProfileUpdate) -> CandidateProfile | None:
    profile = await get_profile(db, profile_id)
    if not profile:
        return None
    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(profile, key, value)
    await db.commit()
    await db.refresh(profile)
    logger.info("profile_updated", id=profile.id)
    return profile


async def delete_profile(db: AsyncSession, profile_id: str) -> bool:
    profile = await get_profile(db, profile_id)
    if not profile:
        return False
    await db.delete(profile)
    await db.commit()
    logger.info("profile_deleted", id=profile_id)
    return True
