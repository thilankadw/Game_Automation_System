"""Provider ROI set routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas import RoiSetCreate, RoiSetRead, RoiSetUpdate
from app.services import roi_sets as roi_set_service

router = APIRouter(tags=["roi-sets"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/game-providers/{provider_id}/roi-sets",
    response_model=RoiSetRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_roi_set(
    provider_id: int, payload: RoiSetCreate, db: DbSession
) -> RoiSetRead:
    """Create a ROI set for a game provider.

    Args:
        provider_id: Primary key of the owning game provider.
        payload: ROI set name and ROIs. The name defaults to ``Option N``.
        db: Active database session.

    Returns:
        The created ROI set.

    Raises:
        HTTPException: If the provider does not exist or the name is taken.
    """
    roi_set = await roi_set_service.create_roi_set(db, provider_id, payload)
    return RoiSetRead.model_validate(roi_set)


@router.get(
    "/game-providers/{provider_id}/roi-sets",
    response_model=list[RoiSetRead],
)
async def list_roi_sets(
    provider_id: int, db: DbSession
) -> list[RoiSetRead]:
    """List the ROI sets owned by a game provider.

    Args:
        provider_id: Primary key of the game provider.
        db: Active database session.

    Returns:
        The provider's ROI sets ordered by ID.

    Raises:
        HTTPException: If the game provider does not exist.
    """
    roi_sets = await roi_set_service.list_roi_sets(db, provider_id)
    return [RoiSetRead.model_validate(roi_set) for roi_set in roi_sets]


@router.get("/roi-sets/{roi_set_id}", response_model=RoiSetRead)
async def get_roi_set(roi_set_id: int, db: DbSession) -> RoiSetRead:
    """Return a single ROI set.

    Args:
        roi_set_id: Primary key of the ROI set.
        db: Active database session.

    Returns:
        The matching ROI set.

    Raises:
        HTTPException: If the ROI set does not exist.
    """
    roi_set = await roi_set_service.get_roi_set(db, roi_set_id)
    return RoiSetRead.model_validate(roi_set)


@router.patch("/roi-sets/{roi_set_id}", response_model=RoiSetRead)
async def update_roi_set(
    roi_set_id: int, payload: RoiSetUpdate, db: DbSession
) -> RoiSetRead:
    """Update a ROI set.

    Supplying ``rois`` replaces the entire ROI list for the set.

    Args:
        roi_set_id: Primary key of the ROI set.
        payload: Fields to update.
        db: Active database session.

    Returns:
        The updated ROI set.

    Raises:
        HTTPException: If the ROI set does not exist or the new name is taken.
    """
    roi_set = await roi_set_service.update_roi_set(db, roi_set_id, payload)
    return RoiSetRead.model_validate(roi_set)


@router.delete("/roi-sets/{roi_set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_roi_set(roi_set_id: int, db: DbSession) -> None:
    """Delete a ROI set and detach it from games.

    Args:
        roi_set_id: Primary key of the ROI set.
        db: Active database session.

    Raises:
        HTTPException: If the ROI set does not exist.
    """
    await roi_set_service.delete_roi_set(db, roi_set_id)
