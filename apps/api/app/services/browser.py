"""Playwright browser configuration shared by the capture services."""

from __future__ import annotations

import ctypes
import sys

VIEWPORT_RATIO = 0.75
FALLBACK_VIEWPORT = (1024, 768)
LAUNCH_ARGS = ("--disable-dev-shm-usage", "--no-first-run")


def viewport_size() -> tuple[int, int]:
    """Return three quarters of the primary display in CSS pixels.

    On Windows, ``GetSystemMetrics`` reports the display in the same virtual
    (CSS) pixels Chrome uses because Python runs DPI-unaware by default.
    """
    if sys.platform == "win32":
        try:
            user32 = ctypes.windll.user32
            width = int(user32.GetSystemMetrics(0))
            height = int(user32.GetSystemMetrics(1))
        except (AttributeError, OSError):
            width = height = 0
        if width > 0 and height > 0:
            return (
                max(1, round(width * VIEWPORT_RATIO)),
                max(1, round(height * VIEWPORT_RATIO)),
            )
    return FALLBACK_VIEWPORT
