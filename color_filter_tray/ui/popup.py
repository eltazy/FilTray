from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QEvent,
    QPoint,
    QPropertyAnimation,
    QRect,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ..backends.base import (
    UI_FILTER_OPTIONS,
    ColorFilterBackend,
    ColorFilterType,
    FilterState,
)
from .widgets import (
    Win11ChevronButton,
    Win11RadioButton,
    Win11ToggleSwitch,
    create_palette_pixmap,
)


class ColorFilterCardWidget(QWidget):
    """
    Inner Windows 11 dark acrylic/mica card widget matching image_2.png:
    - Top header row: Palette icon, "Color filters" title, "On"/"Off" label, coral toggle switch, chevron
    - Subtle 1px divider line
    - Smoothly animated expandable body containing the 6 radio button options
    """

    stateChanged = Signal(FilterState)
    sizeChanged = Signal()

    def __init__(
        self,
        backend: ColorFilterBackend,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.backend = backend
        self._updating_ui = False
        self._suppress_anim = False

        self.setFixedWidth(440)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header container
        self.header_frame = QFrame(self)
        self.header_frame.setFixedHeight(64)
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(20, 0, 18, 0)
        header_layout.setSpacing(14)

        # Palette Icon
        self.icon_label = QLabel(self.header_frame)
        self.icon_label.setPixmap(create_palette_pixmap(size=22, active=True, tray_mode=False))
        self.icon_label.setFixedSize(24, 24)
        header_layout.addWidget(self.icon_label)

        # Title Label ("Color filters")
        self.title_label = QLabel("Color filters", self.header_frame)
        self.title_label.setStyleSheet(
            "color: #F5F4F4; font-size: 14px; font-weight: 500; background: transparent;"
        )
        header_layout.addWidget(self.title_label)

        header_layout.addStretch(1)

        # Status text ("On" / "Off")
        self.status_label = QLabel("Off", self.header_frame)
        self.status_label.setStyleSheet(
            "color: #E2DFDF; font-size: 13px; background: transparent; margin-right: 2px;"
        )
        header_layout.addWidget(self.status_label)

        # Coral Toggle Switch
        self.toggle_switch = Win11ToggleSwitch(self.header_frame)
        self.toggle_switch.toggled.connect(self._on_toggle_changed)
        header_layout.addWidget(self.toggle_switch)

        # Chevron button (^ / v)
        self.chevron_btn = Win11ChevronButton(self.header_frame)
        self.chevron_btn.expandedChanged.connect(self._on_expanded_changed)
        header_layout.addWidget(self.chevron_btn)

        main_layout.addWidget(self.header_frame)

        # 1px separator line
        self.divider = QFrame(self)
        self.divider.setFixedHeight(1)
        self.divider.setStyleSheet("background-color: #1F1B1A;")
        main_layout.addWidget(self.divider)

        # Body container with radio options
        self.body_widget = QWidget(self)
        body_layout = QVBoxLayout(self.body_widget)
        body_layout.setContentsMargins(40, 14, 24, 18)
        body_layout.setSpacing(6)

        self.radio_group = QButtonGroup(self)
        self.radio_group.setExclusive(True)
        self.radio_buttons: dict[ColorFilterType, Win11RadioButton] = {}

        for option in UI_FILTER_OPTIONS:
            rb = Win11RadioButton(option.label, self.body_widget)
            self.radio_group.addButton(rb, int(option.filter_type))
            self.radio_buttons[option.filter_type] = rb
            body_layout.addWidget(rb)

        self.radio_group.idToggled.connect(self._on_filter_selected)
        main_layout.addWidget(self.body_widget)

        # Calculate natural expanded height of the radio list body
        self._expanded_body_height = self.body_widget.sizeHint().height()
        self._current_body_height = 0

        # Smooth height animation for expanding and collapsing the body
        self._expand_anim = QPropertyAnimation(self, b"bodyHeight", self)
        self._expand_anim.setDuration(220)
        self._expand_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._expand_anim.finished.connect(self._on_expand_anim_finished)

        # Default to collapsed view so only the header bar is shown initially
        self.divider.setVisible(False)
        self.body_widget.setFixedHeight(0)
        self.body_widget.setVisible(False)
        self.setFixedHeight(self.header_frame.height())

        self.sync_from_backend()

    def get_body_height(self) -> int:
        return self._current_body_height

    def set_body_height(self, h: int) -> None:
        self._current_body_height = max(0, int(h))
        self.body_widget.setFixedHeight(self._current_body_height)
        divider_h = 1 if self._current_body_height > 0 else 0
        self.setFixedHeight(self.header_frame.height() + divider_h + self._current_body_height)
        self.update()
        self.sizeChanged.emit()

    bodyHeight = Property(int, get_body_height, set_body_height)

    def set_expanded(self, expanded: bool, animate: bool = True) -> None:
        prev_suppress = self._suppress_anim
        self._suppress_anim = not animate
        try:
            if self.chevron_btn.is_expanded != expanded:
                self.chevron_btn.set_expanded(expanded, animate=animate)
            elif not animate:
                self._apply_expanded_immediate(expanded)
        finally:
            self._suppress_anim = prev_suppress

    def _apply_expanded_immediate(self, expanded: bool) -> None:
        self._expand_anim.stop()
        target_h = self._expanded_body_height if expanded else 0
        self.divider.setVisible(expanded)
        self.body_widget.setVisible(expanded)
        self.set_body_height(target_h)

    def sync_from_backend(self) -> FilterState:
        """Read current state from the OS backend and update the UI controls without re-triggering."""
        state = self.backend.get_state()
        self._updating_ui = True
        try:
            self.toggle_switch.setChecked(state.active)
            self.status_label.setText("On" if state.active else "Off")

            target_rb = self.radio_buttons.get(state.filter_type)
            if target_rb is not None:
                target_rb.setChecked(True)

            # When toggle is Off, disable radio buttons or allow selecting only when On
            for rb in self.radio_buttons.values():
                rb.setEnabled(state.active)
                rb.update()
        finally:
            self._updating_ui = False

        self.update()
        return state

    def _on_toggle_changed(self, checked: bool) -> None:
        self.status_label.setText("On" if checked else "Off")
        for rb in self.radio_buttons.values():
            rb.setEnabled(checked)
            rb.update()

        if checked and not self.chevron_btn.is_expanded:
            self.chevron_btn.set_expanded(True, animate=not self._updating_ui)
        elif not checked and self.chevron_btn.is_expanded:
            self.chevron_btn.set_expanded(False, animate=not self._updating_ui)

        if self._updating_ui:
            return

        selected_id = self.radio_group.checkedId()
        ft = (
            ColorFilterType(selected_id)
            if selected_id in ColorFilterType._value2member_map_
            else ColorFilterType.GRAYSCALE
        )
        self.backend.set_state(checked, ft)
        self.stateChanged.emit(FilterState(active=checked, filter_type=ft))

    def _on_filter_selected(self, button_id: int, checked: bool) -> None:
        if not checked or self._updating_ui:
            return
        if button_id not in ColorFilterType._value2member_map_:
            return

        ft = ColorFilterType(button_id)
        active = self.toggle_switch.isChecked()
        self.backend.set_state(active, ft)
        self.stateChanged.emit(FilterState(active=active, filter_type=ft))

    def _on_expanded_changed(self, expanded: bool) -> None:
        if self._suppress_anim:
            self._apply_expanded_immediate(expanded)
            return

        self._expand_anim.stop()
        target_h = self._expanded_body_height if expanded else 0
        if expanded:
            self.divider.setVisible(True)
            self.body_widget.setVisible(True)

        self._expand_anim.setStartValue(self._current_body_height)
        self._expand_anim.setEndValue(target_h)
        self._expand_anim.start()

    def _on_expand_anim_finished(self) -> None:
        if not self.chevron_btn.is_expanded and self._current_body_height == 0:
            self.divider.setVisible(False)
            self.body_widget.setVisible(False)
            self.setFixedHeight(self.header_frame.height())
            self.sizeChanged.emit()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
        radius = 8.0

        # Dark warm charcoal surface matching Windows 11 dark settings card (#2B2625)
        painter.setPen(QPen(QColor("#3E3837"), 1.0))
        painter.setBrush(QColor("#2B2625"))
        painter.drawRoundedRect(rect, radius, radius)

        # Slight highlight on top header area when expanded or animating open
        if self._current_body_height > 0:
            header_rect = QRectF(1.0, 1.0, self.width() - 2.0, float(self.header_frame.height() - 1))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 5))
            painter.drawRoundedRect(header_rect, radius, radius)

        painter.end()


class TrayFlyoutPopup(QWidget):
    """
    Frameless floating popup window that appears right next to the Windows system tray icon
    when clicked, defaults to the collapsed header view, and smoothly animates its expansion
    and collapse away from the taskbar (downward if taskbar is at the top, upward/downward
    toward bottom if taskbar is at the bottom) so the expanded options are never hidden.
    """

    def __init__(
        self,
        backend: ColorFilterBackend,
        standalone_mode: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.backend = backend
        self.standalone_mode = standalone_mode
        self._taskbar_at_top = False
        self._anchor_edge_y: int | None = None

        if standalone_mode:
            self.setWindowTitle("Windows Color Filters — Tray Flyout")
            self.setWindowFlags(
                Qt.WindowType.Window
                | Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
            )
        else:
            self.setWindowFlags(
                Qt.WindowType.Tool
                | Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.NoDropShadowWindowHint
            )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._margin = 8
        layout = QVBoxLayout(self)
        layout.setContentsMargins(self._margin, self._margin, self._margin, self._margin)
        layout.setSpacing(0)

        self.card = ColorFilterCardWidget(backend, self)
        self.card.sizeChanged.connect(self._on_card_resized)
        layout.addWidget(self.card)

        self.setFixedSize(
            self.card.width() + self._margin * 2,
            self.card.height() + self._margin * 2,
        )

    def _detect_taskbar_at_top(self, anchor: QPoint, screen) -> bool:
        """
        Determine whether the taskbar / tray icon is located at the top of the screen.
        Checks both the screen's top work-area inset (availableGeometry().top() > geometry().top())
        and whether the tray icon / cursor anchor is in the upper half of the screen.
        """
        full_geo = screen.geometry()
        avail_geo = screen.availableGeometry()
        if avail_geo.top() > full_geo.top() and avail_geo.bottom() == full_geo.bottom():
            return True
        if avail_geo.bottom() < full_geo.bottom() and avail_geo.top() == full_geo.top():
            return False
        return anchor.y() < avail_geo.center().y()

    def _on_card_resized(self) -> None:
        old_geo = self.geometry()
        new_w = self.card.width() + self._margin * 2
        new_h = self.card.height() + self._margin * 2

        screen = QGuiApplication.screenAt(old_geo.center()) or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry()

        x = max(avail.left() + 12, min(old_geo.x(), avail.right() - new_w - 12))

        if self._taskbar_at_top:
            # Taskbar is at top: keep top edge anchored near the top taskbar and animate downward
            top_anchor = self._anchor_edge_y if self._anchor_edge_y is not None else old_geo.top()
            y = top_anchor
            if y + new_h > avail.bottom() - 12:
                y = max(avail.top() + 12, avail.bottom() - new_h - 12)
        else:
            # Taskbar is at bottom: keep bottom edge anchored above the bottom taskbar
            # so expanding smoothly grows upward into the screen and collapsing shrinks downward
            bottom_anchor = (
                self._anchor_edge_y
                if self._anchor_edge_y is not None
                else (old_geo.top() + old_geo.height())
            )
            y = bottom_anchor - new_h
            if y < avail.top() + 12:
                y = avail.top() + 12
            if y + new_h > avail.bottom() - 12:
                y = avail.bottom() - new_h - 12

        self.setFixedSize(new_w, new_h)
        self.move(x, y)

    def show_above_tray(self, tray_geometry: QRect | None = None) -> None:
        """
        Position the flyout neatly next to the system tray icon, starting in collapsed state by default,
        and record whether the taskbar is at the top or bottom of the screen.
        """
        self.card.sync_from_backend()
        # Reset to collapsed without animation before showing the popup
        self.card.set_expanded(False, animate=False)

        w = self.card.width() + self._margin * 2
        h = self.card.height() + self._margin * 2
        self.setFixedSize(w, h)

        cursor_pos = QCursor.pos()
        if tray_geometry and not tray_geometry.isNull() and tray_geometry.width() > 0:
            anchor = tray_geometry.center()
        else:
            anchor = cursor_pos

        screen = QGuiApplication.screenAt(anchor) or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry()

        self._taskbar_at_top = self._detect_taskbar_at_top(anchor, screen)

        # Center horizontally on the tray icon, clamped inside the screen's available area with a 12px margin
        x = anchor.x() - w // 2
        x = max(avail.left() + 12, min(x, avail.right() - w - 12))

        if self._taskbar_at_top:
            y = avail.top() + 12
            self._anchor_edge_y = y
        else:
            y = avail.bottom() - h - 12
            self._anchor_edge_y = y + h

        self.move(QPoint(x, y))
        self.show()
        self.raise_()
        self.activateWindow()

    def toggle_popup(self, tray_geometry: QRect | None = None) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show_above_tray(tray_geometry)

    def event(self, event: QEvent) -> bool:
        # Auto-dismiss when the flyout loses focus (standard Windows 11 tray flyout behavior)
        if (
            not self.standalone_mode
            and event.type() == QEvent.Type.WindowDeactivate
            and self.isVisible()
        ):
            self.hide()
            return True
        return super().event(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape and not self.standalone_mode:
            self.hide()
            return
        super().keyPressEvent(event)
