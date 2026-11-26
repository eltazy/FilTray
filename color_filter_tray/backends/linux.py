from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from .base import ColorFilterBackend, ColorFilterType, FilterState


class LinuxColorFilterBackend(ColorFilterBackend):
    """
    Linux Color Filter Backend supporting GNOME / KDE / X11 with local state persistence.
    When running in a headless or unsupported desktop environment, persists state cleanly
    to ~/.config/color_filter_tray/state.json so the UI and tray icon remain fully functional.
    """

    def __init__(self) -> None:
        self._config_dir = Path(
            os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
        ) / "color_filter_tray"
        self._state_file = self._config_dir / "state.json"
        self._state = self._load_persisted_state()

    @property
    def platform_name(self) -> str:
        if shutil.which("gsettings"):
            return "Linux (GNOME / X11 + Config)"
        return "Linux (Config Persistence)"

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

        # Optional GNOME magnifier color filter integration if available on desktop
        if shutil.which("gsettings") and os.environ.get("DISPLAY"):
            try:
                # Map to GNOME magnifier color-saturation / invert-lightness when active
                if not active:
                    subprocess.run(
                        [
                            "gsettings",
                            "set",
                            "org.gnome.desktop.a11y.magnifier",
                            "invert-lightness",
                            "false",
                        ],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    subprocess.run(
                        [
                            "gsettings",
                            "set",
                            "org.gnome.desktop.a11y.magnifier",
                            "color-saturation",
                            "1.0",
                        ],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    invert = filter_type in (
                        ColorFilterType.INVERTED,
                        ColorFilterType.GRAYSCALE_INVERTED,
                    )
                    grayscale = filter_type in (
                        ColorFilterType.GRAYSCALE,
                        ColorFilterType.GRAYSCALE_INVERTED,
                    )
                    subprocess.run(
                        [
                            "gsettings",
                            "set",
                            "org.gnome.desktop.a11y.magnifier",
                            "invert-lightness",
                            "true" if invert else "false",
                        ],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    subprocess.run(
                        [
                            "gsettings",
                            "set",
                            "org.gnome.desktop.a11y.magnifier",
                            "color-saturation",
                            "0.0" if grayscale else "1.0",
                        ],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
            except Exception:
                pass
