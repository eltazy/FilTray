from __future__ import annotations

import os
import subprocess
import sys

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from ..backends.base import (
    UI_FILTER_OPTIONS,
    ColorFilterBackend,
    ColorFilterType,
    FilterState,
)
from ..startup import StartupManager, restore_saved_filter
from .popup import TrayFlyoutPopup
from .widgets import create_tray_icon


class ColorFilterTrayController(QObject):
    """
    Manages the background QSystemTrayIcon, its right-click context menu,
    and the custom Windows 11 dark popup card (TrayFlyoutPopup).
    """

    def __init__(
        self,
        app: QApplication,
        backend: ColorFilterBackend,
        show_on_start: bool = False,
        standalone_mode: bool = False,
    ) -> None:
        super().__init__()
        self.app = app
        self.backend = backend

        # Create popup flyout window
        self.popup = TrayFlyoutPopup(backend=self.backend, standalone_mode=standalone_mode)
        self.popup.card.stateChanged.connect(self._on_state_changed)

        # Create system tray icon
        self.tray_icon = QSystemTrayIcon(self)
        self.context_menu = QMenu()
        self._apply_menu_stylesheet()

        # Build context menu actions
        self.action_open_popup = QAction("Open Color Filters Flyout", self.context_menu)
        self.action_open_popup.triggered.connect(self.show_popup)
        self.context_menu.addAction(self.action_open_popup)

        self.action_toggle = QAction("Color filters: On", self.context_menu)
        self.action_toggle.setCheckable(True)
        self.action_toggle.triggered.connect(self._on_menu_toggle)
        self.context_menu.addAction(self.action_toggle)

        self.context_menu.addSeparator()

        self.filter_action_group = QActionGroup(self.context_menu)
        self.filter_action_group.setExclusive(True)
        self.filter_actions: dict[ColorFilterType, QAction] = {}

        for opt in UI_FILTER_OPTIONS:
            act = QAction(opt.label, self.context_menu)
            act.setCheckable(True)
            act.setData(int(opt.filter_type))
            act.triggered.connect(
                lambda checked, ft=opt.filter_type: self._on_menu_filter_selected(ft, checked)
            )
            self.filter_action_group.addAction(act)
            self.context_menu.addAction(act)
            self.filter_actions[opt.filter_type] = act

        self.context_menu.addSeparator()

        self.startup_manager = StartupManager()
        self.startup_manager.initialize_default_startup()

        self.action_startup = QAction("Run at startup", self.context_menu)
        self.action_startup.setCheckable(True)
        self.action_startup.setChecked(self.startup_manager.is_enabled())
        self.action_startup.triggered.connect(self._toggle_startup)
        self.context_menu.addAction(self.action_startup)

        if sys.platform == "win32":
            self.action_win_settings = QAction("Open Windows Color Filter Settings...", self.context_menu)
            self.action_win_settings.triggered.connect(self._open_windows_settings)
            self.context_menu.addAction(self.action_win_settings)

        self.context_menu.addSeparator()

        self.action_quit = QAction("Quit", self.context_menu)
        self.action_quit.triggered.connect(self.quit_app)
        self.context_menu.addAction(self.action_quit)

        self.tray_icon.setContextMenu(self.context_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)

        # Initial state sync
        initial_state = self.backend.get_state()
        self._refresh_tray_and_menu(initial_state)
        self.tray_icon.show()

        # Re-apply the last active color filter shortly after launch so the OS/compositor is ready
        if initial_state.active:
            QTimer.singleShot(500, self._restore_saved_filter_on_startup)

        # Poll OS state every 3 seconds in case user toggles Win+Ctrl+C or changes Windows Settings directly
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(3000)
        self.poll_timer.timeout.connect(self._poll_os_state)
        self.poll_timer.start()

        if show_on_start or standalone_mode:
            QTimer.singleShot(150, self.show_popup)

    def _apply_menu_stylesheet(self) -> None:
        self.context_menu.setStyleSheet(
            """
            QMenu {
                background-color: #2B2625;
                color: #F5F4F4;
                border: 1px solid #3E3837;
                border-radius: 8px;
                padding: 6px;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 24px 6px 12px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3D3635;
            }
            QMenu::item:disabled {
                color: #7A7574;
            }
            QMenu::separator {
                height: 1px;
                background: #3E3837;
                margin: 5px 8px;
            }
            """
        )

    def show_popup(self) -> None:
        self.popup.show_above_tray(self.tray_icon.geometry())

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.popup.toggle_popup(self.tray_icon.geometry())
        elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            # Middle-click quick-toggles Color Filters on/off directly
            current = self.backend.get_state()
            new_state = self.backend.set_active(not current.active)
            self.popup.card.sync_from_backend()
            self._refresh_tray_and_menu(new_state)

    def _on_state_changed(self, state: FilterState) -> None:
        self._refresh_tray_and_menu(state)

    def _on_menu_toggle(self, checked: bool) -> None:
        new_state = self.backend.set_active(checked)
        self.popup.card.sync_from_backend()
        self._refresh_tray_and_menu(new_state)

    def _on_menu_filter_selected(self, filter_type: ColorFilterType, checked: bool) -> None:
        if not checked:
            return
        new_state = self.backend.set_filter_type(filter_type)
        self.popup.card.sync_from_backend()
        self._refresh_tray_and_menu(new_state)

    def _poll_os_state(self) -> None:
        state = self.backend.get_state()
        self._refresh_tray_and_menu(state)
        if self.popup.isVisible():
            self.popup.card.sync_from_backend()

    def _refresh_tray_and_menu(self, state: FilterState) -> None:
        self.tray_icon.setIcon(create_tray_icon(active=state.active))

        filter_label = next(
            (opt.short_label for opt in UI_FILTER_OPTIONS if opt.filter_type == state.filter_type),
            state.filter_type.name,
        )
        status_str = f"On ({filter_label})" if state.active else "Off"
        self.tray_icon.setToolTip(f"Color Filters: {status_str}")

        self.action_toggle.blockSignals(True)
        self.action_toggle.setChecked(state.active)
        self.action_toggle.setText(f"Color filters: {'On' if state.active else 'Off'}")
        self.action_toggle.blockSignals(False)

        for ft, act in self.filter_actions.items():
            act.blockSignals(True)
            act.setChecked(ft == state.filter_type)
            act.setEnabled(state.active)
            act.blockSignals(False)

    def _open_windows_settings(self) -> None:
        if sys.platform == "win32":
            try:
                os.startfile("ms-settings:easeofaccess-colorfilter")
            except Exception:
                subprocess.Popen(["explorer.exe", "ms-settings:easeofaccess-colorfilter"])

    def _toggle_startup(self, enabled: bool) -> None:
        self.startup_manager.set_enabled(enabled)
        self.action_startup.blockSignals(True)
        self.action_startup.setChecked(self.startup_manager.is_enabled())
        self.action_startup.blockSignals(False)

    def _restore_saved_filter_on_startup(self) -> None:
        try:
            state = restore_saved_filter(self.backend)
        except Exception:
            state = self.backend.get_state()
        self.popup.card.sync_from_backend()
        self._refresh_tray_and_menu(state)

    def quit_app(self) -> None:
        self.tray_icon.hide()
        self.popup.close()
        self.app.quit()
