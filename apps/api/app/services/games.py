"""Business logic for games."""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Load, selectinload

from app.models import Game, GameProvider, RoiSet
from app.schemas import GameCreate, GameUpdate, RoiSetCreate
from app.services import roi_sets as roi_set_service


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


async def _resolve_roi_set(
    db: AsyncSession,
    provider_id: int,
    roi_set_id: int | None,
    roi_set_data: RoiSetCreate | None,
) -> RoiSet | None:
    """Select an existing ROI set or create a new one for a provider.

    Args:
        db: Active database session.
        provider_id: Provider that owns the ROI set.
        roi_set_id: Existing ROI set selected by the user.
        roi_set_data: New ROI set to create and attach to the provider.

    Returns:
        The referenced or newly added ROI set, or ``None`` when the game does
        not use one.

    Raises:
        HTTPException: If the selected set does not belong to the provider.
    """
    if roi_set_data is not None:
        return await roi_set_service.add_roi_set(
            db, provider_id, roi_set_data
        )
    if roi_set_id is not None:
        return await roi_set_service.get_roi_set_for_provider(
            db, provider_id, roi_set_id
        )
    return None


def _game_options() -> tuple[Load, ...]:
    """Return eager-load options for a game's ROI set and its ROIs."""
    return (
        selectinload(Game.roi_set).selectinload(RoiSet.rois),
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
    roi_set = await _resolve_roi_set(
        db, data.game_provider_id, data.roi_set_id, data.roi_set
    )

    game = Game(
        name=data.name,
        number_of_spins=data.number_of_spins,
        spin_wait_seconds=data.spin_wait_seconds,
        url=data.url,
        game_provider_id=data.game_provider_id,
        roi_set=roi_set,
    )
    db.add(game)
    await db.commit()
    return await get_game(db, game.id)


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
        .options(*_game_options())
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
    stmt = (
        select(Game)
        .where(Game.id == game_id)
        .options(*_game_options())
    )
    game = await db.scalar(stmt)
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
        .options(*_game_options())
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

    A selected or newly created ROI set must belong to the game's provider.
    Changing the provider without choosing a ROI set clears the existing
    association because sets are scoped to a single provider.

    Args:
        db: Active database session.
        game_id: Primary key of the game.
        data: Fields to update. Omitted or null fields are left unchanged.

    Returns:
        The updated game.

    Raises:
        HTTPException: If the game, the referenced game provider, or the
            selected ROI set does not exist or belongs to another provider.
    """
    game = await get_game(db, game_id)
    updates = data.model_dump(exclude_unset=True, exclude_none=True)

    provider_id = updates.get("game_provider_id", game.game_provider_id)
    provider_changed = provider_id != game.game_provider_id
    if provider_changed:
        await _ensure_game_provider(db, provider_id)

    if data.roi_set is not None:
        game.roi_set = await roi_set_service.add_roi_set(
            db, provider_id, data.roi_set
        )
    elif "roi_set_id" in data.model_fields_set:
        if data.roi_set_id is None:
            game.roi_set = None
        else:
            game.roi_set = await roi_set_service.get_roi_set_for_provider(
                db, provider_id, data.roi_set_id
            )
    elif provider_changed:
        game.roi_set = None

    for field, value in updates.items():
        if field in {"roi_set", "roi_set_id"}:
            continue
        setattr(game, field, value)

    await db.commit()
    return await get_game(db, game_id)


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
