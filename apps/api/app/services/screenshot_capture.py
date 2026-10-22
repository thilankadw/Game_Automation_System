"""Automated game screenshot capture driven by Playwright.

A capture session opens the game in a headed Chrome window, clicks the spin
button ROI, waits for the game's configured spin delay, and saves one
full-window black-and-white screenshot per spin. The click/wait/capture cycle
repeats for the game's configured number of spins.
"""

from __future__ import annotations

import asyncio
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from urllib.parse import quote

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
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import SCREENSHOT_DIR
from app.models import Game, RoiSet
from app.services import game_providers as provider_service
from app.services import games as game_service
from app.services.browser import LAUNCH_ARGS, viewport_size
from app.services.image_processing import save_black_and_white_png

CaptureStatus = Literal["starting", "running", "completed", "failed", "cancelled"]

REQUIRED_ROI_NAMES = ("spin_button",)

_NAVIGATION_TIMEOUT_MS = 60_000
_INITIAL_SETTLE_MS = 3_000
_CLICK_SETTLE_MS = 250
_MAX_SESSIONS = 100
_MAX_SEGMENT_LENGTH = 60
_INVALID_SEGMENT_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_WINDOWS_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}

RoiRect = dict[str, int]


@dataclass
class ScreenshotCaptureSession:
    """A single automated screenshot run for a game."""

    id: str
    game_id: int
    game_name: str
    url: str
    roi_set_id: int
    roi_set_name: str
    total_spins: int
    spin_wait_seconds: int
    output_path: str
    status: CaptureStatus = "starting"
    completed_spins: int = 0
    error: str | None = None
    latest_screenshot: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    cancel_event: asyncio.Event = field(
        default_factory=asyncio.Event, repr=False
    )
    task: asyncio.Task[None] | None = field(default=None, repr=False)


class _CaptureCancelled(Exception):
    """Raised inside a capture run when the operator stops the session."""


def _resolve_rois(game: Game) -> tuple[RoiSet, dict[str, RoiRect]]:
    """Return the game's ROI set and the rectangles needed for capture.

    Args:
        game: Game with its provider ROI set eagerly loaded.

    Returns:
        The ROI set plus a mapping of ROI name to pixel rectangle.

    Raises:
        HTTPException: If the game has no assigned set or the set is missing the
            spin button region.
    """
    if game.roi_set is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Assign a ROI set to this game before capturing screenshots."
            ),
        )

    rois = {roi.name: roi for roi in game.roi_set.rois}
    missing = [name for name in REQUIRED_ROI_NAMES if name not in rois]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"ROI set '{game.roi_set.name}' is missing: "
                f"{', '.join(missing)}."
            ),
        )

    return game.roi_set, {
        name: {
            "x": rois[name].x,
            "y": rois[name].y,
            "width": rois[name].width,
            "height": rois[name].height,
        }
        for name in REQUIRED_ROI_NAMES
    }


def _safe_segment(name: str, fallback: str) -> str:
    """Return a readable folder name that is safe on the filesystem.

    Spaces and most characters are preserved. Characters Windows forbids in a
    path segment are replaced with underscores, trailing dots and spaces are
    stripped, and long names are truncated so the capture path stays within
    the Windows MAX_PATH limit. Reserved device names are prefixed with an
    underscore. The fallback is used when nothing usable remains.

    Args:
        name: Provider or game name to turn into a folder segment.
        fallback: ID-based name used when ``name`` has no usable characters.

    Returns:
        A filesystem-safe directory name.
    """
    segment = _INVALID_SEGMENT_CHARS.sub("_", name).strip().rstrip(" .")
    if segment.split(".", 1)[0].upper() in _RESERVED_WINDOWS_NAMES:
        segment = f"_{segment}"
    segment = segment[:_MAX_SEGMENT_LENGTH].rstrip(" .")
    return segment or fallback


class ScreenshotCaptureManager:
    """Owns the shared Playwright driver and screenshot capture sessions."""

    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._sessions: dict[str, ScreenshotCaptureSession] = {}
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
                    channel="chrome",
                    headless=False,
                    args=list(LAUNCH_ARGS),
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
    ) -> ScreenshotCaptureSession:
        """Start capturing screenshots for a game in the background.

        Args:
            db: Active database session used to load the game.
            game_id: Primary key of the game to capture.

        Returns:
            The session, which reports progress through its status fields.

        Raises:
            HTTPException: If the game does not exist, has no usable ROI set,
                or a capture is already running for the same game.
        """
        game = await game_service.get_game(db, game_id)
        provider = await provider_service.get_game_provider(
            db, game.game_provider_id
        )
        roi_set, rois = _resolve_rois(game)

        for existing in self._sessions.values():
            if (
                existing.game_id == game_id
                and existing.status in {"starting", "running"}
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "A screenshot capture is already running for this game."
                    ),
                )

        session_id = uuid.uuid4().hex
        folder_parts = (
            _safe_segment(provider.name, f"provider_{provider.id}"),
            _safe_segment(game.name, f"game_{game.id}"),
            session_id,
        )
        output_dir = SCREENSHOT_DIR.joinpath(*folder_parts)
        output_path = "/screenshots/" + "/".join(
            quote(part, safe="") for part in folder_parts
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        session = ScreenshotCaptureSession(
            id=session_id,
            game_id=game.id,
            game_name=game.name,
            url=game.url,
            roi_set_id=roi_set.id,
            roi_set_name=roi_set.name,
            total_spins=game.number_of_spins,
            spin_wait_seconds=game.spin_wait_seconds,
            output_path=output_path,
        )
        self._sessions[session.id] = session
        self._prune()

        if session.total_spins <= 0:
            session.status = "completed"
            session.finished_at = datetime.now(UTC)
            return session

        session.task = asyncio.create_task(
            self._run(session, rois, output_dir)
        )
        return session

    async def _run(
        self,
        session: ScreenshotCaptureSession,
        rois: dict[str, RoiRect],
        output_dir: Path,
    ) -> None:
        """Execute the click/wait/capture loop for one session."""
        session.status = "running"
        context: BrowserContext | None = None

        try:
            browser = await self._ensure_browser()
            width, height = viewport_size()
            context = await browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=1,
            )
            page = await context.new_page()
            await page.bring_to_front()
            await page.goto(
                session.url,
                wait_until="domcontentloaded",
                timeout=_NAVIGATION_TIMEOUT_MS,
            )
            await page.wait_for_timeout(_INITIAL_SETTLE_MS)
            await page.evaluate("window.scrollTo(0, 0)")

            await self._click_spin(page, rois["spin_button"], session)

            for spin in range(1, session.total_spins + 1):
                if not await self._wait_for_spin(session):
                    raise _CaptureCancelled

                await page.evaluate("window.scrollTo(0, 0)")
                filename = f"spin_{spin:04d}.png"
                png = await page.screenshot(type="png")
                await asyncio.to_thread(
                    save_black_and_white_png,
                    output_dir / filename,
                    png,
                )
                session.latest_screenshot = (
                    f"{session.output_path}/{filename}"
                )

                session.completed_spins = spin
                if spin < session.total_spins:
                    await self._click_spin(
                        page, rois["spin_button"], session
                    )

            session.status = "completed"
        except _CaptureCancelled:
            session.status = "cancelled"
        except asyncio.CancelledError:
            session.status = "cancelled"
            raise
        except PlaywrightTimeoutError as exc:
            session.status = "failed"
            session.error = f"Timed out while driving the game: {exc}"
        except PlaywrightError as exc:
            session.status = "failed"
            session.error = f"Browser error: {exc}"
        except HTTPException as exc:
            session.status = "failed"
            session.error = str(exc.detail)
        except Exception as exc:  # noqa: BLE001 - surfaced to the operator
            session.status = "failed"
            session.error = str(exc) or exc.__class__.__name__
        finally:
            session.finished_at = datetime.now(UTC)
            if context is not None:
                try:
                    await context.close()
                except PlaywrightError:
                    pass

    async def _wait_for_spin(
        self, session: ScreenshotCaptureSession
    ) -> bool:
        """Wait for the configured spin delay.

        Returns:
            ``True`` when the delay elapsed, or ``False`` when the operator
            cancelled the session.
        """
        if session.cancel_event.is_set():
            return False

        seconds = session.spin_wait_seconds
        if seconds <= 0:
            return True

        try:
            await asyncio.wait_for(
                session.cancel_event.wait(), timeout=seconds
            )
        except TimeoutError:
            return True
        return False

    async def _click_spin(
        self,
        page: Page,
        roi: RoiRect,
        session: ScreenshotCaptureSession,
    ) -> None:
        """Click the center of the spin button ROI."""
        if session.cancel_event.is_set():
            raise _CaptureCancelled

        await page.mouse.click(
            roi["x"] + roi["width"] / 2,
            roi["y"] + roi["height"] / 2,
        )
        await page.wait_for_timeout(_CLICK_SETTLE_MS)

    def _prune(self) -> None:
        """Drop the oldest finished sessions when the history grows large."""
        if len(self._sessions) <= _MAX_SESSIONS:
            return

        finished = sorted(
            (
                session
                for session in self._sessions.values()
                if session.status in {"completed", "failed", "cancelled"}
            ),
            key=lambda session: session.created_at,
        )
        for session in finished[: len(self._sessions) - _MAX_SESSIONS]:
            self._sessions.pop(session.id, None)

    def get_session(self, session_id: str) -> ScreenshotCaptureSession:
        """Return a session by ID.

        Raises:
            HTTPException: If the session ID is unknown.
        """
        session = self._sessions.get(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Screenshot capture session not found",
            )
        return session

    def list_sessions(self) -> list[ScreenshotCaptureSession]:
        """Return every session ordered by creation time."""
        self._prune()
        return sorted(self._sessions.values(), key=lambda item: item.created_at)

    async def stop_session(self, session_id: str) -> None:
        """Cancel a running session and wait for its browser context to close."""
        session = self._sessions.get(session_id)
        if session is None:
            return

        session.cancel_event.set()
        if session.status in {"starting", "running"}:
            session.status = "cancelled"
            session.finished_at = datetime.now(UTC)

        task = session.task
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def shutdown(self) -> None:
        """Cancel every session and stop the Playwright driver."""
        tasks = [
            session.task
            for session in self._sessions.values()
            if session.task is not None and not session.task.done()
        ]
        for session in self._sessions.values():
            session.cancel_event.set()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

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


manager = ScreenshotCaptureManager()
