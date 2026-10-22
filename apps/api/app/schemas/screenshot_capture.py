"""Screenshot capture session request and response schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CaptureStatus = Literal[
    "starting",
    "running",
    "completed",
    "failed",
    "cancelled",
]


class ScreenshotCaptureSessionCreate(BaseModel):
    """Payload for starting an automated screenshot capture."""

    game_id: int = Field(gt=0)


class ScreenshotCaptureSessionRead(BaseModel):
    """Progress and output details for a screenshot capture session."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    game_id: int
    game_name: str
    url: str
    roi_set_id: int
    roi_set_name: str
    total_spins: int
    spin_wait_seconds: int
    completed_spins: int
    status: CaptureStatus
    error: str | None
    output_path: str
    latest_screenshot: str | None
    created_at: datetime
    finished_at: datetime | None


class StoredScreenshotSessionRead(BaseModel):
    """A capture folder persisted on disk with its screenshot URLs."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    screenshot_count: int
    width: int
    height: int
    screenshots: list[str]
