from __future__ import annotations
import re
from PyQt6.QtWidgets import QAbstractScrollArea, QSizePolicy, QApplication, QMenu
from PyQt6.QtGui import QPainter, QFont, QFontMetrics, QColor, QPen, QFontDatabase, QKeySequence
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal, QUrl
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
DEFAULT_FONT_FAMILY = ""   # empty = system fixed font


class VirtualTextPane(QAbstractScrollArea):
    scroll_changed  = pyqtSignal(int)
    file_dropped    = pyqtSignal(str)
    paste_requested = pyqtSignal(str)   # side: "left" or "right"

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

        # Selection state: (row, col) pairs; None = no selection
        self._sel_start: tuple[int, int] | None = None
        self._sel_end:   tuple[int, int] | None = None
        self._selecting  = False

        self._line_h  = 0
        self._char_w  = 0
        self._font: QFont | None = None
        self._font_size = BASE_FONT_SIZE
        self._font_family = DEFAULT_FONT_FAMILY
        self._syncing = False

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        self._init_font()
        self.verticalScrollBar().valueChanged.connect(self._on_vscroll)
        self.horizontalScrollBar().valueChanged.connect(self._on_hscroll)

    # ── Font ──────────────────────────────────────────────────────────────

    def _init_font(self):
        if self._font_family:
            font = QFont(self._font_family)
            font.setStyleHint(QFont.StyleHint.Monospace)
        else:
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

    def set_font_family(self, family: str):
        self._font_family = family
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
        self._sel_start = None
        self._sel_end   = None
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

    # ── Selection ─────────────────────────────────────────────────────────

    def _pos_to_row_col(self, pos: QPoint) -> tuple[int, int]:
        """Convert viewport pixel position to (row, col)."""
        v_offset = self.verticalScrollBar().value()
        h_offset = self.horizontalScrollBar().value()
        row = max(0, min(len(self._lines) - 1,
                         (pos.y() + v_offset) // self._line_h if self._line_h else 0))
        line_text = self._lines[row] if row < len(self._lines) else ""
        x_in_text = pos.x() - LINE_NUM_WIDTH - PADDING_LEFT + h_offset
        if not line_text or x_in_text <= 0:
            col = 0
        else:
            fm = QFontMetrics(self._font)
            col = len(line_text)
            for i in range(len(line_text) + 1):
                if fm.horizontalAdvance(line_text[:i]) >= x_in_text:
                    col = i
                    break
        return row, col

    def _sel_normalized(self) -> tuple[tuple[int, int], tuple[int, int]] | None:
        """Return (start, end) in document order, or None if no selection."""
        if self._sel_start is None or self._sel_end is None:
            return None
        a, b = self._sel_start, self._sel_end
        return (a, b) if a <= b else (b, a)

    def _get_selected_text(self) -> str:
        norm = self._sel_normalized()
        if norm is None:
            return ""
        (r1, c1), (r2, c2) = norm
        if r1 == r2:
            return self._lines[r1][c1:c2] if r1 < len(self._lines) else ""
        parts = []
        if r1 < len(self._lines):
            parts.append(self._lines[r1][c1:])
        for r in range(r1 + 1, r2):
            parts.append(self._lines[r] if r < len(self._lines) else "")
        if r2 < len(self._lines):
            parts.append(self._lines[r2][:c2])
        return "\n".join(parts)

    def _copy_selection(self):
        text = self._get_selected_text()
        if text:
            QApplication.clipboard().setText(text)

    def _select_all(self):
        if not self._lines:
            return
        self._sel_start = (0, 0)
        last_row = len(self._lines) - 1
        self._sel_end = (last_row, len(self._lines[last_row]))
        self.viewport().update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._selecting = True
            rc = self._pos_to_row_col(event.position().toPoint())
            self._sel_start = rc
            self._sel_end   = rc
            self.viewport().update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._selecting and (event.buttons() & Qt.MouseButton.LeftButton):
            self._sel_end = self._pos_to_row_col(event.position().toPoint())
            self.viewport().update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._selecting = False
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Copy):
            self._copy_selection()
        elif event.matches(QKeySequence.StandardKey.SelectAll):
            self._select_all()
        elif event.matches(QKeySequence.StandardKey.Paste):
            self.paste_requested.emit(self._side)
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        act_copy = menu.addAction("Copy")
        act_copy.setShortcut(QKeySequence.StandardKey.Copy)
        act_copy.setEnabled(bool(self._get_selected_text()))
        act_copy.triggered.connect(self._copy_selection)
        menu.addSeparator()
        act_all = menu.addAction("Select All")
        act_all.setShortcut(QKeySequence.StandardKey.SelectAll)
        act_all.triggered.connect(self._select_all)
        menu.addSeparator()
        act_paste = menu.addAction("Paste as content")
        act_paste.setShortcut(QKeySequence.StandardKey.Paste)
        act_paste.setEnabled(bool(QApplication.clipboard().text()))
        act_paste.triggered.connect(lambda: self.paste_requested.emit(self._side))
        menu.exec(event.globalPos())

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

        # Char-level diff highlight — use fm.horizontalAdvance for exact pixel positions
        text_x = LINE_NUM_WIDTH + PADDING_LEFT - h_offset
        if row_type == ROW_MODIFIED and idx in self._char_ranges:
            char_bg = QColor(t["char_diff_bg"])
            for start, end in self._char_ranges[idx]:
                cx = text_x + fm.horizontalAdvance(line_text[:start])
                cw = fm.horizontalAdvance(line_text[start:end])
                if cw > 0:
                    painter.fillRect(QRect(cx, y, cw, self._line_h), char_bg)

        # Search match highlight
        if idx in self._search_matches:
            is_current = (idx == self._search_current_row)
            for start, end in self._search_matches[idx]:
                cx = text_x + fm.horizontalAdvance(line_text[:start])
                cw = max(fm.horizontalAdvance(line_text[start:end]), 4)
                color = QColor(t["search_current"] if is_current else t["search_match"])
                color.setAlpha(200)
                painter.fillRect(QRect(cx, y, cw, self._line_h), color)

        # Selection highlight
        norm = self._sel_normalized()
        if norm is not None:
            (r1, c1), (r2, c2) = norm
            if r1 <= idx <= r2:
                sel_color = QColor(t["selection_bg"])
                sel_color.setAlpha(180)
                if r1 == r2:
                    sx = text_x + fm.horizontalAdvance(line_text[:c1])
                    sw = max(fm.horizontalAdvance(line_text[c1:c2]), 2)
                elif idx == r1:
                    sx = text_x + fm.horizontalAdvance(line_text[:c1])
                    sw = max(vp_w - sx, 2)
                elif idx == r2:
                    sx = text_x
                    sw = max(fm.horizontalAdvance(line_text[:c2]), 2)
                else:
                    sx = text_x
                    sw = vp_w
                painter.fillRect(QRect(sx, y, sw, self._line_h), sel_color)

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
