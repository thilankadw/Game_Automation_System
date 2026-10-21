"""Game CRUD routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas import (
    GameCreate,
    GamePage,
    GameRead,
    GameUpdate,
)
from app.services import games as game_service

router = APIRouter(prefix="/games", tags=["games"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=GameRead, status_code=status.HTTP_201_CREATED)
async def create_game(payload: GameCreate, db: DbSession) -> GameRead:
    """Create a game.

    Args:
        payload: Game fields to create.
        db: Active database session.

    Returns:
        The created game.
    """
    game = await game_service.create_game(db, payload)
    return GameRead.model_validate(game)


@router.get("", response_model=GamePage)
async def list_games(
    db: DbSession,
    name: Annotated[str | None, Query(max_length=255)] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> GamePage:
    """List games with optional name filtering and pagination.

    Args:
        db: Active database session.
        name: Case-insensitive substring to match against game names.
        skip: Number of games to skip.
        limit: Maximum number of games to return.

    Returns:
        A page of games together with the total matching count.
    """
    games, total = await game_service.list_games(
        db, name=name, skip=skip, limit=limit
    )
    return GamePage(
        items=[GameRead.model_validate(game) for game in games],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/by-name/{name}", response_model=GameRead)
async def get_game_by_name(name: str, db: DbSession) -> GameRead:
    """Return a game by its case-insensitive name.

    Args:
        name: Name of the game to find.
        db: Active database session.

    Returns:
        The matching game.

    Raises:
        HTTPException: If no game matches the name.
    """
    game = await game_service.get_game_by_name(db, name)
    return GameRead.model_validate(game)


@router.get("/{game_id}", response_model=GameRead)
async def get_game(game_id: int, db: DbSession) -> GameRead:
    """Return a single game.

    Args:
        game_id: Primary key of the game.
        db: Active database session.

    Returns:
        The matching game.

    Raises:
        HTTPException: If the game does not exist.
    """
    game = await game_service.get_game(db, game_id)
    return GameRead.model_validate(game)


@router.patch("/{game_id}", response_model=GameRead)
async def update_game(
    game_id: int, payload: GameUpdate, db: DbSession
) -> GameRead:
    """Update a game.

    Args:
        game_id: Primary key of the game.
        payload: Fields to update.
        db: Active database session.

    Returns:
        The updated game.

    Raises:
        HTTPException: If the game or the referenced game provider does not
            exist.
    """
    game = await game_service.update_game(db, game_id, payload)
    return GameRead.model_validate(game)


@router.delete("/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_game(game_id: int, db: DbSession) -> None:
    """Delete a game.

    Args:
        game_id: Primary key of the game.
        db: Active database session.

    Raises:
        HTTPException: If the game does not exist.
    """
    await game_service.delete_game(db, game_id)
