"""Tests for screenshot image processing."""

from io import BytesIO
from pathlib import Path

from PIL import Image

from app.services.image_processing import (
    _otsu_threshold,
    save_black_and_white_png,
)


def _png_bytes(image: Image.Image) -> bytes:
    """Encode an image as PNG bytes."""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_otsu_threshold_separates_two_groups() -> None:
    """Otsu's method places the threshold between the dark and light peaks."""
    histogram = [0] * 256
    histogram[20] = 100
    histogram[220] = 100

    assert 20 <= _otsu_threshold(histogram) < 220


def test_save_black_and_white_png_produces_bilevel_image(
    tmp_path: Path,
) -> None:
    """A light region on a dark background becomes pure black and white."""
    image = Image.new("RGB", (40, 20), (20, 20, 30))
    image.paste((240, 230, 200), (10, 5, 30, 15))
    path = tmp_path / "capture.png"

    save_black_and_white_png(path, _png_bytes(image))

    with Image.open(path) as result:
        assert result.mode == "1"
        assert result.getpixel((0, 0)) == 0
        assert result.getpixel((20, 10)) == 255
