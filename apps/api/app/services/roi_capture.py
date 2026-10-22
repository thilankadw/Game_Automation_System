"""Live ROI capture driven by a headed Chrome browser.

The service opens the game URL in a real Chrome window through Playwright and
injects an overlay (``app/static/roi_overlay.js``) so an operator can keep
playing spins while drawing rectangles for the canvas, spin button, balance,
bet, and win regions. No screenshots are taken: the overlay reports the
rectangles back through an exposed binding and the service persists them into
an existing provider ROI set.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.schemas.roi import RoiCreate, RoiSetUpdate
from app.services import games as game_service
from app.services import roi_sets as roi_set_service
from app.services.browser import LAUNCH_ARGS, viewport_size

_OVERLAY_PATH = Path(__file__).resolve().parent.parent / "static" / "roi_overlay.js"
_OVERLAY_SCRIPT = _OVERLAY_PATH.read_text(encoding="utf-8")

_BINDING_NAME = "__roiCapture"
_NAVIGATION_TIMEOUT_MS = 45_000


@dataclass
class RoiCaptureSession:
    """A single live game window used to draw ROIs."""

    id: str
    game_id: int
    game_name: str
    provider_id: int
    url: str
    existing_roi_set_id: int | None
    context: BrowserContext
    page: Page
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    async def handle_binding(
        self, _source: Any, action: str, payload: Any
    ) -> dict[str, Any]:
        """Dispatch an overlay request to the matching handler.

        Args:
            _source: Playwright binding call metadata. Unused.
            action: Action name sent by the overlay.
            payload: Action-specific JSON payload.

        Returns:
            A JSON-serializable result for the overlay. Failures are reported
            as ``{"ok": False, "error": ...}`` instead of raising so the page
            can render a message.
        """
        payload = payload or {}
        if action == "listRoiSets":
            return await self._list_roi_sets()
        if action == "saveRois":
            return await self._save_rois(payload)
        if action == "close":
            asyncio.get_running_loop().create_task(manager.stop_session(self.id))
            return {"ok": True}
        return {"ok": False, "error": f"Unknown action: {action}"}

    async def _list_roi_sets(self) -> dict[str, Any]:
        """Return the provider's ROI sets for the overlay dropdown."""
        try:
            async with SessionLocal() as db:
                roi_sets = await roi_set_service.list_roi_sets(
                    db, self.provider_id
                )
        except HTTPException as exc:
            return {"ok": False, "error": exc.detail}
        return {
            "ok": True,
            "existingRoiSetId": self.existing_roi_set_id,
            "roiSets": [
                {
                    "id": roi_set.id,
                    "name": roi_set.name,
                    "rois": [roi.name for roi in roi_set.rois],
                }
                for roi_set in roi_sets
            ],
        }

    async def _save_rois(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Replace the ROIs of a provider set with the drawn rectangles."""
        try:
            roi_set_id = int(payload["roiSetId"])
        except (KeyError, TypeError, ValueError):
            return {"ok": False, "error": "Select an ROI set first"}

        try:
            rois = [
                RoiCreate(
                    name=roi["name"],
                    x=int(roi["x"]),
                    y=int(roi["y"]),
                    width=int(roi["width"]),
                    height=int(roi["height"]),
                )
                for roi in payload.get("rois", [])
            ]
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            return {"ok": False, "error": f"Invalid ROI payload: {exc}"}

        try:
            async with SessionLocal() as db:
                await roi_set_service.get_roi_set_for_provider(
                    db, self.provider_id, roi_set_id
                )
                roi_set = await roi_set_service.update_roi_set(
                    db, roi_set_id, RoiSetUpdate(rois=rois)
                )
        except HTTPException as exc:
            return {"ok": False, "error": exc.detail}
        return {
            "ok": True,
            "roiSet": {
                "id": roi_set.id,
                "name": roi_set.name,
                "rois": [
                    {
                        "name": roi.name,
                        "x": roi.x,
                        "y": roi.y,
                        "width": roi.width,
                        "height": roi.height,
                    }
                    for roi in roi_set.rois
                ],
            },
        }

    async def close(self) -> None:
        """Close the browser context for this session, ignoring errors."""
        try:
            await self.context.close()
        except PlaywrightError:
            pass


class RoiCaptureManager:
    """Owns the shared Playwright driver and the live capture sessions."""

    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._sessions: dict[str, RoiCaptureSession] = {}
        self._lock = asyncio.Lock()

    async def _ensure_playwright(self) -> Playwright:
        """Start the Playwright driver on first use."""
        async with self._lock:
            if self._playwright is None:
                try:
                    self._playwright = await async_playwright().start()
                except NotImplementedError as exc:
                    # uvicorn's --reload factory uses a SelectorEventLoop on
                    # Windows, which cannot spawn the Playwright driver.
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=(
                            "Playwright needs a Proactor event loop on Windows. "
                            "Restart uvicorn with --loop none, for example: "
                            "uv run uvicorn app.main:app --reload --loop none"
                        ),
                    ) from exc
            return self._playwright

    async def _ensure_browser(self) -> Browser:
        """Return the shared headed browser, launching Chrome if needed."""
        playwright = await self._ensure_playwright()
        async with self._lock:
            if self._browser is not None and self._browser.is_connected():
                return self._browser
            try:
                self._browser = await playwright.chromium.launch(
                    channel="chrome", headless=False, args=list(LAUNCH_ARGS)
                )
            except PlaywrightError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=(
                        "Could not launch Google Chrome. Install Chrome or run "
                        f"'playwright install chromium'. ({exc})"
                    ),
                ) from exc
            return self._browser

    async def start_session(
        self, db: AsyncSession, game_id: int
    ) -> RoiCaptureSession:
        """Open the game URL in Chrome with the drawing overlay injected.

        Args:
            db: Active database session used to load the game.
            game_id: Primary key of the game to capture.

        Returns:
            The created capture session.

        Raises:
            HTTPException: If the game does not exist, Chrome cannot launch,
                or the game URL cannot be opened at all.
        """
        game = await game_service.get_game(db, game_id)
        browser = await self._ensure_browser()

        viewport_width, viewport_height = viewport_size()
        context = await browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height},
            device_scale_factor=1,
        )
        page = await context.new_page()
        session = RoiCaptureSession(
            id=uuid.uuid4().hex,
            game_id=game.id,
            game_name=game.name,
            provider_id=game.game_provider_id,
            url=game.url,
            existing_roi_set_id=game.roi_set_id,
            context=context,
            page=page,
        )

        self._sessions[session.id] = session
        try:
            await page.expose_binding(_BINDING_NAME, session.handle_binding)
            await page.add_init_script(_OVERLAY_SCRIPT)
            try:
                await page.goto(
                    game.url,
                    wait_until="domcontentloaded",
                    timeout=_NAVIGATION_TIMEOUT_MS,
                )
            except PlaywrightTimeoutError:
                # The overlay is injected on DOMContentLoaded, so a slow game
                # still gets it; keep the session open for the operator.
                pass
            except PlaywrightError as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Could not open the game URL: {exc}",
                ) from exc
            await page.evaluate(_OVERLAY_SCRIPT)
            await page.bring_to_front()
        except HTTPException:
            await self.stop_session(session.id)
            raise
        except PlaywrightError as exc:
            await self.stop_session(session.id)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not inject the ROI overlay: {exc}",
            ) from exc

        return session

    def _prune_closed(self) -> None:
        """Drop sessions whose Chrome page was closed by the operator."""
        for session_id, session in list(self._sessions.items()):
            if session.page.is_closed():
                self._sessions.pop(session_id, None)

    def get_session(self, session_id: str) -> RoiCaptureSession:
        """Return a live session by ID.

        Raises:
            HTTPException: If the session ID is unknown or the window closed.
        """
        self._prune_closed()
        session = self._sessions.get(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ROI capture session not found",
            )
        return session

    def list_sessions(self) -> list[RoiCaptureSession]:
        """Return every live capture session ordered by creation time."""
        self._prune_closed()
        return sorted(self._sessions.values(), key=lambda item: item.created_at)

    async def stop_session(self, session_id: str) -> None:
        """Close and remove a capture session, ignoring unknown IDs."""
        session = self._sessions.pop(session_id, None)
        if session is not None:
            await session.close()

    async def shutdown(self) -> None:
        """Close every session and stop the Playwright driver."""
        for session in list(self._sessions.values()):
            await session.close()
        self._sessions.clear()
        if self._browser is not None:
            try:
                await self._browser.close()
            except PlaywrightError:
                pass
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None


manager = RoiCaptureManager()
