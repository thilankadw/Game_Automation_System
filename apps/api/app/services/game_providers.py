"""Business logic for game providers."""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GameProvider
from app.schemas import GameProviderCreate, GameProviderUpdate


async def create_game_provider(
    db: AsyncSession, data: GameProviderCreate
) -> GameProvider:
    """Create and persist a game provider.

    Args:
        db: Active database session.
        data: Validated provider creation payload.

    Returns:
        The persisted game provider.
    """
    provider = GameProvider(name=data.name)
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return provider


async def list_game_providers(
    db: AsyncSession,
    *,
    name: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[GameProvider], int]:
    """Return a page of game providers, optionally filtered by name.

    Args:
        db: Active database session.
        name: Case-insensitive substring to match against provider names.
        skip: Number of providers to skip.
        limit: Maximum number of providers to return.

    Returns:
        A tuple of the providers on the requested page and the total count.
    """
    filters = []
    if name:
        filters.append(GameProvider.name.ilike(f"%{name}%"))

    count_stmt = select(func.count()).select_from(GameProvider).where(*filters)
    total = await db.scalar(count_stmt) or 0

    stmt = (
        select(GameProvider)
        .where(*filters)
        .order_by(GameProvider.id)
        .offset(skip)
        .limit(limit)
    )
    providers = list(await db.scalars(stmt))
    return providers, total


async def get_game_provider(db: AsyncSession, provider_id: int) -> GameProvider:
    """Return a game provider by ID.

    Args:
        db: Active database session.
        provider_id: Primary key of the game provider.

    Returns:
        The matching game provider.

    Raises:
        HTTPException: If the game provider does not exist.
    """
    provider = await db.get(GameProvider, provider_id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game provider not found",
        )
    return provider


async def update_game_provider(
    db: AsyncSession, provider_id: int, data: GameProviderUpdate
) -> GameProvider:
    """Update a game provider and persist the changes.

    Args:
        db: Active database session.
        provider_id: Primary key of the game provider.
        data: Fields to update. Omitted or null fields are left unchanged.

    Returns:
        The updated game provider.

    Raises:
        HTTPException: If the game provider does not exist.
    """
    provider = await get_game_provider(db, provider_id)
    updates = data.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in updates.items():
        setattr(provider, field, value)

    await db.commit()
    await db.refresh(provider)
    return provider


async def delete_game_provider(db: AsyncSession, provider_id: int) -> None:
    """Delete a game provider.

    Args:
        db: Active database session.
        provider_id: Primary key of the game provider.

    Raises:
        HTTPException: If the game provider does not exist.
    """
    provider = await get_game_provider(db, provider_id)
    await db.delete(provider)
    await db.commit()
