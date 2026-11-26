from __future__ import annotations

import sys

from .base import ColorFilterBackend, ColorFilterType, FilterOption, FilterState, UI_FILTER_OPTIONS
from .linux import LinuxColorFilterBackend
from .macos import MacOSColorFilterBackend
from .windows import WindowsColorFilterBackend


def get_backend() -> ColorFilterBackend:
    """Return the appropriate OS-specific ColorFilterBackend."""
    if sys.platform == "win32":
        return WindowsColorFilterBackend()
    if sys.platform == "darwin":
        return MacOSColorFilterBackend()
    return LinuxColorFilterBackend()


__all__ = [
    "ColorFilterBackend",
    "ColorFilterType",
    "FilterOption",
    "FilterState",
    "UI_FILTER_OPTIONS",
    "WindowsColorFilterBackend",
    "LinuxColorFilterBackend",
    "MacOSColorFilterBackend",
    "get_backend",
]
