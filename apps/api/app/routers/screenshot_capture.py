"""Automated screenshot capture session routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas import (
    ScreenshotCaptureSessionCreate,
    ScreenshotCaptureSessionRead,
    StoredScreenshotSessionRead,
)
from app.services.screenshot_capture import (
    delete_all_stored_sessions,
    delete_stored_session,
    list_stored_sessions,
    manager,
)

router = APIRouter(
    prefix="/screenshot-capture/sessions", tags=["screenshot-capture"]
)
game_router = APIRouter(prefix="/games", tags=["screenshot-capture"])

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


@game_router.get(
    "/{game_id}/screenshots",
    response_model=list[StoredScreenshotSessionRead],
)
async def list_game_screenshots(
    game_id: int, db: DbSession
) -> list[StoredScreenshotSessionRead]:
    """List screenshots stored on disk for a game, newest session first.

    Args:
        game_id: Primary key of the game.
        db: Active database session.

    Returns:
        Stored capture sessions with their screenshot URLs.

    Raises:
        HTTPException: If the game or its provider does not exist.
    """
    sessions = await list_stored_sessions(db, game_id)
    return [
        StoredScreenshotSessionRead.model_validate(session)
        for session in sessions
    ]


@game_router.delete(
    "/{game_id}/screenshots/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_game_screenshot_session(
    game_id: int, session_id: str, db: DbSession
) -> None:
    """Delete one stored screenshot session for a game.

    Args:
        game_id: Primary key of the game.
        session_id: Stored session folder to remove.
        db: Active database session.

    Raises:
        HTTPException: If the game, provider, or session is missing, the
            session is still capturing, or deletion fails.
    """
    await delete_stored_session(db, game_id, session_id)


@game_router.delete(
    "/{game_id}/screenshots",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_all_game_screenshots(game_id: int, db: DbSession) -> None:
    """Delete every stored screenshot session for a game.

    Args:
        game_id: Primary key of the game.
        db: Active database session.

    Raises:
        HTTPException: If the game or provider is missing, a capture is still
            running for the game, or deletion fails.
    """
    await delete_all_stored_sessions(db, game_id)
