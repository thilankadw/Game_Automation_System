"""Automated screenshot capture session routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas import (
    ScreenshotCaptureSessionCreate,
    ScreenshotCaptureSessionRead,
)
from app.services.screenshot_capture import manager

router = APIRouter(
    prefix="/screenshot-capture/sessions", tags=["screenshot-capture"]
)

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "",
    response_model=ScreenshotCaptureSessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def start_screenshot_capture(
    payload: ScreenshotCaptureSessionCreate, db: DbSession
) -> ScreenshotCaptureSessionRead:
    """Start an automated spin-and-screenshot run for a game.

    Args:
        payload: The game to capture.
        db: Active database session.

    Returns:
        The created capture session, which continues in the background.

    Raises:
        HTTPException: If the game does not exist, its ROI set cannot drive a
            capture, or another capture is already running for the game.
    """
    session = await manager.start_session(db, payload.game_id)
    return ScreenshotCaptureSessionRead.model_validate(session)


@router.get("", response_model=list[ScreenshotCaptureSessionRead])
async def list_screenshot_capture_sessions() -> list[
    ScreenshotCaptureSessionRead
]:
    """List screenshot capture sessions, newest last."""
    return [
        ScreenshotCaptureSessionRead.model_validate(session)
        for session in manager.list_sessions()
    ]


@router.get(
    "/{session_id}", response_model=ScreenshotCaptureSessionRead
)
async def get_screenshot_capture_session(
    session_id: str,
) -> ScreenshotCaptureSessionRead:
    """Return a screenshot capture session with its current progress.

    Args:
        session_id: Identifier returned by the start endpoint.

    Returns:
        The matching session.

    Raises:
        HTTPException: If the session is unknown.
    """
    session = manager.get_session(session_id)
    return ScreenshotCaptureSessionRead.model_validate(session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def stop_screenshot_capture_session(session_id: str) -> None:
    """Stop a running screenshot capture and close its Chrome context.

    Args:
        session_id: Identifier returned by the start endpoint.

    Raises:
        HTTPException: If the session is unknown.
    """
    manager.get_session(session_id)
    await manager.stop_session(session_id)
