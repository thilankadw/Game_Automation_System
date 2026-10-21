"""Pydantic request and response schemas."""

from app.schemas.game import GameBase, GameCreate, GamePage, GameRead, GameUpdate
from app.schemas.game_provider import (
    GameProviderBase,
    GameProviderCreate,
    GameProviderPage,
    GameProviderRead,
    GameProviderUpdate,
)

__all__ = [
    "GameBase",
    "GameCreate",
    "GamePage",
    "GameProviderBase",
    "GameProviderCreate",
    "GameProviderPage",
    "GameProviderRead",
    "GameProviderUpdate",
    "GameRead",
    "GameUpdate",
]
