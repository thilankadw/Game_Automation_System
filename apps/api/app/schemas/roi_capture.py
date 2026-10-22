"""ROI capture session request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RoiCaptureSessionCreate(BaseModel):
    """Payload for opening a live ROI capture window."""

    game_id: int = Field(gt=0)


class RoiCaptureSessionRead(BaseModel):
    """A live ROI capture window returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    game_id: int
    game_name: str
    provider_id: int
    url: str
    existing_roi_set_id: int | None
    created_at: datetime
