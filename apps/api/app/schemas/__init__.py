"""Pydantic request and response schemas."""

from app.schemas.game import GameBase, GameCreate, GamePage, GameRead, GameUpdate
from app.schemas.game_provider import (
    GameProviderBase,
    GameProviderCreate,
    GameProviderPage,
    GameProviderRead,
    GameProviderUpdate,
)
from app.schemas.roi import (
    RoiBase,
    RoiCreate,
    RoiRead,
    RoiSetCreate,
    RoiSetRead,
    RoiSetUpdate,
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
    "RoiBase",
    "RoiCreate",
    "RoiRead",
    "RoiSetCreate",
    "RoiSetRead",
    "RoiSetUpdate",
]
