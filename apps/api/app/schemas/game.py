"""Game request and response schemas."""

from pydantic import BaseModel, ConfigDict, Field


class GameBase(BaseModel):
    """Fields shared by game schemas."""

    name: str = Field(min_length=1, max_length=255)
    number_of_spins: int = Field(ge=0)
    url: str = Field(min_length=1, max_length=2048)
    game_provider_id: int = Field(gt=0)


class GameCreate(GameBase):
    """Payload for creating a game."""


class GameUpdate(BaseModel):
    """Payload for updating a game. Omitted fields are left unchanged."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    number_of_spins: int | None = Field(default=None, ge=0)
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    game_provider_id: int | None = Field(default=None, gt=0)


class GameRead(GameBase):
    """Game returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int


class GamePage(BaseModel):
    """A page of games."""

    items: list[GameRead]
    total: int
    skip: int
    limit: int
