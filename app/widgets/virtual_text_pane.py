from __future__ import annotations
import re
from PyQt6.QtWidgets import QAbstractScrollArea, QSizePolicy
from PyQt6.QtGui import QPainter, QFont, QFontMetrics, QColor, QPen, QFontDatabase
from PyQt6.QtCore import Qt, QRect, pyqtSignal, QUrl
from app.core.diff_engine import (
    DiffResult, ROW_ADDED, ROW_DELETED, ROW_MODIFIED, ROW_PHANTOM
)
from app.ui import themes

LINE_NUM_WIDTH = 52
PADDING_LEFT   = 6
PADDING_RIGHT  = 8
BASE_FONT_SIZE = 11
MIN_FONT_SIZE  = 7
MAX_FONT_SIZE  = 24


class VirtualTextPane(QAbstractScrollArea):
    scroll_changed = pyqtSignal(int)
    file_dropped   = pyqtSignal(str)

    def __init__(self, side: str, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._side = side
        self._lines: list[str] = []
        self._row_types: dict[int, str] = {}
        self._char_ranges: dict[int, list[tuple[int, int]]] = {}
        self._line_numbers: list[int | None] = []

        # Search state
        self._search_matches: dict[int, list[tuple[int, int]]] = {}
        self._search_all: list[tuple[int, int, int]] = []   # (row, start, end)
        self._search_current_row: int = -1

        self._line_h  = 0
        self._char_w  = 0
        self._font: QFont | None = None
        self._font_size = BASE_FONT_SIZE
        self._syncing = False

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._init_font()
        self.verticalScrollBar().valueChanged.connect(self._on_vscroll)
        self.horizontalScrollBar().valueChanged.connect(self._on_hscroll)

    # ── Font ──────────────────────────────────────────────────────────────

    def _init_font(self):
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSize(self._font_size)
        self._font = font
        fm = QFontMetrics(font)
        self._line_h = fm.height() + 2
        self._char_w = fm.horizontalAdvance(" ")

    def set_font_size(self, size: int):
        self._font_size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, size))
        self._init_font()
        self._update_scroll_range()
        self.viewport().update()

    @property
    def font_size(self) -> int:
        return self._font_size

    # ── Content ───────────────────────────────────────────────────────────

    def apply_theme(self):
        self.viewport().update()

    def set_content(self, result: DiffResult):
        if self._side == "left":
            self._lines       = result.left_lines
            self._row_types   = result.left_row_types
            self._char_ranges = result.left_char_ranges
            self._line_numbers = result.left_line_numbers
        else:
            self._lines       = result.right_lines
            self._row_types   = result.right_row_types
            self._char_ranges = result.right_char_ranges
            self._line_numbers = result.right_line_numbers

        self._search_matches.clear()
        self._search_all.clear()
        self._search_current_row = -1
        self._update_scroll_range()
        self.verticalScrollBar().setValue(0)
        self.horizontalScrollBar().setValue(0)
        self.viewport().update()

    def clear(self):
        self._lines = []
        self._row_types = {}
        self._char_ranges = {}
        self._line_numbers = []
        self._search_matches.clear()
        self._search_all.clear()
        self._update_scroll_range()
        self.viewport().update()

    # ── Search ────────────────────────────────────────────────────────────

    def set_search(self, pattern: str, is_regex: bool, case_sensitive: bool) -> int:
        """Compute search matches. Returns total match count."""
        self._search_matches.clear()
        self._search_all.clear()
        self._search_current_row = -1

        if not pattern:
            self.viewport().update()
            return 0

        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            compiled = re.compile(pattern if is_regex else re.escape(pattern), flags)
        except re.error:
            self.viewport().update()
            return 0

        for row, line in enumerate(self._lines):
            matches = [(m.start(), m.end()) for m in compiled.finditer(line)]
            if matches:
                self._search_matches[row] = matches
                for s, e in matches:
                    self._search_all.append((row, s, e))

        self.viewport().update()
        return len(self._search_all)

    def clear_search(self):
        self._search_matches.clear()
        self._search_all.clear()
        self._search_current_row = -1
        self.viewport().update()

    def highlight_search_row(self, row: int):
        self._search_current_row = row
        self.viewport().update()

    # ── Scroll ────────────────────────────────────────────────────────────

    def _update_scroll_range(self):
        total_h = len(self._lines) * self._line_h
        vp_h = self.viewport().height()
        self.verticalScrollBar().setRange(0, max(0, total_h - vp_h))
        self.verticalScrollBar().setSingleStep(self._line_h)
        self.verticalScrollBar().setPageStep(vp_h)

        max_chars = max((len(l) for l in self._lines), default=0)
        content_w = max_chars * self._char_w + LINE_NUM_WIDTH + PADDING_LEFT + PADDING_RIGHT
        vp_w = self.viewport().width()
        self.horizontalScrollBar().setRange(0, max(0, content_w - vp_w))
        self.horizontalScrollBar().setSingleStep(self._char_w)
        self.horizontalScrollBar().setPageStep(vp_w)

    def _on_vscroll(self, value: int):
        if not self._syncing:
            self.scroll_changed.emit(value)
        self.viewport().update()

    def _on_hscroll(self, _value: int):
        self.viewport().update()

    def set_vscroll(self, value: int):
        self._syncing = True
        self.verticalScrollBar().setValue(value)
        self._syncing = False

    def set_hscroll(self, value: int):
        self.horizontalScrollBar().setValue(value)

    def scroll_to_row(self, row: int):
        target = max(0, row * self._line_h - self.viewport().height() // 2)
        self.verticalScrollBar().setValue(target)

    @property
    def first_visible_row(self) -> int:
        return self.verticalScrollBar().value() // self._line_h if self._line_h else 0

    @property
    def visible_row_count(self) -> int:
        return (self.viewport().height() // self._line_h) + 2 if self._line_h else 0

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_scroll_range()

    # ── Drag & drop ───────────────────────────────────────────────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].isLocalFile():
                event.acceptProposedAction()
                return
        event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.file_dropped.emit(urls[0].toLocalFile())
            event.acceptProposedAction()

    # ── Paint ─────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        if not self._lines or self._line_h == 0:
            self._paint_empty()
            return

        painter = QPainter(self.viewport())
        painter.setFont(self._font)
        t = themes.current()
        painter.fillRect(self.viewport().rect(), QColor(t["bg"]))

        h_offset = self.horizontalScrollBar().value()
        v_offset = self.verticalScrollBar().value()
        first_row = v_offset // self._line_h
        last_row  = min(len(self._lines),
                        first_row + self.viewport().height() // self._line_h + 2)
        fm = QFontMetrics(self._font)

        for idx in range(first_row, last_row):
            y = idx * self._line_h - v_offset
            self._paint_row(painter, idx, y, h_offset, fm, t)

        painter.end()

    def _paint_empty(self):
        painter = QPainter(self.viewport())
        t = themes.current()
        painter.fillRect(self.viewport().rect(), QColor(t["bg"]))
        painter.setPen(QColor(t["line_num_fg"]))
        painter.setFont(self._font)
        painter.drawText(self.viewport().rect(),
                         Qt.AlignmentFlag.AlignCenter,
                         "Open a file to begin comparison")
        painter.end()

    def _row_bg(self, row_type: str, t: dict) -> QColor | None:
        mapping = {
            ROW_ADDED:    t["added_bg"],
            ROW_DELETED:  t["deleted_bg"],
            ROW_MODIFIED: t["modified_bg"],
            ROW_PHANTOM:  t["phantom_bg"],
        }
        key = mapping.get(row_type)
        return QColor(key) if key else None

    def _paint_row(self, painter: QPainter, idx: int, y: int,
                   h_offset: int, fm: QFontMetrics, t: dict):
        vp_w      = self.viewport().width()
        row_type  = self._row_types.get(idx, "equal")
        line_text = self._lines[idx] if idx < len(self._lines) else ""

        # Line-number gutter
        painter.fillRect(QRect(0, y, LINE_NUM_WIDTH, self._line_h),
                         QColor(t["line_num_bg"]))

        # Row diff background
        row_bg = self._row_bg(row_type, t)
        if row_bg:
            painter.fillRect(QRect(LINE_NUM_WIDTH, y, vp_w, self._line_h), row_bg)

        # Char-level diff highlight
        if row_type == ROW_MODIFIED and idx in self._char_ranges:
            char_bg = QColor(t["char_diff_bg"])
            for start, end in self._char_ranges[idx]:
                cx = LINE_NUM_WIDTH + PADDING_LEFT - h_offset + start * self._char_w
                cw = (end - start) * self._char_w
                if cw > 0:
                    painter.fillRect(QRect(cx, y, cw, self._line_h), char_bg)

        # Search match highlight
        if idx in self._search_matches:
            is_current = (idx == self._search_current_row)
            for start, end in self._search_matches[idx]:
                cx = LINE_NUM_WIDTH + PADDING_LEFT - h_offset + start * self._char_w
                cw = max((end - start) * self._char_w, 4)
                color = QColor(t["search_current"] if is_current else t["search_match"])
                color.setAlpha(200)
                painter.fillRect(QRect(cx, y, cw, self._line_h), color)

        # Line number
        lnum = self._line_numbers[idx] if idx < len(self._line_numbers) else None
        painter.setPen(QColor(t["line_num_fg"]))
        if lnum is not None:
            painter.drawText(QRect(0, y, LINE_NUM_WIDTH - 4, self._line_h),
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                             str(lnum))

        # Text
        painter.setPen(QColor(t["text"]))
        painter.drawText(LINE_NUM_WIDTH + PADDING_LEFT - h_offset,
                         y + fm.ascent() + 1, line_text)

        # Separator
        painter.setPen(QPen(QColor(t["gutter_border"])))
        painter.drawLine(LINE_NUM_WIDTH - 1, y, LINE_NUM_WIDTH - 1, y + self._line_h)
