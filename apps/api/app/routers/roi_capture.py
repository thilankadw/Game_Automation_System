"""ROI capture session routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas import RoiCaptureSessionCreate, RoiCaptureSessionRead
from app.services.roi_capture import manager

router = APIRouter(prefix="/roi-capture/sessions", tags=["roi-capture"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "",
    response_model=RoiCaptureSessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def start_roi_capture(
    payload: RoiCaptureSessionCreate, db: DbSession
) -> RoiCaptureSessionRead:
    """Open a headed Chrome window to draw ROIs for a game.

    Args:
        payload: The game to capture.
        db: Active database session.

    Returns:
        The created capture session.

    Raises:
        HTTPException: If the game does not exist, Chrome cannot launch, or
            the game URL cannot be opened.
    """
    session = await manager.start_session(db, payload.game_id)
    return RoiCaptureSessionRead.model_validate(session)


@router.get("", response_model=list[RoiCaptureSessionRead])
async def list_roi_capture_sessions() -> list[RoiCaptureSessionRead]:
    """List the live ROI capture sessions."""
    return [
        RoiCaptureSessionRead.model_validate(session)
        for session in manager.list_sessions()
    ]


@router.get("/{session_id}", response_model=RoiCaptureSessionRead)
async def get_roi_capture_session(
    session_id: str,
) -> RoiCaptureSessionRead:
    """Return a single live ROI capture session.

    Args:
        session_id: Identifier returned by the start endpoint.

    Returns:
        The matching capture session.

    Raises:
        HTTPException: If the session is unknown or already closed.
    """
    session = manager.get_session(session_id)
    return RoiCaptureSessionRead.model_validate(session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def stop_roi_capture_session(session_id: str) -> None:
    """Close a live ROI capture session and its Chrome window.

    Args:
        session_id: Identifier returned by the start endpoint.

    Raises:
        HTTPException: If the session is unknown or already closed.
    """
    manager.get_session(session_id)
    await manager.stop_session(session_id)
