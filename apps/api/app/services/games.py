"""Business logic for games."""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Game, GameProvider
from app.schemas import GameCreate, GameUpdate


async def _ensure_game_provider(db: AsyncSession, provider_id: int) -> None:
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


async def create_game(db: AsyncSession, data: GameCreate) -> Game:
    """Create and persist a game.

    Args:
        db: Active database session.
        data: Validated game creation payload.

    Returns:
        The persisted game.

    Raises:
        HTTPException: If the referenced game provider does not exist.
    """
    await _ensure_game_provider(db, data.game_provider_id)

    game = Game(
        name=data.name,
        number_of_spins=data.number_of_spins,
        url=data.url,
        game_provider_id=data.game_provider_id,
    )
    db.add(game)
    await db.commit()
    await db.refresh(game)
    return game


async def list_games(
    db: AsyncSession,
    *,
    name: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Game], int]:
    """Return a page of games, optionally filtered by name.

    Args:
        db: Active database session.
        name: Case-insensitive substring to match against game names.
        skip: Number of games to skip.
        limit: Maximum number of games to return.

    Returns:
        A tuple of the games on the requested page and the total count.
    """
    filters = []
    if name:
        filters.append(Game.name.ilike(f"%{name}%"))

    count_stmt = select(func.count()).select_from(Game).where(*filters)
    total = await db.scalar(count_stmt) or 0

    stmt = (
        select(Game)
        .where(*filters)
        .order_by(Game.id)
        .offset(skip)
        .limit(limit)
    )
    games = list(await db.scalars(stmt))
    return games, total


async def get_game(db: AsyncSession, game_id: int) -> Game:
    """Return a game by ID.

    Args:
        db: Active database session.
        game_id: Primary key of the game.

    Returns:
        The matching game.

    Raises:
        HTTPException: If the game does not exist.
    """
    game = await db.get(Game, game_id)
    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )
    return game


async def get_game_by_name(db: AsyncSession, name: str) -> Game:
    """Return a game by case-insensitive name.

    Args:
        db: Active database session.
        name: Name of the game to find.

    Returns:
        The first matching game.

    Raises:
        HTTPException: If no game matches the name.
    """
    stmt = (
        select(Game)
        .where(func.lower(Game.name) == name.lower())
        .order_by(Game.id)
        .limit(1)
    )
    game = await db.scalar(stmt)
    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )
    return game


async def update_game(
    db: AsyncSession, game_id: int, data: GameUpdate
) -> Game:
    """Update a game and persist the changes.

    Args:
        db: Active database session.
        game_id: Primary key of the game.
        data: Fields to update. Omitted or null fields are left unchanged.

    Returns:
        The updated game.

    Raises:
        HTTPException: If the game or the referenced game provider does not
            exist.
    """
    game = await get_game(db, game_id)
    updates = data.model_dump(exclude_unset=True, exclude_none=True)

    provider_id = updates.get("game_provider_id")
    if provider_id is not None and provider_id != game.game_provider_id:
        await _ensure_game_provider(db, provider_id)

    for field, value in updates.items():
        setattr(game, field, value)

    await db.commit()
    await db.refresh(game)
    return game


async def delete_game(db: AsyncSession, game_id: int) -> None:
    """Delete a game.

    Args:
        db: Active database session.
        game_id: Primary key of the game.

    Raises:
        HTTPException: If the game does not exist.
    """
    game = await get_game(db, game_id)
    await db.delete(game)
    await db.commit()
