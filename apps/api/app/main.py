"""FastAPI application and shared routes."""

import asyncio
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import engine, get_db
from app.routers import game_providers, games, roi_capture, roi_sets
from app.services.roi_capture import manager as roi_capture_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Release the browser sessions and database engine on shutdown."""
    if sys.platform == "win32" and not isinstance(
        asyncio.get_running_loop(), asyncio.ProactorEventLoop
    ):
        # uvicorn's --reload factory picks a SelectorEventLoop on Windows,
        # which cannot spawn the Playwright driver used for ROI capture.
        logger.warning(
            "ROI capture needs a Proactor event loop on Windows. "
            "Restart uvicorn with --loop none."
        )
    yield
    await roi_capture_manager.shutdown()
    await engine.dispose()


app = FastAPI(title="Game Automation System API", lifespan=lifespan)

DbSession = Annotated[AsyncSession, Depends(get_db)]

app.include_router(game_providers.router)
app.include_router(games.router)
app.include_router(roi_sets.router)
app.include_router(roi_capture.router)


@app.get("/health")
async def health(db: DbSession) -> dict[str, str]:
    """Check that the API and database are reachable."""
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
