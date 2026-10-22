"""Screenshot image processing helpers.

Captured game regions are reduced to one-bit black-and-white PNGs to keep
stored screenshots small and to make the text easier to feed into OCR.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image

_DEFAULT_THRESHOLD = 127


def _otsu_threshold(histogram: list[int]) -> int:
    """Return the Otsu threshold for a 256-bin grayscale histogram.

    Otsu's method picks the threshold that maximizes the variance between the
    dark and light pixel groups, so it adapts to both light-on-dark and
    dark-on-light game themes.

    Args:
        histogram: 256 grayscale pixel counts.

    Returns:
        The grayscale value separating the two groups.
    """
    total = sum(histogram)
    if total == 0:
        return _DEFAULT_THRESHOLD

    weighted_sum = sum(value * count for value, count in enumerate(histogram))
    background_weight = 0
    background_sum = 0.0
    best_variance = -1.0
    best_threshold = _DEFAULT_THRESHOLD

    for value, count in enumerate(histogram):
        background_weight += count
        if background_weight == 0:
            continue

        foreground_weight = total - background_weight
        if foreground_weight == 0:
            break

        background_sum += value * count
        background_mean = background_sum / background_weight
        foreground_mean = (
            weighted_sum - background_sum
        ) / foreground_weight
        variance = (
            background_weight
            * foreground_weight
            * (background_mean - foreground_mean) ** 2
        )

        if variance > best_variance:
            best_variance = variance
            best_threshold = value

    return best_threshold


def save_black_and_white_png(path: Path, png_bytes: bytes) -> None:
    """Convert a PNG screenshot to a one-bit black-and-white PNG.

    The image is converted to grayscale, binarized with an Otsu threshold, and
    written with maximum PNG compression. No dithering is applied so text
    edges stay crisp and the file remains small.

    Args:
        path: Destination path for the processed PNG.
        png_bytes: Raw PNG bytes returned by the browser.
    """
    with Image.open(BytesIO(png_bytes)) as source:
        grayscale = source.convert("L")

    threshold = _otsu_threshold(grayscale.histogram())
    bilevel = grayscale.point(
        lambda value: 255 if value > threshold else 0,
        mode="1",
    )
    bilevel.save(path, format="PNG", optimize=True, compress_level=9)
