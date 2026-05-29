from __future__ import annotations
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QFileDialog, QMessageBox, QProgressDialog,
    QApplication,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QAction, QKeySequence

from app.core.file_loader import load_file, BinaryFileError, FileLoadError, FileContent
from app.core.diff_engine import compute_diff, DiffResult
from app.core.filter_engine import FilterEngine
from app.widgets.virtual_text_pane import VirtualTextPane
from app.widgets.gutter_widget import GutterWidget
from app.widgets.minimap_widget import MinimapWidget
from app.widgets.filter_bar import FilterBar
from app.widgets.search_bar import SearchBar
from app.widgets.file_browser_panel import FileBrowserPanel
from app.ui.status_bar import AppStatusBar
from app.ui.about_dialog import AboutDialog
from app.ui.shortcuts_dialog import ShortcutsDialog
from app.ui import themes


# ──────────────────────────────────────────────────────────────
# Background worker for load + diff
# ──────────────────────────────────────────────────────────────

class SingleFileWorker(QObject):
    """Load one file and display it in its pane immediately."""
    finished = pyqtSignal(object, str)   # FileContent, side
    error    = pyqtSignal(str)

    def __init__(self, path: str, encoding, side: str):
        super().__init__()
        self._path = path
        self._enc  = encoding
        self._side = side

    def run(self):
        try:
            fc = load_file(self._path, self._enc)
            self.finished.emit(fc, self._side)
        except (BinaryFileError, FileLoadError) as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(f"Unexpected error: {e}")


class DiffWorker(QObject):
    finished = pyqtSignal(object, object, object)
    error = pyqtSignal(str)

    def __init__(self, left_path, right_path, left_enc, right_enc, filter_engine):
        super().__init__()
        self._lp = left_path
        self._rp = right_path
        self._le = left_enc
        self._re = right_enc
        self._fe = filter_engine

    def run(self):
        try:
            lfc = load_file(self._lp, self._le)
            rfc = load_file(self._rp, self._re)
            result = compute_diff(lfc.lines, rfc.lines, self._fe)
            self.finished.emit(lfc, rfc, result)
        except (BinaryFileError, FileLoadError) as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(f"Unexpected error: {e}")


# ──────────────────────────────────────────────────────────────
# Main Window
# ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FileDiff")
        self.resize(1500, 860)

        self._left_path: str | None = None
        self._right_path: str | None = None
        self._left_enc: str | None = None
        self._right_enc: str | None = None
        self._left_fc: FileContent | None = None
        self._right_fc: FileContent | None = None
        self._diff_result: DiffResult | None = None
        self._diff_row_idx: int = 0
        self._filter_engine = FilterEngine()
        self._worker_thread: QThread | None = None

        # Search state
        self._search_rows: list[int] = []   # unique rows with any match
        self._search_idx: int = -1

        self._build_ui()
        self._build_menu()
        self._apply_theme()

    # ------------------------------------------------------------------ UI build

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Ignore pattern bar
        self._filter_bar = FilterBar()
        self._filter_bar.filter_changed.connect(self._on_filter_changed)
        root_layout.addWidget(self._filter_bar)

        # Search bar (always visible)
        self._search_bar = SearchBar()
        self._search_bar.search_requested.connect(self._on_search_requested)
        self._search_bar.navigate.connect(self._navigate_search)
        self._search_bar.closed.connect(self._close_search)
        root_layout.addWidget(self._search_bar)

        # Main area: [left_col | gutter | right_col] | minimap
        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        # ── Single sidebar (far left) ─────────────────────────────────────
        self._browser = FileBrowserPanel()
        self._browser.open_as_left.connect(self._load_left)
        self._browser.open_as_right.connect(self._load_right)

        # ── Left text pane ────────────────────────────────────────────────
        self._left_pane = VirtualTextPane("left")
        self._left_pane.scroll_changed.connect(self._sync_scroll_from_left)
        self._left_pane.file_dropped.connect(self._drop_left)

        # ── Gutter ────────────────────────────────────────────────────────
        self._gutter = GutterWidget()
        self._gutter.copy_left_to_right.connect(self._on_copy_ltr)
        self._gutter.copy_right_to_left.connect(self._on_copy_rtl)

        # ── Right text pane ───────────────────────────────────────────────
        self._right_pane = VirtualTextPane("right")
        self._right_pane.scroll_changed.connect(self._sync_scroll_from_right)
        self._right_pane.file_dropped.connect(self._drop_right)

        # ── Diff area splitter: left | gutter | right ─────────────────────
        self._diff_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._diff_splitter.addWidget(self._left_pane)
        self._diff_splitter.addWidget(self._gutter)
        self._diff_splitter.addWidget(self._right_pane)
        self._diff_splitter.setStretchFactor(0, 1)
        self._diff_splitter.setStretchFactor(1, 0)
        self._diff_splitter.setStretchFactor(2, 1)
        self._diff_splitter.setSizes([660, 32, 660])
        self._diff_splitter.setCollapsible(1, False)
        h_gutter = self._diff_splitter.handle(1)
        if h_gutter:
            h_gutter.setEnabled(False)

        # ── Main splitter: sidebar | diff area ────────────────────────────
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(self._browser)
        self._splitter.addWidget(self._diff_splitter)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([220, 1280])
        self._splitter.setCollapsible(0, True)

        h_layout.addWidget(self._splitter, 1)

        # ── Minimap ───────────────────────────────────────────────────────
        self._minimap = MinimapWidget()
        self._minimap.scroll_requested.connect(self._on_minimap_scroll)
        h_layout.addWidget(self._minimap, 0)

        root_layout.addLayout(h_layout, 1)

        # Status bar
        self._status = AppStatusBar()
        self._status.encoding_changed.connect(self._on_encoding_changed)
        self._status.font_size_changed.connect(self._on_font_size_changed)
        self.setStatusBar(self._status)

        self._left_pane.verticalScrollBar().valueChanged.connect(self._update_gutter_scroll)

    def _build_menu(self):
        mb = self.menuBar()

        # ── File menu ─────────────────────────────────────────────────────
        file_menu = mb.addMenu("&File")

        act_open_left = QAction("Open &Left File…", self)
        act_open_left.setShortcut(QKeySequence("Ctrl+L"))
        act_open_left.triggered.connect(self._open_left)
        file_menu.addAction(act_open_left)

        act_open_right = QAction("Open &Right File…", self)
        act_open_right.setShortcut(QKeySequence("Ctrl+R"))
        act_open_right.triggered.connect(self._open_right)
        file_menu.addAction(act_open_right)

        file_menu.addSeparator()

        # Export submenu
        export_menu = file_menu.addMenu("&Export")

        act_export_auto = QAction("Auto-save Both  (_before / _after)", self)
        act_export_auto.setShortcut(QKeySequence("Ctrl+E"))
        act_export_auto.triggered.connect(self._export_auto)
        export_menu.addAction(act_export_auto)

        export_menu.addSeparator()

        act_export_left_as = QAction("Save Left As…", self)
        act_export_left_as.setShortcut(QKeySequence("Ctrl+Shift+L"))
        act_export_left_as.triggered.connect(self._export_left_as)
        export_menu.addAction(act_export_left_as)

        act_export_right_as = QAction("Save Right As…", self)
        act_export_right_as.setShortcut(QKeySequence("Ctrl+Shift+R"))
        act_export_right_as.triggered.connect(self._export_right_as)
        export_menu.addAction(act_export_right_as)

        file_menu.addSeparator()
        act_quit = QAction("&Quit", self)
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # ── Navigate menu ─────────────────────────────────────────────────
        nav_menu = mb.addMenu("&Navigate")

        act_prev = QAction("&Previous Difference", self)
        act_prev.setShortcut(QKeySequence("F7"))
        act_prev.triggered.connect(self._prev_diff)
        nav_menu.addAction(act_prev)

        act_next = QAction("&Next Difference", self)
        act_next.setShortcut(QKeySequence("F8"))
        act_next.triggered.connect(self._next_diff)
        nav_menu.addAction(act_next)

        # ── View menu ─────────────────────────────────────────────────────
        view_menu = mb.addMenu("&View")

        act_find = QAction("&Find / Search…", self)
        act_find.setShortcut(QKeySequence("Ctrl+F"))
        act_find.triggered.connect(self._open_search)
        view_menu.addAction(act_find)

        view_menu.addSeparator()

        act_theme = QAction("Toggle &Dark/Light Theme", self)
        act_theme.setShortcut(QKeySequence("Ctrl+T"))
        act_theme.triggered.connect(self._toggle_theme)
        view_menu.addAction(act_theme)

        act_browser = QAction("Toggle &File Browser", self)
        act_browser.setShortcut(QKeySequence("Ctrl+B"))
        act_browser.triggered.connect(self._toggle_browser)
        view_menu.addAction(act_browser)

        view_menu.addSeparator()

        act_zoom_in = QAction("Zoom &In", self)
        act_zoom_in.setShortcut(QKeySequence("Ctrl+="))
        act_zoom_in.triggered.connect(self._font_increase)
        view_menu.addAction(act_zoom_in)

        act_zoom_out = QAction("Zoom &Out", self)
        act_zoom_out.setShortcut(QKeySequence("Ctrl+-"))
        act_zoom_out.triggered.connect(self._font_decrease)
        view_menu.addAction(act_zoom_out)

        act_zoom_reset = QAction("&Reset Zoom", self)
        act_zoom_reset.setShortcut(QKeySequence("Ctrl+0"))
        act_zoom_reset.triggered.connect(self._font_reset)
        view_menu.addAction(act_zoom_reset)

        # ── Help menu ─────────────────────────────────────────────────────
        help_menu = mb.addMenu("&Help")
        act_shortcuts = QAction("&Keyboard Shortcuts", self)
        act_shortcuts.setShortcut(QKeySequence("Ctrl+/"))
        act_shortcuts.triggered.connect(self._show_shortcuts)
        help_menu.addAction(act_shortcuts)
        help_menu.addSeparator()
        act_about = QAction("&About FileDiff…", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    # ------------------------------------------------------------------ File open / browser

    def _open_left(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Left File")
        if path:
            self._load_left(path)

    def _open_right(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Right File")
        if path:
            self._load_right(path)

    def _drop_left(self, path: str):
        self._load_left(path)

    def _drop_right(self, path: str):
        self._load_right(path)

    def _load_left(self, path: str):
        self._left_path = path
        self._left_enc = None
        self._browser.set_root(os.path.dirname(path))
        if self._right_path:
            self._run_diff()          # both sides ready → full diff
        else:
            self._run_single(path, None, "left")   # show immediately

    def _load_right(self, path: str):
        self._right_path = path
        self._right_enc = None
        self._browser.set_root(os.path.dirname(path))
        if self._left_path:
            self._run_diff()          # both sides ready → full diff
        else:
            self._run_single(path, None, "right")  # show immediately

    def _toggle_browser(self):
        self._browser.setVisible(not self._browser.isVisible())

    # ------------------------------------------------------------------ Export

    @staticmethod
    def _extract_sh_basename(lines: list[str]) -> str | None:
        """Scan ALL lines top-to-bottom, stop at first match of #sh/#show pattern."""
        import re
        for line in lines:
            m = re.search(r'#\s{0,2}sh', line)
            if not m:
                continue
            raw = line[: m.start()].strip()
            safe = re.sub(r'[^\w\-\.]', '_', raw).strip('_')
            if safe:
                return safe   # stop immediately at first match
        return None

    def _export_auto(self):
        """Auto-save both sides.
        Naming priority:
          1. Text before #sh / # sh / #  sh on left file's first line
          2. Text before #sh / # sh / #  sh on right file's first line
          3. No pattern found → open single dialog for base name, then save both
        """
        if not self._left_fc or not self._right_fc:
            QMessageBox.warning(self, "Export", "No files loaded yet.")
            return

        # Try to extract base name from first line of left, then right
        base_name = (
            self._extract_sh_basename(self._left_fc.lines)
            or self._extract_sh_basename(self._right_fc.lines)
        )

        save_dir = os.path.dirname(self._left_fc.path)

        if base_name:
            # Auto-save immediately
            before_path = os.path.join(save_dir, f"{base_name}_before.txt")
            after_path  = os.path.join(save_dir, f"{base_name}_after.txt")
            self._write_lines(before_path, self._left_fc.lines,  self._left_fc.encoding)
            self._write_lines(after_path,  self._right_fc.lines, self._right_fc.encoding)
            QMessageBox.information(
                self, "Auto-save complete",
                f"Saved:\n• {before_path}\n• {after_path}"
            )
        else:
            # Fallback: ask for base name once, save both automatically
            base_name_input, _ = QFileDialog.getSaveFileName(
                self,
                "No #sh pattern found — enter base filename",
                os.path.join(save_dir, "output"),
                "Text files (*.txt);;All files (*.*)"
            )
            if not base_name_input:
                return
            # Strip extension if user typed one, we'll add our own suffixes
            base_clean, _ = os.path.splitext(base_name_input)
            before_path = base_clean + "_before.txt"
            after_path  = base_clean + "_after.txt"
            self._write_lines(before_path, self._left_fc.lines,  self._left_fc.encoding)
            self._write_lines(after_path,  self._right_fc.lines, self._right_fc.encoding)
            QMessageBox.information(
                self, "Saved",
                f"Saved:\n• {before_path}\n• {after_path}"
            )

    def _export_left_as(self):
        self._export_side_as("left")

    def _export_right_as(self):
        self._export_side_as("right")

    def _export_side_as(self, side: str):
        fc = self._left_fc if side == "left" else self._right_fc
        if not fc:
            QMessageBox.warning(self, "Export", f"No {side} file loaded.")
            return

        base, _ = os.path.splitext(fc.path)
        default_name = base + ("_before.txt" if side == "left" else "_after.txt")

        out_path, _ = QFileDialog.getSaveFileName(
            self, f"Save {side} file as…",
            default_name,
            "Text files (*.txt);;All files (*.*)"
        )
        if out_path:
            self._write_lines(out_path, fc.lines, fc.encoding)
            self._status.showMessage(f"Saved → {out_path}", 4000)

    @staticmethod
    def _write_lines(path: str, lines: list[str], encoding: str):
        with open(path, "w", encoding=encoding, errors="replace") as f:
            f.write("\n".join(lines))
            if lines:
                f.write("\n")

    # ------------------------------------------------------------------ Single-file preview

    def _run_single(self, path: str, encoding, side: str):
        """Load one file and show it in its pane without waiting for the other side."""
        thread = QThread()
        worker = SingleFileWorker(path, encoding, side)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(lambda fc, s: self._on_single_done(fc, s, thread))
        worker.error.connect(lambda msg: (thread.quit(), QMessageBox.critical(self, "Error", msg)))
        # Keep references so GC doesn't collect them
        self._single_thread = thread
        self._single_worker = worker
        thread.start()

    def _on_single_done(self, fc: FileContent, side: str, thread: QThread):
        thread.quit()
        # Store FileContent so export still works for the loaded side
        if side == "left":
            self._left_fc = fc
            self._status.update_left(fc.path, fc.encoding, fc.line_ending, len(fc.lines))
        else:
            self._right_fc = fc
            self._status.update_right(fc.path, fc.encoding, fc.line_ending, len(fc.lines))

        # Build a plain (no-diff) DiffResult so the pane can render the content
        plain = DiffResult()
        plain.left_lines       = fc.lines
        plain.right_lines      = fc.lines
        plain.left_line_numbers  = list(range(1, len(fc.lines) + 1))
        plain.right_line_numbers = list(range(1, len(fc.lines) + 1))
        # row_types and char_ranges stay empty → no diff colours

        pane = self._left_pane if side == "left" else self._right_pane
        pane.set_content(plain)

        total = len(fc.lines)
        self._minimap.set_diff_data([], total)
        self._minimap.set_viewport(0, pane.visible_row_count)

        name = os.path.basename(fc.path)
        self.setWindowTitle(f"FileDiff — {name}")
        self._status.update_diff_count(0)

    # ------------------------------------------------------------------ Diff pipeline

    def _run_diff(self):
        if not self._left_path or not self._right_path:
            return

        dlg = QProgressDialog("Loading and comparing files…", None, 0, 0, self)
        dlg.setWindowModality(Qt.WindowModality.WindowModal)
        dlg.setMinimumDuration(400)
        dlg.show()
        QApplication.processEvents()

        self._worker_thread = QThread()
        self._worker = DiffWorker(
            self._left_path, self._right_path,
            self._left_enc, self._right_enc,
            self._filter_engine,
        )
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(lambda lfc, rfc, dr: self._on_diff_done(lfc, rfc, dr, dlg))
        self._worker.error.connect(lambda msg: self._on_diff_error(msg, dlg))
        self._worker_thread.start()

    def _on_diff_done(self, lfc: FileContent, rfc: FileContent, result: DiffResult, dlg):
        dlg.close()
        self._worker_thread.quit()
        self._left_fc = lfc
        self._right_fc = rfc
        self._diff_result = result
        self._diff_row_idx = 0

        self._left_pane.set_content(result)
        self._right_pane.set_content(result)

        total_rows = len(result.left_lines)
        self._minimap.set_diff_data(result.diff_row_indices, total_rows)
        self._minimap.set_viewport(0, self._left_pane.visible_row_count)

        self._gutter.set_diff_data(
            result.left_row_types, result.right_row_types,
            result.left_lines, result.right_lines,
            self._left_pane._line_h,
        )
        self._gutter.set_scroll(0, self._left_pane.visible_row_count, 0)

        self._status.update_left(lfc.path, lfc.encoding, lfc.line_ending, len(lfc.lines))
        self._status.update_right(rfc.path, rfc.encoding, rfc.line_ending, len(rfc.lines))
        self._status.update_diff_count(len(result.diff_row_indices))

        self.setWindowTitle(
            f"FileDiff — {os.path.basename(lfc.path)} ↔ {os.path.basename(rfc.path)}"
        )

        if result.diff_row_indices:
            self._jump_to_row(result.diff_row_indices[0])

    def _on_diff_error(self, msg: str, dlg):
        dlg.close()
        if self._worker_thread:
            self._worker_thread.quit()
        QMessageBox.critical(self, "Error", msg)

    # ------------------------------------------------------------------ Scroll sync

    def _sync_scroll_from_left(self, value: int):
        self._right_pane.set_vscroll(value)
        self._update_minimap_viewport()
        self._update_gutter_scroll()

    def _sync_scroll_from_right(self, value: int):
        self._left_pane.set_vscroll(value)
        self._update_minimap_viewport()
        self._update_gutter_scroll()

    def _update_minimap_viewport(self):
        self._minimap.set_viewport(
            self._left_pane.first_visible_row,
            self._left_pane.visible_row_count,
        )

    def _update_gutter_scroll(self):
        first = self._left_pane.first_visible_row
        count = self._left_pane.visible_row_count
        v_off = self._left_pane.verticalScrollBar().value()
        self._gutter.set_scroll(first, count, v_off % max(1, self._left_pane._line_h))

    def _on_minimap_scroll(self, row: int):
        self._left_pane.scroll_to_row(row)
        self._right_pane.scroll_to_row(row)
        self._update_minimap_viewport()
        self._update_gutter_scroll()

    # ------------------------------------------------------------------ Navigation

    def _jump_to_row(self, row: int):
        self._left_pane.scroll_to_row(row)
        self._right_pane.scroll_to_row(row)
        self._update_minimap_viewport()
        self._update_gutter_scroll()

    def _next_diff(self):
        if not self._diff_result or not self._diff_result.diff_row_indices:
            return
        rows = self._diff_result.diff_row_indices
        cur = self._left_pane.first_visible_row
        for row in rows:
            if row > cur:
                self._jump_to_row(row)
                return
        self._jump_to_row(rows[0])

    def _prev_diff(self):
        if not self._diff_result or not self._diff_result.diff_row_indices:
            return
        rows = self._diff_result.diff_row_indices
        cur = self._left_pane.first_visible_row
        for row in reversed(rows):
            if row < cur:
                self._jump_to_row(row)
                return
        self._jump_to_row(rows[-1])

    # ------------------------------------------------------------------ Encoding / filter

    def _on_encoding_changed(self, side: str, encoding: str):
        if side == "left":
            self._left_enc = encoding
            if self._right_path:
                self._run_diff()
            elif self._left_path:
                self._run_single(self._left_path, encoding, "left")
        else:
            self._right_enc = encoding
            if self._left_path:
                self._run_diff()
            elif self._right_path:
                self._run_single(self._right_path, encoding, "right")

    def _on_filter_changed(self, pattern: str, is_regex: bool):
        self._filter_engine.compile(pattern, is_regex)
        self._run_diff()

    def _on_copy_ltr(self, row: int):
        pass

    def _on_copy_rtl(self, row: int):
        pass

    # ------------------------------------------------------------------ Search

    def _open_search(self):
        self._search_bar.focus()

    def _close_search(self):
        self._left_pane.clear_search()
        self._right_pane.clear_search()
        self._search_rows.clear()
        self._search_idx = -1
        self._search_bar.clear_count()

    def _on_search_requested(self, pattern: str, is_regex: bool, case_sensitive: bool):
        if not pattern:
            self._close_search()
            return

        l_count = self._left_pane.set_search(pattern, is_regex, case_sensitive)
        r_count = self._right_pane.set_search(pattern, is_regex, case_sensitive)

        # Combine unique match rows from both panes for navigation
        rows = set(r for r, _, _ in self._left_pane._search_all)
        rows |= set(r for r, _, _ in self._right_pane._search_all)
        self._search_rows = sorted(rows)
        self._search_idx  = -1

        total = l_count + r_count
        self._search_bar.update_count(0, total)

        if self._search_rows:
            self._navigate_search(+1)

    def _navigate_search(self, direction: int):
        if not self._search_rows:
            return

        self._search_idx = (self._search_idx + direction) % len(self._search_rows)
        row = self._search_rows[self._search_idx]

        self._left_pane.highlight_search_row(row)
        self._right_pane.highlight_search_row(row)
        self._jump_to_row(row)

        current_match = self._search_idx + 1
        total = len(self._left_pane._search_all) + len(self._right_pane._search_all)
        self._search_bar.update_count(current_match, total)

    # ------------------------------------------------------------------ Font scale

    def _on_font_size_changed(self, size: int):
        self._left_pane.set_font_size(size)
        self._right_pane.set_font_size(size)
        self._update_gutter_scroll()

    def _font_increase(self):
        new_size = self._left_pane.font_size + 1
        self._status.set_font_size(new_size)

    def _font_decrease(self):
        new_size = self._left_pane.font_size - 1
        self._status.set_font_size(new_size)

    def _font_reset(self):
        from app.widgets.virtual_text_pane import BASE_FONT_SIZE
        self._status.set_font_size(BASE_FONT_SIZE)

    # ------------------------------------------------------------------ About / Shortcuts

    def _show_shortcuts(self):
        dlg = ShortcutsDialog(self)
        dlg.exec()

    def _show_about(self):
        dlg = AboutDialog(self)
        dlg.exec()

    # ------------------------------------------------------------------ Theme

    def _toggle_theme(self):
        themes.toggle()
        self._apply_theme()

    def _apply_theme(self):
        t = themes.current()
        bg = t["bg"]
        fg = t["text"]
        toolbar_bg = t["toolbar_bg"]

        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background-color: {bg}; color: {fg}; }}
            QMenuBar {{ background-color: {toolbar_bg}; color: {fg}; }}
            QMenuBar::item:selected {{ background-color: {t["selection_bg"]}; }}
            QMenu {{ background-color: {toolbar_bg}; color: {fg}; }}
            QMenu::item:selected {{ background-color: {t["selection_bg"]}; }}
            QStatusBar {{ background-color: {toolbar_bg}; color: {fg}; }}
            QLabel {{ color: {fg}; }}
            QLineEdit {{ background-color: {bg}; color: {fg}; border: 1px solid {t["gutter_border"]}; }}
            QComboBox {{ background-color: {bg}; color: {fg}; border: 1px solid {t["gutter_border"]}; }}
            QCheckBox {{ color: {fg}; }}
            QSplitter::handle {{ background: {t["gutter_border"]}; }}
        """)

        self._left_pane.apply_theme()
        self._right_pane.apply_theme()
        self._browser.apply_theme()
        self._gutter.apply_theme()
        self._minimap.update()
