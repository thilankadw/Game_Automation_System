"""Game provider CRUD routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas import (
    GameProviderCreate,
    GameProviderPage,
    GameProviderRead,
    GameProviderUpdate,
)
from app.services import game_providers as provider_service

router = APIRouter(prefix="/game-providers", tags=["game-providers"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "",
    response_model=GameProviderRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_game_provider(
    payload: GameProviderCreate, db: DbSession
) -> GameProviderRead:
    """Create a game provider.

    Args:
        payload: Provider name to create.
        db: Active database session.

    Returns:
        The created game provider.
    """
    provider = await provider_service.create_game_provider(db, payload)
    return GameProviderRead.model_validate(provider)


@router.get("", response_model=GameProviderPage)
async def list_game_providers(
    db: DbSession,
    name: Annotated[str | None, Query(max_length=255)] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> GameProviderPage:
    """List game providers with optional name filtering and pagination.

    Args:
        db: Active database session.
        name: Case-insensitive substring to match against provider names.
        skip: Number of providers to skip.
        limit: Maximum number of providers to return.

    Returns:
        A page of providers together with the total matching count.
    """
    providers, total = await provider_service.list_game_providers(
        db, name=name, skip=skip, limit=limit
    )
    return GameProviderPage(
        items=[GameProviderRead.model_validate(provider) for provider in providers],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{provider_id}", response_model=GameProviderRead)
async def get_game_provider(
    provider_id: int, db: DbSession
) -> GameProviderRead:
    """Return a single game provider.

    Args:
        provider_id: Primary key of the game provider.
        db: Active database session.

    Returns:
        The matching game provider.

    Raises:
        HTTPException: If the game provider does not exist.
    """
    provider = await provider_service.get_game_provider(db, provider_id)
    return GameProviderRead.model_validate(provider)


@router.patch("/{provider_id}", response_model=GameProviderRead)
async def update_game_provider(
    provider_id: int, payload: GameProviderUpdate, db: DbSession
) -> GameProviderRead:
    """Update a game provider.

    Args:
        provider_id: Primary key of the game provider.
        payload: Fields to update.
        db: Active database session.

    Returns:
        The updated game provider.

    Raises:
        HTTPException: If the game provider does not exist.
    """
    provider = await provider_service.update_game_provider(db, provider_id, payload)
    return GameProviderRead.model_validate(provider)


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_game_provider(provider_id: int, db: DbSession) -> None:
    """Delete a game provider.

    Args:
        provider_id: Primary key of the game provider.
        db: Active database session.

    Raises:
        HTTPException: If the game provider does not exist.
    """
    await provider_service.delete_game_provider(db, provider_id)
