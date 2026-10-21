"""Business logic for provider ROI sets."""

import re

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Game, GameProvider, Roi, RoiSet
from app.schemas import RoiCreate, RoiSetCreate, RoiSetUpdate

_OPTION_NAME = re.compile(r"Option (\d+)")


async def _ensure_provider(db: AsyncSession, provider_id: int) -> None:
    """Validate that a game provider exists.

    Args:
        db: Active database session.
        provider_id: Primary key of the game provider.

    Raises:
        HTTPException: If the game provider does not exist.
    """
    if await db.get(GameProvider, provider_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game provider not found",
        )


def _build_rois(rois: list[RoiCreate]) -> list[Roi]:
    """Create ROI ORM objects from validated ROI payloads."""
    return [
        Roi(
            name=roi.name,
            x=roi.x,
            y=roi.y,
            width=roi.width,
            height=roi.height,
        )
        for roi in rois
    ]


async def _next_option_name(db: AsyncSession, provider_id: int) -> str:
    """Return the next available ``Option N`` name for a provider."""
    names = await db.scalars(
        select(RoiSet.name).where(RoiSet.game_provider_id == provider_id)
    )
    highest = 0
    for name in names:
        match = _OPTION_NAME.fullmatch(name)
        if match is not None:
            highest = max(highest, int(match.group(1)))
    return f"Option {highest + 1}"


async def _ensure_name_available(
    db: AsyncSession,
    provider_id: int,
    name: str,
    *,
    roi_set_id: int | None = None,
) -> None:
    """Validate that a ROI set name is unique within a provider.

    Args:
        db: Active database session.
        provider_id: Primary key of the owning game provider.
        name: Candidate ROI set name.
        roi_set_id: Existing set being updated, excluded from the check.

    Raises:
        HTTPException: If another set already uses the name.
    """
    stmt = select(RoiSet.id).where(
        RoiSet.game_provider_id == provider_id,
        func.lower(RoiSet.name) == name.lower(),
    )
    if roi_set_id is not None:
        stmt = stmt.where(RoiSet.id != roi_set_id)
    if await db.scalar(stmt) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ROI set name already exists for this game provider",
        )


async def add_roi_set(
    db: AsyncSession, provider_id: int, data: RoiSetCreate
) -> RoiSet:
    """Add a ROI set to the session without committing it.

    This helper lets game creation add a new provider ROI set in the same
    transaction as the game so a failure cannot leave an orphaned set.

    Args:
        db: Active database session.
        provider_id: Primary key of the owning game provider.
        data: Validated ROI set creation payload.

    Returns:
        The flushed ROI set.

    Raises:
        HTTPException: If the provider does not exist or the name is taken.
    """
    await _ensure_provider(db, provider_id)
    name = data.name or await _next_option_name(db, provider_id)
    await _ensure_name_available(db, provider_id, name)

    roi_set = RoiSet(
        name=name,
        game_provider_id=provider_id,
        rois=_build_rois(data.rois),
    )
    db.add(roi_set)
    await db.flush()
    return roi_set


async def create_roi_set(
    db: AsyncSession, provider_id: int, data: RoiSetCreate
) -> RoiSet:
    """Create and persist a ROI set for a game provider.

    Args:
        db: Active database session.
        provider_id: Primary key of the owning game provider.
        data: Validated ROI set creation payload.

    Returns:
        The persisted ROI set.

    Raises:
        HTTPException: If the provider does not exist, the name is taken, or
            the database rejects the write.
    """
    roi_set = await add_roi_set(db, provider_id, data)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ROI set name already exists for this game provider",
        ) from exc
    return roi_set


async def list_roi_sets(
    db: AsyncSession, provider_id: int
) -> list[RoiSet]:
    """Return all ROI sets owned by a game provider.

    Args:
        db: Active database session.
        provider_id: Primary key of the game provider.

    Returns:
        The provider's ROI sets ordered by ID.

    Raises:
        HTTPException: If the game provider does not exist.
    """
    await _ensure_provider(db, provider_id)
    stmt = (
        select(RoiSet)
        .where(RoiSet.game_provider_id == provider_id)
        .options(selectinload(RoiSet.rois))
        .order_by(RoiSet.id)
    )
    return list(await db.scalars(stmt))


async def get_roi_set(db: AsyncSession, roi_set_id: int) -> RoiSet:
    """Return a ROI set by ID.

    Args:
        db: Active database session.
        roi_set_id: Primary key of the ROI set.

    Returns:
        The matching ROI set with its ROIs loaded.

    Raises:
        HTTPException: If the ROI set does not exist.
    """
    stmt = (
        select(RoiSet)
        .where(RoiSet.id == roi_set_id)
        .options(selectinload(RoiSet.rois))
    )
    roi_set = await db.scalar(stmt)
    if roi_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ROI set not found",
        )
    return roi_set


async def get_roi_set_for_provider(
    db: AsyncSession, provider_id: int, roi_set_id: int
) -> RoiSet:
    """Return a ROI set only when it belongs to the given provider.

    Args:
        db: Active database session.
        provider_id: Primary key of the expected owning provider.
        roi_set_id: Primary key of the ROI set.

    Returns:
        The matching ROI set with its ROIs loaded.

    Raises:
        HTTPException: If the set does not exist or belongs to another
            provider.
    """
    roi_set = await get_roi_set(db, roi_set_id)
    if roi_set.game_provider_id != provider_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ROI set does not belong to the game provider",
        )
    return roi_set


async def update_roi_set(
    db: AsyncSession, roi_set_id: int, data: RoiSetUpdate
) -> RoiSet:
    """Update a ROI set and persist the changes.

    Supplying ``rois`` replaces the complete ROI list for the set.

    Args:
        db: Active database session.
        roi_set_id: Primary key of the ROI set.
        data: Fields to update. Omitted or null fields are left unchanged.

    Returns:
        The updated ROI set.

    Raises:
        HTTPException: If the set does not exist or the new name is taken.
    """
    roi_set = await get_roi_set(db, roi_set_id)

    if data.name is not None and data.name != roi_set.name:
        await _ensure_name_available(
            db,
            roi_set.game_provider_id,
            data.name,
            roi_set_id=roi_set.id,
        )
        roi_set.name = data.name

    if data.rois is not None:
        roi_set.rois.clear()
        await db.flush()
        roi_set.rois.extend(_build_rois(data.rois))

    await db.commit()
    return roi_set


async def delete_roi_set(db: AsyncSession, roi_set_id: int) -> None:
    """Delete a ROI set and detach it from any games using it.

    Args:
        db: Active database session.
        roi_set_id: Primary key of the ROI set.

    Raises:
        HTTPException: If the ROI set does not exist.
    """
    roi_set = await get_roi_set(db, roi_set_id)
    await db.execute(
        update(Game)
        .where(Game.roi_set_id == roi_set_id)
        .values(roi_set_id=None)
    )
    await db.delete(roi_set)
    await db.commit()
