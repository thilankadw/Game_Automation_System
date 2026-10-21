"""FastAPI application and shared routes."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import engine, get_db
from app.routers import game_providers


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Release the database engine when the application shuts down."""
    yield
    await engine.dispose()


app = FastAPI(title="Game Automation System API", lifespan=lifespan)

DbSession = Annotated[AsyncSession, Depends(get_db)]

app.include_router(game_providers.router)


@app.get("/health")
async def health(db: DbSession) -> dict[str, str]:
    """Check that the API and database are reachable."""
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
