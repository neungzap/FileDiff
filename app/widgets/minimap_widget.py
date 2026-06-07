from __future__ import annotations
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtCore import Qt, QRect, pyqtSignal
from app.ui import themes

MINIMAP_WIDTH = 14


class MinimapWidget(QWidget):
    scroll_requested = pyqtSignal(int)  # target row index

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(MINIMAP_WIDTH)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click to jump to position")

        self._diff_rows: list[int] = []
        self._total_rows: int = 0
        self._first_visible: int = 0
        self._visible_count: int = 0

    def set_diff_data(self, diff_rows: list[int], total_rows: int):
        self._diff_rows = diff_rows
        self._total_rows = total_rows
        self.update()

    def set_viewport(self, first_visible: int, visible_count: int):
        self._first_visible = first_visible
        self._visible_count = visible_count
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        t = themes.current()
        h = self.height()
        w = self.width()

        # Background
        painter.fillRect(self.rect(), QColor(t["minimap_bg"]))

        if self._total_rows == 0:
            painter.end()
            return

        scale = h / self._total_rows

        # Draw diff markers
        diff_color = QColor(t["minimap_diff"])
        painter.setPen(diff_color)
        for row in self._diff_rows:
            y = int(row * scale)
            painter.drawLine(0, y, w, y)

        # Draw viewport indicator
        vp_y = int(self._first_visible * scale)
        vp_h = max(4, int(self._visible_count * scale))
        vp_color = QColor(t["minimap_viewport"])
        vp_color.setAlpha(60)
        painter.fillRect(QRect(0, vp_y, w, vp_h), vp_color)
        vp_border = QColor(t["minimap_viewport"])
        vp_border.setAlpha(140)
        painter.setPen(vp_border)
        painter.drawRect(QRect(0, vp_y, w - 1, vp_h))

        painter.end()

    def mousePressEvent(self, event):
        if self._total_rows == 0:
            return
        ratio = event.position().y() / self.height()
        target = int(ratio * self._total_rows)
        target = max(0, min(target, self._total_rows - 1))
        self.scroll_requested.emit(target)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.mousePressEvent(event)
