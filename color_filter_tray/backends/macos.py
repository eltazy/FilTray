from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .base import ColorFilterBackend, ColorFilterType, FilterState


# Map ColorFilterType to macOS DisplayFilterManager filterType values
MACOS_FILTER_MAP = {
    ColorFilterType.GRAYSCALE: 1,
    ColorFilterType.PROTANOPIA: 2,
    ColorFilterType.DEUTERANOPIA: 4,
    ColorFilterType.TRITANOPIA: 8,
    ColorFilterType.INVERTED: 1,
    ColorFilterType.GRAYSCALE_INVERTED: 1,
}


class MacOSColorFilterBackend(ColorFilterBackend):
    """
    macOS Color Filter Backend interacting with com.apple.universalaccess
    and local JSON state persistence in ~/Library/Application Support/ColorFilterTray.
    """

    def __init__(self) -> None:
        self._config_dir = (
            Path.home() / "Library" / "Application Support" / "ColorFilterTray"
        )
        self._state_file = self._config_dir / "state.json"
        self._state = self._load_persisted_state()

    @property
    def platform_name(self) -> str:
        return "macOS (Accessibility Display Filters)"

    def _load_persisted_state(self) -> FilterState:
        try:
            if self._state_file.exists():
                data = json.loads(self._state_file.read_text(encoding="utf-8"))
                active = bool(data.get("active", False))
                ft_val = int(data.get("filter_type", int(ColorFilterType.GRAYSCALE)))
                ft = (
                    ColorFilterType(ft_val)
                    if ft_val in ColorFilterType._value2member_map_
                    else ColorFilterType.GRAYSCALE
                )
                return FilterState(active=active, filter_type=ft)
        except Exception:
            pass
        return FilterState(active=False, filter_type=ColorFilterType.GRAYSCALE)

    def _save_persisted_state(self, state: FilterState) -> None:
        try:
            self._config_dir.mkdir(parents=True, exist_ok=True)
            self._state_file.write_text(
                json.dumps(
                    {
                        "active": state.active,
                        "filter_type": int(state.filter_type),
                        "filter_name": state.filter_type.name,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass

    def get_state(self) -> FilterState:
        return self._state

    def set_state(self, active: bool, filter_type: ColorFilterType) -> None:
        self._state = FilterState(active=active, filter_type=filter_type)
        self._save_persisted_state(self._state)

        try:
            mac_type = MACOS_FILTER_MAP.get(filter_type, 1)
            subprocess.run(
                [
                    "defaults",
                    "write",
                    "com.apple.universalaccess",
                    "__Color__-MADisplayFilterTypeEnabled",
                    "-bool",
                    "true" if active else "false",
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                [
                    "defaults",
                    "write",
                    "com.apple.universalaccess",
                    "__Color__-MADisplayFilterType",
                    "-int",
                    str(mac_type),
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass
