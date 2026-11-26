from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from color_filter_tray.backends.base import (
    UI_FILTER_OPTIONS,
    ColorFilterType,
)
from color_filter_tray.backends.linux import LinuxColorFilterBackend
from color_filter_tray.backends.windows import WindowsColorFilterBackend


class TestColorFilterBackends(unittest.TestCase):
    def test_ui_filter_options_order_and_values(self) -> None:
        # Verify the 6 options match the exact order and DWORD values of Windows 11 Settings
        expected = [
            (ColorFilterType.DEUTERANOPIA, 3, "Red-green (green weak, deuteranopia)"),
            (ColorFilterType.PROTANOPIA, 4, "Red-green (red weak, protanopia)"),
            (ColorFilterType.TRITANOPIA, 5, "Blue-yellow (tritanopia)"),
            (ColorFilterType.GRAYSCALE, 0, "Grayscale"),
            (ColorFilterType.GRAYSCALE_INVERTED, 2, "Grayscale inverted"),
            (ColorFilterType.INVERTED, 1, "Inverted"),
        ]
        self.assertEqual(len(UI_FILTER_OPTIONS), 6)
        for opt, (ft, val, label) in zip(UI_FILTER_OPTIONS, expected):
            self.assertEqual(opt.filter_type, ft)
            self.assertEqual(int(opt.filter_type), val)
            self.assertEqual(opt.label, label)

    def test_linux_backend_state_persistence(self) -> None:
        backend = LinuxColorFilterBackend()
        backend.set_state(True, ColorFilterType.GRAYSCALE)
        state = backend.get_state()
        self.assertTrue(state.active)
        self.assertEqual(state.filter_type, ColorFilterType.GRAYSCALE)

        state2 = backend.set_filter_type(ColorFilterType.DEUTERANOPIA)
        self.assertTrue(state2.active)
        self.assertEqual(state2.filter_type, ColorFilterType.DEUTERANOPIA)

        state3 = backend.set_active(False)
        self.assertFalse(state3.active)
        self.assertEqual(state3.filter_type, ColorFilterType.DEUTERANOPIA)

    def test_windows_backend_caching_on_non_win32(self) -> None:
        backend = WindowsColorFilterBackend()
        backend.set_state(True, ColorFilterType.TRITANOPIA)
        state = backend.get_state()
        self.assertTrue(state.active)
        self.assertEqual(state.filter_type, ColorFilterType.TRITANOPIA)


if __name__ == "__main__":
    unittest.main()
