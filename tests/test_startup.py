from __future__ import annotations

import json
import plistlib
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from color_filter_tray.backends.base import ColorFilterType, FilterState
from color_filter_tray.startup import (
    MACOS_LAUNCH_AGENT_LABEL,
    WINDOWS_RUN_KEY,
    WINDOWS_VALUE_NAME,
    StartupManager,
    restore_saved_filter,
)

LAUNCH_CMD = ["/opt/FilTray App/filtray"]


class _TempDirTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.config_file = self.root / "config" / "config.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def read_config(self) -> dict:
        return json.loads(self.config_file.read_text(encoding="utf-8"))


class TestLinuxStartup(_TempDirTestCase):
    def make_manager(self, system_file: Path | None = None) -> StartupManager:
        return StartupManager(
            platform="linux",
            config_file=self.config_file,
            autostart_dir=self.root / "autostart",
            system_autostart_file=system_file or (self.root / "etc" / "filtray.desktop"),
            launch_command=LAUNCH_CMD,
        )

    def test_first_run_enables_startup_by_default(self) -> None:
        mgr = self.make_manager()
        self.assertTrue(mgr.initialize_default_startup())
        self.assertTrue(mgr.is_enabled())
        self.assertTrue(self.read_config()["launch_at_startup"])

        content = (self.root / "autostart" / "filtray.desktop").read_text(encoding="utf-8")
        self.assertIn('Exec="/opt/FilTray App/filtray"', content)
        self.assertIn("X-GNOME-Autostart-enabled=true", content)

    def test_opt_out_is_respected_on_next_launch(self) -> None:
        mgr = self.make_manager()
        mgr.initialize_default_startup()
        mgr.set_enabled(False)

        self.assertFalse(mgr.is_enabled())
        self.assertFalse((self.root / "autostart" / "filtray.desktop").exists())
        self.assertFalse(self.read_config()["launch_at_startup"])

        # Simulate a subsequent app launch
        self.assertFalse(self.make_manager().initialize_default_startup())
        self.assertFalse(mgr.is_enabled())

    def test_disable_overrides_system_wide_autostart(self) -> None:
        system_file = self.root / "etc" / "filtray.desktop"
        system_file.parent.mkdir(parents=True)
        system_file.write_text("[Desktop Entry]\nType=Application\nExec=/usr/bin/filtray\n", encoding="utf-8")

        mgr = self.make_manager(system_file)
        self.assertTrue(mgr.is_enabled())  # .deb system entry counts as enabled

        mgr.set_enabled(False)
        user_file = self.root / "autostart" / "filtray.desktop"
        self.assertIn("Hidden=true", user_file.read_text(encoding="utf-8"))
        self.assertFalse(mgr.is_enabled())

        mgr.set_enabled(True)
        self.assertTrue(mgr.is_enabled())
        self.assertNotIn("Hidden=true", user_file.read_text(encoding="utf-8"))


class TestMacOSStartup(_TempDirTestCase):
    def make_manager(self) -> StartupManager:
        return StartupManager(
            platform="darwin",
            config_file=self.config_file,
            launch_agents_dir=self.root / "LaunchAgents",
            launch_command=LAUNCH_CMD,
        )

    def test_launch_agent_created_and_removed(self) -> None:
        mgr = self.make_manager()
        self.assertTrue(mgr.initialize_default_startup())

        plist_file = self.root / "LaunchAgents" / f"{MACOS_LAUNCH_AGENT_LABEL}.plist"
        data = plistlib.loads(plist_file.read_bytes())
        self.assertEqual(data["Label"], MACOS_LAUNCH_AGENT_LABEL)
        self.assertEqual(data["ProgramArguments"], LAUNCH_CMD)
        self.assertTrue(data["RunAtLoad"])
        self.assertTrue(mgr.is_enabled())

        mgr.set_enabled(False)
        self.assertFalse(plist_file.exists())
        self.assertFalse(mgr.is_enabled())
        self.assertFalse(self.read_config()["launch_at_startup"])


class _FakeKey:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _make_fake_winreg(store: dict) -> SimpleNamespace:
    def open_key(hive, path, reserved, access):
        assert path == WINDOWS_RUN_KEY
        return _FakeKey()

    def query_value_ex(key, name):
        if name not in store:
            raise FileNotFoundError(name)
        return store[name], 1

    def set_value_ex(key, name, reserved, typ, value):
        store[name] = value

    def delete_value(key, name):
        if name not in store:
            raise FileNotFoundError(name)
        del store[name]

    return SimpleNamespace(
        HKEY_CURRENT_USER=object(),
        KEY_READ=1,
        KEY_SET_VALUE=2,
        REG_SZ=1,
        OpenKey=open_key,
        QueryValueEx=query_value_ex,
        SetValueEx=set_value_ex,
        DeleteValue=delete_value,
    )


class TestWindowsStartup(_TempDirTestCase):
    def test_registry_run_entry_lifecycle(self) -> None:
        store: dict = {}
        with patch.dict(sys.modules, {"winreg": _make_fake_winreg(store)}):
            mgr = StartupManager(
                platform="win32",
                config_file=self.config_file,
                launch_command=[r"C:\Apps\FilTray.exe"],
            )
            self.assertTrue(mgr.initialize_default_startup())
            self.assertEqual(store[WINDOWS_VALUE_NAME], r'"C:\Apps\FilTray.exe"')
            self.assertTrue(mgr.is_enabled())

            # Portable .exe moved: next launch refreshes the registry path
            moved = StartupManager(
                platform="win32",
                config_file=self.config_file,
                launch_command=[r"D:\Tools\FilTray.exe"],
            )
            moved.initialize_default_startup()
            self.assertEqual(store[WINDOWS_VALUE_NAME], r'"D:\Tools\FilTray.exe"')

            moved.set_enabled(False)
            self.assertNotIn(WINDOWS_VALUE_NAME, store)
            self.assertFalse(moved.is_enabled())
            self.assertFalse(moved.initialize_default_startup())
            self.assertNotIn(WINDOWS_VALUE_NAME, store)


class TestRestoreSavedFilter(unittest.TestCase):
    def test_reapplies_active_filter(self) -> None:
        backend = MagicMock()
        backend.get_state.return_value = FilterState(True, ColorFilterType.DEUTERANOPIA)
        state = restore_saved_filter(backend)
        backend.set_state.assert_called_once_with(True, ColorFilterType.DEUTERANOPIA)
        self.assertTrue(state.active)

    def test_does_nothing_when_inactive(self) -> None:
        backend = MagicMock()
        backend.get_state.return_value = FilterState(False, ColorFilterType.GRAYSCALE)
        restore_saved_filter(backend)
        backend.set_state.assert_not_called()


if __name__ == "__main__":
    unittest.main()
