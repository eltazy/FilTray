from __future__ import annotations

import json
import os
import plistlib
import sys
from pathlib import Path
from typing import Any

from .backends.base import ColorFilterBackend, FilterState

WINDOWS_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
WINDOWS_VALUE_NAME = "ColorFilterTray"
LINUX_DESKTOP_FILENAME = "filtray.desktop"
MACOS_LAUNCH_AGENT_LABEL = "org.opensource.filtray"
MACOS_PLIST_FILENAME = f"{MACOS_LAUNCH_AGENT_LABEL}.plist"


def get_launch_command() -> list[str]:
    """Return the argv list needed to launch FilTray on the current platform."""
    if getattr(sys, "frozen", False):
        return [sys.executable]

    script_path = os.path.abspath(sys.argv[0])
    if sys.platform == "win32":
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        exe = pythonw if os.path.exists(pythonw) else sys.executable
        return [exe, script_path]

    return [sys.executable, script_path]


def _format_windows_command(cmd: list[str]) -> str:
    return " ".join(f'"{part}"' for part in cmd)


def _format_desktop_exec(cmd: list[str]) -> str:
    formatted: list[str] = []
    for part in cmd:
        if any(ch.isspace() or ch in '"\\$`' for ch in part):
            escaped = part.replace("\\", "\\\\").replace('"', '\\"')
            formatted.append(f'"{escaped}"')
        else:
            formatted.append(part)
    return " ".join(formatted)


def _default_config_file(platform: str) -> Path:
    if platform == "win32":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else (Path.home() / ".config")
        return base / "ColorFilterTray" / "config.json"
    if platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "ColorFilterTray" / "config.json"
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg_config) if xdg_config else (Path.home() / ".config")
    return base / "color_filter_tray" / "config.json"


def _default_linux_autostart_dir() -> Path:
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg_config) if xdg_config else (Path.home() / ".config")
    return base / "autostart"


def _default_macos_launch_agents_dir() -> Path:
    return Path.home() / "Library" / "LaunchAgents"


class StartupManager:
    """
    Cross-platform launch-at-startup manager supporting:
      - Windows : HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
      - Linux   : XDG Autostart (~/.config/autostart/filtray.desktop)
      - macOS   : LaunchAgent (~/Library/LaunchAgents/org.opensource.filtray.plist)

    Persists user preference in config.json so startup is enabled automatically on
    first launch while respecting explicit opt-out from the system tray menu.
    """

    def __init__(
        self,
        platform: str | None = None,
        config_file: Path | None = None,
        autostart_dir: Path | None = None,
        system_autostart_file: Path | None = None,
        launch_agents_dir: Path | None = None,
        launch_command: list[str] | None = None,
    ) -> None:
        self.platform = platform or sys.platform
        self.config_file = config_file or _default_config_file(self.platform)
        self.autostart_dir = autostart_dir or _default_linux_autostart_dir()
        self.system_autostart_file = (
            system_autostart_file
            if system_autostart_file is not None
            else Path("/etc/xdg/autostart") / LINUX_DESKTOP_FILENAME
        )
        self.launch_agents_dir = launch_agents_dir or _default_macos_launch_agents_dir()
        self._launch_command = launch_command

    def _get_command(self) -> list[str]:
        if self._launch_command is not None:
            return list(self._launch_command)
        return get_launch_command()

    # ------------------------------------------------------------------
    # Config persistence
    # ------------------------------------------------------------------
    def _load_config(self) -> dict[str, Any]:
        try:
            if self.config_file.exists():
                data = json.loads(self.config_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
        return {}

    def _save_config(self, data: dict[str, Any]) -> None:
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            self.config_file.write_text(
                json.dumps(data, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def initialize_default_startup(self) -> bool:
        """
        Ensure launch-at-startup is enabled by default on first run.
        - If 'launch_at_startup' is not yet recorded in config.json, enable startup and save True.
        - If 'launch_at_startup' is True, refresh the OS entry (e.g., if a portable binary moved).
        - If 'launch_at_startup' is False, respect the user's opt-out and leave it disabled.
        Returns the resulting enabled state.
        """
        config = self._load_config()
        pref = config.get("launch_at_startup")

        if pref is None:
            ok = self._set_os_startup(True)
            config["launch_at_startup"] = True
            self._save_config(config)
            return ok

        if bool(pref):
            return self._set_os_startup(True)

        return False

    def is_enabled(self) -> bool:
        """Return True if OS-level launch-at-startup is currently enabled."""
        if self.platform == "win32":
            return self._is_windows_enabled()
        if self.platform == "darwin":
            return self._is_macos_enabled()
        if self.platform.startswith("linux"):
            return self._is_linux_enabled()
        return False

    def set_enabled(self, enabled: bool) -> bool:
        """Enable or disable OS-level launch-at-startup and persist the user's preference."""
        ok = self._set_os_startup(enabled)
        config = self._load_config()
        config["launch_at_startup"] = bool(enabled)
        self._save_config(config)
        return ok

    def _set_os_startup(self, enabled: bool) -> bool:
        if self.platform == "win32":
            return self._set_windows_startup(enabled)
        if self.platform == "darwin":
            return self._set_macos_startup(enabled)
        if self.platform.startswith("linux"):
            return self._set_linux_startup(enabled)
        return False

    # ------------------------------------------------------------------
    # Windows (HKCU\...\Run)
    # ------------------------------------------------------------------
    def _is_windows_enabled(self) -> bool:
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                WINDOWS_RUN_KEY,
                0,
                winreg.KEY_READ,
            ) as key:
                val, _ = winreg.QueryValueEx(key, WINDOWS_VALUE_NAME)
                return bool(val)
        except (ImportError, FileNotFoundError, OSError):
            return False

    def _set_windows_startup(self, enabled: bool) -> bool:
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                WINDOWS_RUN_KEY,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                if enabled:
                    cmd = _format_windows_command(self._get_command())
                    winreg.SetValueEx(key, WINDOWS_VALUE_NAME, 0, winreg.REG_SZ, cmd)
                else:
                    try:
                        winreg.DeleteValue(key, WINDOWS_VALUE_NAME)
                    except FileNotFoundError:
                        pass
            return True
        except (ImportError, OSError):
            return False

    # ------------------------------------------------------------------
    # Linux (XDG Autostart)
    # ------------------------------------------------------------------
    @property
    def _linux_user_desktop_file(self) -> Path:
        return self.autostart_dir / LINUX_DESKTOP_FILENAME

    def _parse_desktop_enabled(self, desktop_file: Path) -> bool:
        try:
            content = desktop_file.read_text(encoding="utf-8")
        except OSError:
            return False

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().lower()
            if key == "Hidden" and value == "true":
                return False
            if key == "X-GNOME-Autostart-enabled" and value == "false":
                return False
        return True

    def _is_linux_enabled(self) -> bool:
        if self._linux_user_desktop_file.exists():
            return self._parse_desktop_enabled(self._linux_user_desktop_file)
        if self.system_autostart_file.exists():
            return self._parse_desktop_enabled(self.system_autostart_file)
        return False

    def _set_linux_startup(self, enabled: bool) -> bool:
        user_file = self._linux_user_desktop_file
        try:
            if enabled:
                self.autostart_dir.mkdir(parents=True, exist_ok=True)
                exec_line = _format_desktop_exec(self._get_command())
                content = (
                    "[Desktop Entry]\n"
                    "Type=Application\n"
                    "Name=FilTray\n"
                    "GenericName=Color Filters Tray\n"
                    "Comment=Cross-platform system tray app for controlling screen Color Filters\n"
                    f"Exec={exec_line}\n"
                    "Terminal=false\n"
                    "Categories=Utility;Accessibility;\n"
                    "StartupNotify=false\n"
                    "X-GNOME-Autostart-enabled=true\n"
                )
                user_file.write_text(content, encoding="utf-8")
            else:
                if self.system_autostart_file.exists():
                    # Override system-wide /etc/xdg/autostart entry per XDG Autostart spec
                    self.autostart_dir.mkdir(parents=True, exist_ok=True)
                    content = (
                        "[Desktop Entry]\n"
                        "Type=Application\n"
                        "Name=FilTray\n"
                        "Hidden=true\n"
                        "X-GNOME-Autostart-enabled=false\n"
                    )
                    user_file.write_text(content, encoding="utf-8")
                elif user_file.exists():
                    user_file.unlink()
            return True
        except OSError:
            return False

    # ------------------------------------------------------------------
    # macOS (LaunchAgent)
    # ------------------------------------------------------------------
    @property
    def _macos_plist_file(self) -> Path:
        return self.launch_agents_dir / MACOS_PLIST_FILENAME

    def _is_macos_enabled(self) -> bool:
        return self._macos_plist_file.exists()

    def _set_macos_startup(self, enabled: bool) -> bool:
        plist_file = self._macos_plist_file
        try:
            if enabled:
                self.launch_agents_dir.mkdir(parents=True, exist_ok=True)
                payload = {
                    "Label": MACOS_LAUNCH_AGENT_LABEL,
                    "ProgramArguments": self._get_command(),
                    "RunAtLoad": True,
                    "KeepAlive": False,
                    "ProcessType": "Interactive",
                }
                plist_file.write_bytes(plistlib.dumps(payload, fmt=plistlib.FMT_XML))
            else:
                if plist_file.exists():
                    plist_file.unlink()
            return True
        except OSError:
            return False


def restore_saved_filter(backend: ColorFilterBackend) -> FilterState:
    """
    Read the persisted/OS color filter state and, if active, explicitly re-apply it
    to the OS so the last selected filter takes effect immediately on startup.
    """
    state = backend.get_state()
    if state.active:
        backend.set_state(True, state.filter_type)
    return state
