from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QAbstractButton, QRadioButton, QWidget


# Accent color matching the coral/salmon orange from Windows 11 screenshot (image_2.png)
ACCENT_CORAL = QColor("#F28B66")
ACCENT_CORAL_HOVER = QColor("#F59B7B")


def create_palette_pixmap(size: int = 24, active: bool = True, tray_mode: bool = False) -> QPixmap:
    """
    Renders a crisp artist palette icon matching the Windows 11 Color filters header
    and a high-contrast system tray icon with an optional active indicator dot.
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    s = float(size)
    if tray_mode:
        # Rounded badge background for tray icon readability on dark/light taskbars
        bg_rect = QRectF(s * 0.08, s * 0.08, s * 0.84, s * 0.84)
        painter.setPen(QPen(QColor("#3E3E42"), max(1.0, s * 0.04)))
        painter.setBrush(QColor("#252528"))
        painter.drawRoundedRect(bg_rect, s * 0.22, s * 0.22)

    # Draw artist palette outline
    stroke_color = ACCENT_CORAL if (tray_mode and active) else QColor("#FFFFFF")
    pen = QPen(stroke_color, max(1.5, s * 0.075))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    pad = s * 0.22 if tray_mode else s * 0.14
    d = s - 2 * pad
    cx = s / 2.0
    cy = s / 2.0

    path = QPainterPath()
    # Start near bottom-right thumb notch and sweep counter-clockwise around the palette
    path.moveTo(cx + d * 0.18, cy + d * 0.46)
    path.cubicTo(
        cx - d * 0.35, cy + d * 0.52,
        cx - d * 0.54, cy + d * 0.10,
        cx - d * 0.46, cy - d * 0.18,
    )
    path.cubicTo(
        cx - d * 0.38, cy - d * 0.48,
        cx + d * 0.05, cy - d * 0.54,
        cx + d * 0.34, cy - d * 0.34,
    )
    path.cubicTo(
        cx + d * 0.54, cy - d * 0.18,
        cx + d * 0.50, cy + d * 0.14,
        cx + d * 0.30, cy + d * 0.14,
    )
    # Thumb indentation curve
    path.cubicTo(
        cx + d * 0.14, cy + d * 0.14,
        cx + d * 0.12, cy + d * 0.30,
        cx + d * 0.22, cy + d * 0.38,
    )
    path.cubicTo(
        cx + d * 0.26, cy + d * 0.42,
        cx + d * 0.24, cy + d * 0.46,
        cx + d * 0.18, cy + d * 0.46,
    )
    painter.drawPath(path)

    # Three paint dots inside the palette
    dot_r = max(1.1, s * 0.055)
    dots = [
        (cx - d * 0.22, cy - d * 0.06, QColor("#60CDFF") if (tray_mode and active) else stroke_color),
        (cx - d * 0.08, cy - d * 0.24, ACCENT_CORAL if (tray_mode and active) else stroke_color),
        (cx + d * 0.14, cy - d * 0.18, QColor("#6CCB5F") if (tray_mode and active) else stroke_color),
    ]
    painter.setPen(Qt.PenStyle.NoPen)
    for dx, dy, color in dots:
        painter.setBrush(color)
        painter.drawEllipse(QPointF(dx, dy), dot_r, dot_r)

    # Active badge dot in bottom-right corner for tray icon
    if tray_mode and active:
        badge_r = s * 0.14
        painter.setPen(QPen(QColor("#1E1E20"), max(1.0, s * 0.05)))
        painter.setBrush(ACCENT_CORAL)
        painter.drawEllipse(QPointF(s * 0.78, s * 0.78), badge_r, badge_r)

    painter.end()
    return pixmap


def create_tray_icon(active: bool = True) -> QIcon:
    return QIcon(create_palette_pixmap(size=64, active=active, tray_mode=True))


class Win11ToggleSwitch(QAbstractButton):
    """
    Windows 11 pill toggle switch matching the second screenshot:
    - Pill track (40x20px)
    - When ON: coral/salmon fill (#F28B66) with dark inner circle knob (#1E1918) on the right
    - When OFF: dark transparent fill with gray border (#9A9695) and light gray knob on the left
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(42, 22)

        self._knob_pos = 0.0
        self._anim = QPropertyAnimation(self, b"knobPos", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.toggled.connect(self._animate_knob)

    def get_knob_pos(self) -> float:
        return self._knob_pos

    def set_knob_pos(self, pos: float) -> None:
        self._knob_pos = pos
        self.update()

    knobPos = Property(float, get_knob_pos, set_knob_pos)

    def setChecked(self, checked: bool) -> None:
        super().setChecked(checked)
        self._knob_pos = 1.0 if checked else 0.0
        self.update()

    def _animate_knob(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._knob_pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(1.0, 1.0, self.width() - 2.0, self.height() - 2.0)
        radius = rect.height() / 2.0

        hovered = self.underMouse()

        if self.isChecked():
            track_color = ACCENT_CORAL_HOVER if hovered else ACCENT_CORAL
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(track_color)
            painter.drawRoundedRect(rect, radius, radius)
            knob_color = QColor("#1A1615")
        else:
            border_color = QColor("#C4C0BF") if hovered else QColor("#9E9A99")
            track_color = QColor(255, 255, 255, 12) if hovered else QColor(0, 0, 0, 40)
            painter.setPen(QPen(border_color, 1.3))
            painter.setBrush(track_color)
            painter.drawRoundedRect(rect, radius, radius)
            knob_color = QColor("#D6D2D1") if hovered else QColor("#B8B4B3")

        knob_r = 5.8 if not hovered else 6.4
        min_x = rect.left() + radius
        max_x = rect.right() - radius
        cx = min_x + (max_x - min_x) * self._knob_pos
        cy = rect.center().y()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(knob_color)
        painter.drawEllipse(QPointF(cx, cy), knob_r, knob_r)
        painter.end()


class Win11RadioButton(QRadioButton):
    """
    Windows 11 custom radio button matching image_2.png:
    - Unchecked: 20x20 circle with thin gray outline (#8A8583) and dark fill
    - Checked: 20x20 coral circle (#F28B66) with dark center dot (#1A1615)
    - Text: 14px Segoe UI / system sans-serif in crisp off-white (#F3F2F2)
    """

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)

    def hitButton(self, pos) -> bool:
        return self.rect().contains(pos)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        enabled = self.isEnabled()
        hovered = self.underMouse() and enabled
        checked = self.isChecked()

        circle_d = 20.0
        cx = 12.0
        cy = self.height() / 2.0
        circle_rect = QRectF(cx - circle_d / 2.0, cy - circle_d / 2.0, circle_d, circle_d)

        if checked:
            fill_color = ACCENT_CORAL if enabled else QColor("#7A5346")
            if hovered:
                fill_color = ACCENT_CORAL_HOVER
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill_color)
            painter.drawEllipse(circle_rect)

            # Inner dark dot matching Windows 11 radio button indicator
            inner_r = 4.6 if not hovered else 4.0
            painter.setBrush(QColor("#1A1615"))
            painter.drawEllipse(QPointF(cx, cy), inner_r, inner_r)
        else:
            border_color = QColor("#B0ABA9") if hovered else QColor("#878280")
            if not enabled:
                border_color = QColor("#575352")
            fill_color = QColor(255, 255, 255, 10) if hovered else QColor(0, 0, 0, 35)
            painter.setPen(QPen(border_color, 1.3))
            painter.setBrush(fill_color)
            painter.drawEllipse(circle_rect)

        # Draw label text
        text_color = QColor("#F5F4F4") if enabled else QColor("#7A7574")
        painter.setPen(text_color)
        font = self.font()
        font.setPixelSize(14)
        painter.setFont(font)

        text_rect = QRectF(34.0, 0.0, self.width() - 38.0, float(self.height()))
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self.text(),
        )
        painter.end()


class Win11ChevronButton(QAbstractButton):
    """
    Subtle chevron button on the right of the header bar to collapse/expand the filter list
    with a smooth rotation animation.
    """

    expandedChanged = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._expanded = False
        self._progress = 0.0  # 0.0 = collapsed (downward 'v'), 1.0 = expanded (upward '^')
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(28, 28)

        self._anim = QPropertyAnimation(self, b"chevronProgress", self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.clicked.connect(self.toggle_expanded)

    def get_chevron_progress(self) -> float:
        return self._progress

    def set_chevron_progress(self, val: float) -> None:
        self._progress = val
        self.update()

    chevronProgress = Property(float, get_chevron_progress, set_chevron_progress)

    @property
    def is_expanded(self) -> bool:
        return self._expanded

    def set_expanded(self, expanded: bool, animate: bool = True) -> None:
        if self._expanded != expanded:
            self._expanded = expanded
            target = 1.0 if expanded else 0.0
            self._anim.stop()
            if animate:
                self._anim.setStartValue(self._progress)
                self._anim.setEndValue(target)
                self._anim.start()
            else:
                self._progress = target
                self.update()
            self.expandedChanged.emit(self._expanded)
        elif not animate:
            self._anim.stop()
            self._progress = 1.0 if expanded else 0.0
            self.update()

    def toggle_expanded(self) -> None:
        self.set_expanded(not self._expanded, animate=True)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        if self.underMouse():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 18))
            painter.drawRoundedRect(self.rect(), 5.0, 5.0)

        pen = QPen(QColor("#E0DCDC"), 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        cx = self.width() / 2.0
        cy = self.height() / 2.0

        # Smoothly rotate between 0 deg (collapsed 'v') and 180 deg (expanded '^')
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(180.0 * self._progress)

        path = QPainterPath()
        path.moveTo(-5.0, -2.2)
        path.lineTo(0.0, 2.8)
        path.lineTo(5.0, -2.2)

        painter.drawPath(path)
        painter.restore()
        painter.end()
