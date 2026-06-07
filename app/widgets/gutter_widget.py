from __future__ import annotations
from PyQt6.QtWidgets import QWidget, QApplication, QToolTip
from PyQt6.QtGui import QPainter, QColor, QPen, QPolygon, QCursor
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal
from app.core.diff_engine import ROW_PHANTOM, ROW_ADDED, ROW_DELETED, ROW_MODIFIED
from app.ui import themes

GUTTER_WIDTH = 32
ARROW_SIZE = 8


class GutterWidget(QWidget):
    copy_left_to_right = pyqtSignal(int)   # row index
    copy_right_to_left = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(GUTTER_WIDTH)
        self.setCursor(Qt.CursorShape.ArrowCursor)

        self._left_types: dict[int, str] = {}
        self._right_types: dict[int, str] = {}
        self._left_lines: list[str] = []
        self._right_lines: list[str] = []
        self._line_h = 20
        self._v_offset = 0
        self._first_visible = 0
        self._visible_count = 0
        self._total_rows = 0

        # Track button hit boxes: (row, direction) -> QRect
        self._buttons: list[tuple[int, str, QRect]] = []

    def set_diff_data(
        self,
        left_types: dict[int, str],
        right_types: dict[int, str],
        left_lines: list[str],
        right_lines: list[str],
        line_h: int,
    ):
        self._left_types = left_types
        self._right_types = right_types
        self._left_lines = left_lines
        self._right_lines = right_lines
        self._line_h = line_h
        self._total_rows = max(len(left_lines), len(right_lines))
        self.update()

    def set_scroll(self, first_visible: int, visible_count: int, v_offset: int):
        self._first_visible = first_visible
        self._visible_count = visible_count
        self._v_offset = v_offset
        self.update()

    def apply_theme(self):
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        t = themes.current()
        painter.fillRect(self.rect(), QColor(t["gutter_bg"]))

        # Border lines
        painter.setPen(QPen(QColor(t["gutter_border"])))
        painter.drawLine(0, 0, 0, self.height())
        painter.drawLine(self.width() - 1, 0, self.width() - 1, self.height())

        self._buttons.clear()
        last_row = min(self._total_rows, self._first_visible + self._visible_count + 2)

        for row in range(self._first_visible, last_row):
            y = row * self._line_h - self._v_offset
            lt = self._left_types.get(row, "equal")
            rt = self._right_types.get(row, "equal")

            if lt == ROW_PHANTOM and rt in (ROW_ADDED, ROW_MODIFIED):
                # Right side has content, left is phantom → ◀ arrow
                self._draw_arrow(painter, y, "left", t)
                rect = QRect(1, y + (self._line_h - ARROW_SIZE) // 2, GUTTER_WIDTH // 2 - 1, ARROW_SIZE)
                self._buttons.append((row, "left", rect))

            elif rt == ROW_PHANTOM and lt in (ROW_DELETED, ROW_MODIFIED):
                # Left side has content, right is phantom → ▶ arrow
                self._draw_arrow(painter, y, "right", t)
                rect = QRect(GUTTER_WIDTH // 2, y + (self._line_h - ARROW_SIZE) // 2, GUTTER_WIDTH // 2 - 1, ARROW_SIZE)
                self._buttons.append((row, "right", rect))

            elif lt == ROW_MODIFIED and rt == ROW_MODIFIED:
                # Both sides differ → show both arrows
                self._draw_arrow(painter, y, "left", t)
                self._draw_arrow(painter, y, "right", t)
                rl = QRect(1, y + (self._line_h - ARROW_SIZE) // 2, GUTTER_WIDTH // 2 - 2, ARROW_SIZE)
                rr = QRect(GUTTER_WIDTH // 2 + 1, y + (self._line_h - ARROW_SIZE) // 2, GUTTER_WIDTH // 2 - 2, ARROW_SIZE)
                self._buttons.append((row, "left", rl))
                self._buttons.append((row, "right", rr))

        painter.end()

    def _draw_arrow(self, painter: QPainter, y: int, direction: str, t: dict):
        cx = GUTTER_WIDTH // 2
        my = y + self._line_h // 2
        s = ARROW_SIZE // 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(t["line_num_fg"]))

        if direction == "left":
            pts = QPolygon([QPoint(cx - 2, my), QPoint(cx + s, my - s), QPoint(cx + s, my + s)])
        else:
            pts = QPolygon([QPoint(cx + 2, my), QPoint(cx - s, my - s), QPoint(cx - s, my + s)])
        painter.drawPolygon(pts)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position().toPoint()
        for row, direction, rect in self._buttons:
            if rect.contains(pos):
                if direction == "right":
                    # Copy left → clipboard
                    text = self._left_lines[row] if row < len(self._left_lines) else ""
                    QApplication.clipboard().setText(text)
                    QToolTip.showText(QCursor.pos(), f"Copied to clipboard: {text[:60]}")
                    self.copy_left_to_right.emit(row)
                else:
                    # Copy right → clipboard
                    text = self._right_lines[row] if row < len(self._right_lines) else ""
                    QApplication.clipboard().setText(text)
                    QToolTip.showText(QCursor.pos(), f"Copied to clipboard: {text[:60]}")
                    self.copy_right_to_left.emit(row)
                break
