"""Game request and response schemas."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.roi import RoiSetCreate, RoiSetRead


class GameBase(BaseModel):
    """Fields shared by game schemas."""

    name: str = Field(min_length=1, max_length=255)
    number_of_spins: int = Field(default=1000, ge=0)
    url: str = Field(min_length=1, max_length=2048)
    game_provider_id: int = Field(gt=0)


class GameCreate(GameBase):
    """Payload for creating a game.

    Provide either an existing provider ROI set through ``roi_set_id`` or a
    new set through ``roi_set``. A new set is also added to the provider.
    """

    roi_set_id: int | None = Field(default=None, gt=0)
    roi_set: RoiSetCreate | None = None

    @model_validator(mode="after")
    def _single_roi_source(self) -> "GameCreate":
        """Reject payloads that select and create a ROI set at once."""
        if self.roi_set_id is not None and self.roi_set is not None:
            raise ValueError("Provide either roi_set_id or roi_set, not both")
        return self


class GameUpdate(BaseModel):
    """Payload for updating a game. Omitted fields are left unchanged."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    number_of_spins: int | None = Field(default=None, ge=0)
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    game_provider_id: int | None = Field(default=None, gt=0)
    roi_set_id: int | None = Field(default=None, gt=0)
    roi_set: RoiSetCreate | None = None

    @model_validator(mode="after")
    def _single_roi_source(self) -> "GameUpdate":
        """Reject payloads that select and create a ROI set at once."""
        if self.roi_set_id is not None and self.roi_set is not None:
            raise ValueError("Provide either roi_set_id or roi_set, not both")
        return self


class GameRead(GameBase):
    """Game returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    roi_set_id: int | None = None
    roi_set: RoiSetRead | None = None


class GamePage(BaseModel):
    """A page of games."""

    items: list[GameRead]
    total: int
    skip: int
    limit: int
