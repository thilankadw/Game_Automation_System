"""Game provider request and response schemas."""

from pydantic import BaseModel, ConfigDict, Field


class GameProviderBase(BaseModel):
    """Fields shared by game provider schemas."""

    name: str = Field(min_length=1, max_length=255)


class GameProviderCreate(GameProviderBase):
    """Payload for creating a game provider."""


class GameProviderUpdate(BaseModel):
    """Payload for updating a game provider. Omitted fields are left unchanged."""

    name: str | None = Field(default=None, min_length=1, max_length=255)


class GameProviderRead(GameProviderBase):
    """Game provider returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
