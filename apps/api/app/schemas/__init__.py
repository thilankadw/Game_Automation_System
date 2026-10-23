"""Pydantic request and response schemas."""

from app.schemas.game import GameBase, GameCreate, GamePage, GameRead, GameUpdate
from app.schemas.game_provider import (
    GameProviderBase,
    GameProviderCreate,
    GameProviderPage,
    GameProviderRead,
    GameProviderUpdate,
)
from app.schemas.ocr import (
    OcrRunCreate,
    OcrRunRead,
    OcrSpinReadingPage,
    OcrSpinReadingRead,
)
from app.schemas.roi import (
    RoiBase,
    RoiCreate,
    RoiRead,
    RoiSetCreate,
    RoiSetRead,
    RoiSetUpdate,
)
from app.schemas.roi_capture import (
    RoiCaptureSessionCreate,
    RoiCaptureSessionRead,
)
from app.schemas.screenshot_capture import (
    ScreenshotCaptureSessionCreate,
    ScreenshotCaptureSessionRead,
    StoredScreenshotSessionRead,
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
    "OcrRunCreate",
    "OcrRunRead",
    "OcrSpinReadingPage",
    "OcrSpinReadingRead",
    "RoiBase",
    "RoiCaptureSessionCreate",
    "RoiCaptureSessionRead",
    "RoiCreate",
    "RoiRead",
    "RoiSetCreate",
    "RoiSetRead",
    "RoiSetUpdate",
    "ScreenshotCaptureSessionCreate",
    "ScreenshotCaptureSessionRead",
    "StoredScreenshotSessionRead",
]
