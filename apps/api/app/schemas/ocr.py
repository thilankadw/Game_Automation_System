"""OCR run and spin reading request/response schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

OcrRunStatus = Literal[
    "starting",
    "running",
    "completed",
    "failed",
    "cancelled",
]


class OcrRunCreate(BaseModel):
    """Payload for extracting values from a stored screenshot session."""

    session_id: str = Field(min_length=1, max_length=128)


class OcrRunRead(BaseModel):
    """Progress details for one OCR extraction run."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    game_id: int
    game_name: str
    session_id: str
    roi_set_id: int
    roi_set_name: str
    total_spins: int
    processed_spins: int
    recognized_spins: int
    status: OcrRunStatus
    error: str | None
    created_at: datetime
    finished_at: datetime | None


class OcrSpinReadingRead(BaseModel):
    """Balance, bet, and win values stored for one screenshot frame."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    game_id: int
    session_id: str
    spin_number: int
    balance: float | None
    bet: float | None
    win: float | None
    balance_text: str | None
    bet_text: str | None
    win_text: str | None
    screenshot_path: str
    created_at: datetime


class OcrSpinReadingPage(BaseModel):
    """A page of stored OCR spin readings."""

    items: list[OcrSpinReadingRead]
    total: int
    skip: int
    limit: int
