from __future__ import annotations
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTreeView, QFileDialog, QSizePolicy,
    QAbstractItemView, QMenu, QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QDir, QMimeData, QUrl
from PyQt6.QtGui import QFileSystemModel, QAction, QDrag
from app.ui import themes

# QFileSystemModel column indices
COL_NAME = 0
COL_SIZE = 1
COL_TYPE = 2
COL_DATE = 3

SORT_OPTIONS = [
    ("Name  A→Z",    COL_NAME, Qt.SortOrder.AscendingOrder),
    ("Name  Z→A",    COL_NAME, Qt.SortOrder.DescendingOrder),
    ("Date  Newest", COL_DATE, Qt.SortOrder.DescendingOrder),
    ("Date  Oldest", COL_DATE, Qt.SortOrder.AscendingOrder),
    ("Size  Large",  COL_SIZE, Qt.SortOrder.DescendingOrder),
    ("Size  Small",  COL_SIZE, Qt.SortOrder.AscendingOrder),
]


class _DragTreeView(QTreeView):
    """QTreeView that starts a URL drag when the user drags a file row."""

    def __init__(self, model: QFileSystemModel, parent=None):
        super().__init__(parent)
        self._fs_model = model
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)

    def startDrag(self, supported_actions):
        idx = self.currentIndex()
        if not idx.isValid():
            return
        path = self._fs_model.filePath(idx)
        if not os.path.isfile(path):
            return
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(path)])
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)


class FileBrowserPanel(QWidget):
    """Single sidebar file-browser. Emits which pane to load into."""
    open_as_left  = pyqtSignal(str)
    open_as_right = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(180)
        self.setMaximumWidth(380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Top toolbar (folder nav) ──────────────────────────────────────
        toolbar = QWidget()
        toolbar.setFixedHeight(32)
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(4, 2, 4, 2)
        tb.setSpacing(3)

        btn_open = QPushButton("📂")
        btn_open.setFixedWidth(28)
        btn_open.setToolTip("Open folder")
        btn_open.clicked.connect(self._on_open_folder)
        tb.addWidget(btn_open)

        btn_up = QPushButton("⬆")
        btn_up.setFixedWidth(28)
        btn_up.setToolTip("Parent folder")
        btn_up.clicked.connect(self._go_up)
        tb.addWidget(btn_up)

        self._path_label = QLabel("~")
        self._path_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._path_label.setStyleSheet("font-size: 11px;")
        tb.addWidget(self._path_label)

        layout.addWidget(toolbar)

        # ── Sort bar ──────────────────────────────────────────────────────
        sort_row = QWidget()
        sort_row.setFixedHeight(28)
        sr = QHBoxLayout(sort_row)
        sr.setContentsMargins(4, 1, 4, 1)
        sr.setSpacing(4)

        sort_lbl = QLabel("Sort:")
        sort_lbl.setStyleSheet("font-size: 11px;")
        sr.addWidget(sort_lbl)

        self._sort_combo = QComboBox()
        self._sort_combo.setStyleSheet("font-size: 11px;")
        for label, _, _ in SORT_OPTIONS:
            self._sort_combo.addItem(label)
        self._sort_combo.currentIndexChanged.connect(self._apply_sort)
        sr.addWidget(self._sort_combo, 1)

        layout.addWidget(sort_row)

        # ── Load-pane buttons ─────────────────────────────────────────────
        btn_row = QWidget()
        btn_row.setFixedHeight(30)
        br = QHBoxLayout(btn_row)
        br.setContentsMargins(4, 2, 4, 2)
        br.setSpacing(4)

        self._btn_left = QPushButton("◀ Open Left")
        self._btn_left.setToolTip("Load selected file → LEFT pane")
        self._btn_left.clicked.connect(self._load_selected_left)
        br.addWidget(self._btn_left)

        self._btn_right = QPushButton("Open Right ▶")
        self._btn_right.setToolTip("Load selected file → RIGHT pane")
        self._btn_right.clicked.connect(self._load_selected_right)
        br.addWidget(self._btn_right)

        layout.addWidget(btn_row)

        # ── Drag hint label ───────────────────────────────────────────────
        hint = QLabel("  ↕ drag file to a pane")
        hint.setStyleSheet("font-size: 10px; color: gray;")
        layout.addWidget(hint)

        # ── File-system model + tree ──────────────────────────────────────
        self._root_path = QDir.homePath()
        self._model = QFileSystemModel()
        self._model.setRootPath(self._root_path)
        self._model.setFilter(
            QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)

        self._tree = _DragTreeView(self._model)
        self._tree.setModel(self._model)
        self._tree.setRootIndex(self._model.index(self._root_path))
        self._tree.setAnimated(True)
        self._tree.setIndentation(14)
        self._tree.setSortingEnabled(True)
        self._tree.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self._tree.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tree.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(
            self._show_context_menu)

        # Show Name + Date only; hide Size and Type
        self._tree.setColumnHidden(COL_SIZE, True)
        self._tree.setColumnHidden(COL_TYPE, True)
        self._tree.header().setVisible(True)
        self._tree.header().setStretchLastSection(False)
        self._tree.header().setSectionResizeMode(
            COL_NAME, self._tree.header().ResizeMode.Stretch)
        self._tree.header().setSectionResizeMode(
            COL_DATE, self._tree.header().ResizeMode.ResizeToContents)

        self._tree.doubleClicked.connect(self._on_double_click)

        # Apply default sort
        self._apply_sort(0)

        layout.addWidget(self._tree, 1)

        self._set_root(QDir.homePath())
        self.apply_theme()

    # ── Public ────────────────────────────────────────────────────────────

    def set_root(self, path: str):
        self._set_root(path)

    def apply_theme(self):
        t = themes.current()
        bg     = t["line_num_bg"]
        fg     = t["text"]
        sel    = t["selection_bg"]
        bdr    = t["gutter_border"]
        btn_bg = t["bg"]
        self.setStyleSheet(f"""
            QWidget   {{ background-color: {bg}; color: {fg}; }}
            QTreeView {{ background-color: {bg}; color: {fg};
                        border: none; font-size: 12px; }}
            QTreeView::item:selected {{ background-color: {sel}; color: {fg}; }}
            QTreeView::item:hover    {{ background-color: {sel}; }}
            QHeaderView::section     {{ background-color: {btn_bg};
                                        color: {fg}; border: none;
                                        font-size: 11px; padding: 2px; }}
            QPushButton {{ background-color: {btn_bg}; color: {fg};
                          border: 1px solid {bdr}; border-radius: 3px;
                          padding: 2px 5px; font-size: 11px; }}
            QPushButton:hover {{ background-color: {sel}; }}
            QComboBox   {{ background-color: {btn_bg}; color: {fg};
                          border: 1px solid {bdr}; border-radius: 3px; }}
            QLabel      {{ color: {fg}; }}
            QMenu       {{ background-color: {btn_bg}; color: {fg}; }}
            QMenu::item:selected {{ background-color: {sel}; }}
        """)

    # ── Private ───────────────────────────────────────────────────────────

    def _set_root(self, path: str):
        self._root_path = path
        self._model.setRootPath(path)
        self._tree.setRootIndex(self._model.index(path))
        label = os.path.basename(path) or path
        self._path_label.setText(label)
        self._path_label.setToolTip(path)

    def _apply_sort(self, index: int):
        _, col, order = SORT_OPTIONS[index]
        self._tree.sortByColumn(col, order)

    def _selected_path(self) -> str | None:
        idx = self._tree.currentIndex()
        if not idx.isValid():
            return None
        path = self._model.filePath(idx)
        return path if os.path.isfile(path) else None

    def _load_selected_left(self):
        path = self._selected_path()
        if path:
            self.open_as_left.emit(path)

    def _load_selected_right(self):
        path = self._selected_path()
        if path:
            self.open_as_right.emit(path)

    def _on_open_folder(self):
        path = QFileDialog.getExistingDirectory(
            self, "Open Folder", self._root_path)
        if path:
            self._set_root(path)

    def _go_up(self):
        parent = os.path.dirname(self._root_path)
        if parent and parent != self._root_path:
            self._set_root(parent)

    def _on_double_click(self, index):
        path = self._model.filePath(index)
        if os.path.isdir(path):
            self._set_root(path)
        elif os.path.isfile(path):
            self.open_as_left.emit(path)

    def _show_context_menu(self, pos):
        index = self._tree.indexAt(pos)
        if not index.isValid():
            return
        path = self._model.filePath(index)
        if not os.path.isfile(path):
            return
        menu = QMenu(self)
        act_l = QAction("◀  Open as Left Pane", self)
        act_r = QAction("Open as Right Pane  ▶", self)
        act_l.triggered.connect(lambda: self.open_as_left.emit(path))
        act_r.triggered.connect(lambda: self.open_as_right.emit(path))
        menu.addAction(act_l)
        menu.addAction(act_r)
        menu.exec(self._tree.viewport().mapToGlobal(pos))
