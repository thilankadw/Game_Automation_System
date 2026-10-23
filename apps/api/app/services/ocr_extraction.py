"""OCR extraction of balance, bet, and win values from stored screenshots.

The screenshot capture service saves one black-and-white frame per spin. This
service reads the game's balance, bet, and win ROIs from a selected stored
session, parses the amounts, and persists one reading per frame. Runs execute
in the background so the API can report progress for large screenshot sets.
"""

from __future__ import annotations

import asyncio
import re
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

from fastapi import HTTPException, status
from PIL import Image, ImageOps
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models import Game, RoiSet, SpinReading
from app.services import games as game_service
from app.services import screenshot_capture

OcrRunStatus = Literal[
    "starting",
    "running",
    "completed",
    "failed",
    "cancelled",
]

REQUIRED_ROI_NAMES = ("balance", "bet", "win")

_MAX_RUNS = 100
_COMMIT_EVERY = 25
_OCR_SCALE = 2
_DARK_THRESHOLD = 160
_CONTRAST_THRESHOLD = 120
_CLUSTER_GAP = 20
_NUMBER_PATTERN = re.compile(r"-?\d[\d\s'.,]*")
_SPIN_FILE_PATTERN = re.compile(r"spin_(\d+)\.png$")
_ENGINE_CALL_LOCK = threading.Lock()
_ENGINE_LOCK = threading.Lock()
_engine: Any | None = None

RoiRect = dict[str, int]


@dataclass
class OcrRun:
    """A single OCR extraction run over a stored screenshot session."""

    id: str
    game_id: int
    game_name: str
    session_id: str
    roi_set_id: int
    roi_set_name: str
    total_spins: int
    status: OcrRunStatus = "starting"
    processed_spins: int = 0
    recognized_spins: int = 0
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    cancel_event: asyncio.Event = field(
        default_factory=asyncio.Event, repr=False
    )
    task: asyncio.Task[None] | None = field(default=None, repr=False)


class _OcrCancelled(Exception):
    """Raised inside an OCR run when the operator stops it."""


def _get_engine() -> Any:
    """Return the lazily created RapidOCR engine.

    The engine is shared and guarded by a lock because the ONNX sessions use
    native resources that are not safe for concurrent inference.
    """
    global _engine
    if _engine is None:
        with _ENGINE_LOCK:
            if _engine is None:
                try:
                    from rapidocr_onnxruntime import RapidOCR
                except ImportError as exc:
                    raise RuntimeError(
                        "RapidOCR is not installed. Run 'uv sync' to install "
                        "the OCR dependencies."
                    ) from exc
                _engine = RapidOCR()
    return _engine


def _parse_amount(text: str | None) -> Decimal | None:
    """Parse the first numeric value from OCR text.

    Game screens use both ``1,234.56`` and ``1.234,56`` conventions, so the
    final separator with one or two trailing digits is treated as the decimal
    mark. Groups of exactly three digits are treated as thousands separators.
    Non-numeric status text such as "Press Spin to Win" returns ``None``.
    """
    if not text:
        return None

    match = _NUMBER_PATTERN.search(text)
    if match is None:
        return None

    candidate = re.sub(r"[\s']", "", match.group(0).strip().strip(".,"))
    if not candidate or candidate == "-":
        return None

    if candidate.count("-") > 1 or "-" in candidate[1:]:
        return None

    has_comma = "," in candidate
    has_dot = "." in candidate

    if has_comma and has_dot:
        decimal_sep = (
            "," if candidate.rfind(",") > candidate.rfind(".") else "."
        )
        thousands_sep = "." if decimal_sep == "," else ","
        candidate = candidate.replace(thousands_sep, "").replace(
            decimal_sep, "."
        )
    elif has_comma:
        parts = candidate.split(",")
        if len(parts) == 2 and 1 <= len(parts[1]) <= 2:
            candidate = f"{parts[0]}.{parts[1]}"
        else:
            candidate = "".join(parts)
    elif has_dot:
        parts = candidate.split(".")
        if len(parts) > 2:
            candidate = "".join(parts)
        elif len(parts) == 2 and len(parts[1]) == 3:
            candidate = f"{parts[0]}{parts[1]}"

    try:
        amount = Decimal(candidate)
    except InvalidOperation:
        return None

    if not amount.is_finite() or amount.adjusted() > 15:
        return None

    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _clean_text(text: str) -> str | None:
    """Trim OCR text and keep it within the database column length."""
    cleaned = " ".join(text.split())
    return cleaned[:255] or None


def _histogram_median(image: Image.Image) -> int:
    """Return the median luma value from an image histogram."""
    histogram = image.histogram()
    target = image.width * image.height / 2
    running = 0
    for value, count in enumerate(histogram):
        running += count
        if running >= target:
            return value
    return 255


def _dark_text_crop(crop: Image.Image) -> Image.Image:
    """Normalize a crop so its text is dark on a light background."""
    gray = crop.convert("L")
    width, height = gray.size
    inset_x = max(1, width // 4)
    inset_y = max(1, height // 4)
    center = gray.crop(
        (
            inset_x,
            inset_y,
            max(inset_x + 1, width - inset_x),
            max(inset_y + 1, height - inset_y),
        )
    )
    if _histogram_median(center) < 128:
        return ImageOps.invert(gray)
    return gray


def _widest_text_cluster(
    image: Image.Image, top: int, bottom: int
) -> tuple[int, int] | None:
    """Return the widest dark-text cluster inside a horizontal band."""
    width, _ = image.size
    left = 2 if width > 4 else 0
    right = width - 2 if width > 4 else width
    pixels = image.load()

    runs: list[tuple[int, int]] = []
    start: int | None = None
    for x in range(left, right):
        has_ink = any(
            pixels[x, y] < _DARK_THRESHOLD for y in range(top, bottom)
        )
        if has_ink and start is None:
            start = x
        elif not has_ink and start is not None:
            runs.append((start, x))
            start = None
    if start is not None:
        runs.append((start, right))
    if not runs:
        return None

    clusters: list[list[int]] = []
    for start_x, end_x in runs:
        if not clusters or start_x - clusters[-1][1] >= _CLUSTER_GAP:
            clusters.append([start_x, end_x])
        else:
            clusters[-1][1] = end_x

    cluster_start, cluster_end = max(
        clusters, key=lambda cluster: cluster[1] - cluster[0]
    )
    return cluster_start, cluster_end


def _crop_amount_region(crop: Image.Image) -> Image.Image:
    """Trim an amount ROI to its numeric text before recognition."""
    gray = _dark_text_crop(crop)
    width, height = gray.size
    left = 2 if width > 4 else 0
    right = width - 2 if width > 4 else width
    pixels = gray.load()

    scan_top = max(1, int(height * 0.2))
    scan_bottom = min(height - 1, int(height * 0.8))
    rows = [
        y
        for y in range(scan_top, scan_bottom)
        if sum(
            1 for x in range(left, right) if pixels[x, y] < _DARK_THRESHOLD
        )
        >= 3
    ]
    if not rows:
        return gray

    top = min(rows)
    bottom = max(rows) + 1
    cluster = _widest_text_cluster(gray, top, bottom)
    if cluster is None:
        return gray.crop((left, top, right, bottom))

    cluster_start, cluster_end = cluster
    return gray.crop(
        (max(0, cluster_start - 2), top, min(width, cluster_end + 2), bottom)
    )


def _crop_win_text(crop: Image.Image) -> Image.Image:
    """Trim a win ROI to its longest high-contrast text band."""
    gray = crop.convert("L")
    width, height = gray.size
    rows: list[int] = []
    for y in range(height):
        row = gray.crop((0, y, width, y + 1))
        histogram = row.histogram()
        low, high = row.getextrema()
        if (
            high - low >= _CONTRAST_THRESHOLD
            and sum(histogram[:80]) >= 3
            and sum(histogram[176:]) >= 3
        ):
            rows.append(y)

    groups: list[list[int]] = []
    for y in rows:
        if not groups or y - groups[-1][-1] > 2:
            groups.append([y])
        else:
            groups[-1].append(y)
    if not groups:
        return gray

    band_rows = max(groups, key=len)
    top = max(0, band_rows[0] - 1)
    bottom = min(height, band_rows[-1] + 2)
    band = gray.crop((0, top, width, bottom))
    if _histogram_median(band) < 128:
        band = ImageOps.invert(band)

    cluster = _widest_text_cluster(band, 0, band.height)
    if cluster is None:
        return band

    cluster_start, cluster_end = cluster
    return band.crop(
        (
            max(0, cluster_start - 2),
            0,
            min(width, cluster_end + 2),
            band.height,
        )
    )


def _recognize_crop(
    engine: Any, crop: Image.Image, scale: int = _OCR_SCALE
) -> str:
    """Run recognition-only OCR on one cropped ROI."""
    if scale > 1:
        crop = crop.resize(
            (crop.width * scale, crop.height * scale),
            Image.Resampling.LANCZOS,
        )

    result, _ = engine(crop.convert("RGB"), use_det=False, use_cls=False, use_rec=True)
    parts: list[str] = []
    if result:
        for entry in result:
            # Detection runs return [box, text, score], while recognition-only
            # runs return [text, score].
            text = next(
                (value for value in entry[:2] if isinstance(value, str)),
                "",
            ).strip()
            if text:
                parts.append(text)
    return " ".join(parts)


def _extract_text_values(
    screenshot_path: Path, rois: dict[str, RoiRect]
) -> dict[str, str]:
    """Read the configured ROI text from one screenshot frame.

    Recognition-only inference is much faster than running the text detector
    on every small crop. Amount ROIs are trimmed to the text band first so the
    surrounding panel border and icon do not bias the recognizer. Win ROIs may
    contain either a numeric amount or a status message, so both layouts are
    attempted.
    """
    engine = _get_engine()
    with Image.open(screenshot_path) as source:
        image = source.convert("RGB")

    texts: dict[str, str] = {}
    with _ENGINE_CALL_LOCK:
        for name in REQUIRED_ROI_NAMES:
            roi = rois[name]
            crop = image.crop(
                (
                    roi["x"],
                    roi["y"],
                    roi["x"] + roi["width"],
                    roi["y"] + roi["height"],
                )
            )
            if name == "win":
                text = _recognize_crop(engine, crop)
                if _parse_amount(text) is None:
                    text = _recognize_crop(engine, _crop_win_text(crop))
            else:
                text = _recognize_crop(engine, _crop_amount_region(crop))
                if _parse_amount(text) is None:
                    fallback = _recognize_crop(engine, crop)
                    if fallback:
                        text = fallback
            texts[name] = text

    return texts


async def _extract_text_values_async(
    screenshot_path: Path, rois: dict[str, RoiRect]
) -> dict[str, str]:
    """Run OCR inference outside the event loop."""
    return await asyncio.to_thread(_extract_text_values, screenshot_path, rois)


def _resolve_rois(game: Game) -> tuple[RoiSet, dict[str, RoiRect]]:
    """Return the ROI rectangles needed to read balance, bet, and win."""
    if game.roi_set is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Assign a ROI set to this game before running OCR.",
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


def _find_session_frames(
    folder_parts: tuple[str, str], session_id: str
) -> list[Path]:
    """Return the screenshot frames inside one validated stored session."""
    if not screenshot_capture._valid_session_name(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot session not found",
        )

    base_dir = screenshot_capture.SCREENSHOT_DIR.joinpath(*folder_parts)
    session_dir = base_dir / session_id
    try:
        resolved_base = base_dir.resolve()
        resolved_session = session_dir.resolve()
    except (OSError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot session not found",
        ) from exc

    if (
        resolved_session.parent != resolved_base
        or not resolved_session.is_dir()
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot session not found",
        )

    files = sorted(
        path for path in resolved_session.glob("spin_*.png") if path.is_file()
    )
    if not files:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Screenshot session has no frames to read.",
        )
    return files


def _spin_number(path: Path, fallback: int) -> int:
    """Read the spin number from a screenshot filename."""
    match = _SPIN_FILE_PATTERN.match(path.name)
    if match is None:
        return fallback
    return int(match.group(1))


def _screenshot_url(
    folder_parts: tuple[str, str], session_id: str, filename: str
) -> str:
    """Build the public URL for a stored screenshot frame."""
    return "/screenshots/" + "/".join(
        quote(part, safe="")
        for part in (*folder_parts, session_id, filename)
    )


def _reading_values(
    texts: dict[str, str],
) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    """Parse the three OCR texts into amounts."""
    return (
        _parse_amount(texts.get("balance")),
        _parse_amount(texts.get("bet")),
        _parse_amount(texts.get("win")),
    )


class OcrRunManager:
    """Own the OCR runs and their background tasks."""

    def __init__(self) -> None:
        self._runs: dict[str, OcrRun] = {}
        self._lock = asyncio.Lock()

    async def start_run(
        self, db: AsyncSession, game_id: int, session_id: str
    ) -> OcrRun:
        """Start reading a stored session for one game in the background."""
        game = await game_service.get_game(db, game_id)
        roi_set, rois = _resolve_rois(game)

        if session_id in screenshot_capture.manager.active_session_ids():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Stop the running capture before reading its screenshots."
                ),
            )

        for existing in self._runs.values():
            if (
                existing.game_id == game_id
                and existing.session_id == session_id
                and existing.status in {"starting", "running"}
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "OCR is already running for this screenshot session."
                    ),
                )

        folder_parts = await screenshot_capture._load_game_folder_parts(
            db, game_id
        )
        files = await asyncio.to_thread(
            _find_session_frames, folder_parts, session_id
        )

        run = OcrRun(
            id=uuid.uuid4().hex,
            game_id=game.id,
            game_name=game.name,
            session_id=session_id,
            roi_set_id=roi_set.id,
            roi_set_name=roi_set.name,
            total_spins=len(files),
        )
        self._runs[run.id] = run
        self._prune()
        run.task = asyncio.create_task(
            self._run(run, rois, files, folder_parts)
        )
        return run

    async def _run(
        self,
        run: OcrRun,
        rois: dict[str, RoiRect],
        files: list[Path],
        folder_parts: tuple[str, str],
    ) -> None:
        """Read every frame and store one reading per screenshot."""
        run.status = "running"

        try:
            async with SessionLocal() as db:
                await db.execute(
                    delete(SpinReading).where(
                        SpinReading.game_id == run.game_id,
                        SpinReading.session_id == run.session_id,
                    )
                )
                await db.commit()

                try:
                    for index, path in enumerate(files, start=1):
                        if run.cancel_event.is_set():
                            raise _OcrCancelled

                        texts = await _extract_text_values_async(path, rois)
                        if run.cancel_event.is_set():
                            raise _OcrCancelled

                        balance, bet, win = _reading_values(texts)
                        spin_number = _spin_number(path, index)
                        db.add(
                            SpinReading(
                                game_id=run.game_id,
                                session_id=run.session_id,
                                spin_number=spin_number,
                                balance=balance,
                                bet=bet,
                                win=win,
                                balance_text=_clean_text(
                                    texts.get("balance", "")
                                ),
                                bet_text=_clean_text(texts.get("bet", "")),
                                win_text=_clean_text(texts.get("win", "")),
                                screenshot_path=_screenshot_url(
                                    folder_parts,
                                    run.session_id,
                                    path.name,
                                ),
                            )
                        )

                        run.processed_spins = index
                        if any(
                            value is not None
                            for value in (balance, bet, win)
                        ):
                            run.recognized_spins += 1

                        if index % _COMMIT_EVERY == 0:
                            await db.commit()

                    await db.commit()
                except _OcrCancelled:
                    await db.commit()
                    raise

            run.status = "completed"
        except _OcrCancelled:
            run.status = "cancelled"
        except Exception as exc:  # noqa: BLE001 - surfaced to the operator
            run.status = "failed"
            run.error = str(exc) or exc.__class__.__name__
        finally:
            run.finished_at = datetime.now(UTC)

    def _prune(self) -> None:
        """Drop the oldest finished runs when the history grows large."""
        if len(self._runs) <= _MAX_RUNS:
            return

        finished = sorted(
            (
                run
                for run in self._runs.values()
                if run.status in {"completed", "failed", "cancelled"}
            ),
            key=lambda run: run.created_at,
        )
        for run in finished[: len(self._runs) - _MAX_RUNS]:
            self._runs.pop(run.id, None)

    def get_run(self, game_id: int, run_id: str) -> OcrRun:
        """Return one run for a game or raise 404."""
        run = self._runs.get(run_id)
        if run is None or run.game_id != game_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OCR run not found",
            )
        return run

    def active_run(
        self, game_id: int, session_id: str | None = None
    ) -> OcrRun | None:
        """Return an in-flight run for a game or session, if one exists."""
        for run in self._runs.values():
            if run.game_id != game_id or run.status not in {
                "starting",
                "running",
            }:
                continue
            if session_id is None or run.session_id == session_id:
                return run
        return None

    def list_runs(self, game_id: int) -> list[OcrRun]:
        """Return a game's OCR runs ordered by creation time."""
        self._prune()
        return sorted(
            (
                run
                for run in self._runs.values()
                if run.game_id == game_id
            ),
            key=lambda run: run.created_at,
        )

    async def stop_run(self, game_id: int, run_id: str) -> None:
        """Ask a run to stop and wait for its background task."""
        run = self.get_run(game_id, run_id)
        run.cancel_event.set()
        task = run.task
        if task is not None and not task.done():
            await task

    async def shutdown(self) -> None:
        """Stop every in-flight OCR task."""
        tasks = [
            run.task
            for run in self._runs.values()
            if run.task is not None and not run.task.done()
        ]
        for run in self._runs.values():
            run.cancel_event.set()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._runs.clear()


manager = OcrRunManager()


async def list_readings(
    db: AsyncSession,
    game_id: int,
    *,
    session_id: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[SpinReading], int]:
    """Return a page of stored readings for a game, newest spin first."""
    await game_service.get_game(db, game_id)

    filters = [SpinReading.game_id == game_id]
    if session_id:
        filters.append(SpinReading.session_id == session_id)

    total = (
        await db.scalar(
            select(func.count()).select_from(SpinReading).where(*filters)
        )
        or 0
    )
    stmt = (
        select(SpinReading)
        .where(*filters)
        .order_by(SpinReading.spin_number.desc(), SpinReading.id.desc())
        .offset(skip)
        .limit(limit)
    )
    readings = list(await db.scalars(stmt))
    return readings, total


async def delete_readings(
    db: AsyncSession, game_id: int, *, session_id: str | None = None
) -> None:
    """Delete stored OCR readings for a game, optionally one session.

    Args:
        db: Active database session.
        game_id: Primary key of the game.
        session_id: Optional stored screenshot session to clear. When omitted,
            every reading for the game is deleted.

    Raises:
        HTTPException: If the game does not exist or an OCR run is still
            writing readings for the affected scope.
    """
    await game_service.get_game(db, game_id)

    if manager.active_run(game_id, session_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stop the OCR run before deleting its readings.",
        )

    filters = [SpinReading.game_id == game_id]
    if session_id is not None:
        filters.append(SpinReading.session_id == session_id)

    await db.execute(delete(SpinReading).where(*filters))
    await db.commit()
