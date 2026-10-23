"""OCR extraction routes for stored game screenshots."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas import (
    OcrRunCreate,
    OcrRunRead,
    OcrSpinReadingPage,
    OcrSpinReadingRead,
)
from app.services import games as game_service
from app.services import ocr_extraction

router = APIRouter(prefix="/games", tags=["ocr"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/{game_id}/ocr-runs",
    response_model=OcrRunRead,
    status_code=status.HTTP_201_CREATED,
)
async def start_ocr_run(
    game_id: int, payload: OcrRunCreate, db: DbSession
) -> OcrRunRead:
    """Start reading a stored screenshot session for a game.

    Args:
        game_id: Primary key of the game.
        payload: Stored screenshot session to read.
        db: Active database session.

    Returns:
        The created run, which continues in the background.

    Raises:
        HTTPException: If the game, ROI set, or screenshot session is missing,
            the session is still capturing, or OCR is already running for it.
    """
    run = await ocr_extraction.manager.start_run(
        db, game_id, payload.session_id
    )
    return OcrRunRead.model_validate(run)


@router.get(
    "/{game_id}/ocr-runs", response_model=list[OcrRunRead]
)
async def list_ocr_runs(game_id: int, db: DbSession) -> list[OcrRunRead]:
    """List OCR runs for a game, oldest first."""
    await game_service.get_game(db, game_id)
    return [
        OcrRunRead.model_validate(run)
        for run in ocr_extraction.manager.list_runs(game_id)
    ]


@router.get(
    "/{game_id}/ocr-runs/{run_id}", response_model=OcrRunRead
)
async def get_ocr_run(game_id: int, run_id: str) -> OcrRunRead:
    """Return one OCR run with its current progress."""
    run = ocr_extraction.manager.get_run(game_id, run_id)
    return OcrRunRead.model_validate(run)


@router.delete(
    "/{game_id}/ocr-runs/{run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def stop_ocr_run(game_id: int, run_id: str) -> None:
    """Stop a running OCR extraction and keep readings already stored."""
    await ocr_extraction.manager.stop_run(game_id, run_id)


@router.get(
    "/{game_id}/ocr-readings",
    response_model=OcrSpinReadingPage,
)
async def list_ocr_readings(
    game_id: int,
    db: DbSession,
    session_id: Annotated[str | None, Query(max_length=128)] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> OcrSpinReadingPage:
    """List stored OCR readings for a game, newest spin first."""
    readings, total = await ocr_extraction.list_readings(
        db,
        game_id,
        session_id=session_id,
        skip=skip,
        limit=limit,
    )
    return OcrSpinReadingPage(
        items=[
            OcrSpinReadingRead.model_validate(reading)
            for reading in readings
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.delete(
    "/{game_id}/ocr-readings/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_ocr_session_readings(
    game_id: int, session_id: str, db: DbSession
) -> None:
    """Delete all OCR readings extracted from one stored session.

    Args:
        game_id: Primary key of the game.
        session_id: Stored screenshot session to clear.
        db: Active database session.

    Raises:
        HTTPException: If the game is missing or an OCR run is still writing
            readings for the session.
    """
    await ocr_extraction.delete_readings(
        db, game_id, session_id=session_id
    )


@router.delete(
    "/{game_id}/ocr-readings",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_all_ocr_readings(game_id: int, db: DbSession) -> None:
    """Delete every OCR reading stored for a game.

    Args:
        game_id: Primary key of the game.
        db: Active database session.

    Raises:
        HTTPException: If the game is missing or an OCR run is still writing
            readings for the game.
    """
    await ocr_extraction.delete_readings(db, game_id)
