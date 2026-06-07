from __future__ import annotations
from PyQt6.QtWidgets import QStatusBar, QLabel, QComboBox, QWidget, QHBoxLayout, QPushButton, QFontComboBox
from PyQt6.QtGui import QFont
from PyQt6.QtCore import pyqtSignal

COMMON_ENCODINGS = [
    "utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be",
    "latin-1", "cp1252", "cp874", "cp1250", "cp1251",
    "ascii", "iso-8859-1", "iso-8859-11",
]

BASE_FONT_SIZE = 11


class PaneStatusWidget(QWidget):
    encoding_changed = pyqtSignal(str, str)

    def __init__(self, side: str, parent=None):
        super().__init__(parent)
        self._side = side
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)

        self._path_label = QLabel("No file")
        self._path_label.setMaximumWidth(300)
        layout.addWidget(self._path_label)

        self._enc_combo = QComboBox()
        self._enc_combo.addItems(COMMON_ENCODINGS)
        self._enc_combo.setFixedWidth(100)
        self._enc_combo.currentTextChanged.connect(self._on_enc_changed)
        layout.addWidget(self._enc_combo)

        self._le_label = QLabel("")
        layout.addWidget(self._le_label)

        self._lines_label = QLabel("")
        layout.addWidget(self._lines_label)

    def update_info(self, path: str, encoding: str, line_ending: str, line_count: int):
        import os
        self._path_label.setText(os.path.basename(path))
        self._path_label.setToolTip(path)
        self._enc_combo.blockSignals(True)
        idx = self._enc_combo.findText(encoding.lower())
        if idx >= 0:
            self._enc_combo.setCurrentIndex(idx)
        else:
            self._enc_combo.insertItem(0, encoding.lower())
            self._enc_combo.setCurrentIndex(0)
        self._enc_combo.blockSignals(False)
        self._le_label.setText(f"[{line_ending}]")
        self._lines_label.setText(f"{line_count} lines")

    def _on_enc_changed(self, enc: str):
        self.encoding_changed.emit(self._side, enc)


class FontScaleWidget(QWidget):
    scale_changed = pyqtSignal(int)    # new absolute font size in pt
    family_changed = pyqtSignal(str)   # new font family name (empty = system default)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._size = BASE_FONT_SIZE
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(4)

        # Font family picker — monospace fonts only
        self._family_combo = QFontComboBox()
        self._family_combo.setFontFilters(QFontComboBox.FontFilter.MonospacedFonts)
        self._family_combo.setFixedWidth(160)
        self._family_combo.setToolTip("Font family")
        self._family_combo.currentFontChanged.connect(self._on_family_changed)
        layout.addWidget(self._family_combo)

        btn_minus = QPushButton("A-")
        btn_minus.setFixedWidth(30)
        btn_minus.setToolTip("Decrease font size  (Ctrl+-)")
        btn_minus.clicked.connect(self._decrease)
        layout.addWidget(btn_minus)

        self._pct_label = QLabel("100%")
        self._pct_label.setFixedWidth(42)
        self._pct_label.setToolTip("Font size relative to default")
        layout.addWidget(self._pct_label)

        btn_plus = QPushButton("A+")
        btn_plus.setFixedWidth(30)
        btn_plus.setToolTip("Increase font size  (Ctrl+=)")
        btn_plus.clicked.connect(self._increase)
        layout.addWidget(btn_plus)

    def _on_family_changed(self, font: QFont):
        self.family_changed.emit(font.family())

    def _increase(self):
        self._set(self._size + 1)

    def _decrease(self):
        self._set(self._size - 1)

    def _set(self, size: int):
        from app.widgets.virtual_text_pane import MIN_FONT_SIZE, MAX_FONT_SIZE
        self._size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, size))
        pct = int(self._size / BASE_FONT_SIZE * 100)
        self._pct_label.setText(f"{pct}%")
        self.scale_changed.emit(self._size)

    def set_size(self, size: int):
        self._set(size)


class AppStatusBar(QStatusBar):
    encoding_changed = pyqtSignal(str, str)
    font_size_changed = pyqtSignal(int)
    font_family_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._left  = PaneStatusWidget("left")
        self._right = PaneStatusWidget("right")
        self._diff_label  = QLabel("")
        self._font_scale  = FontScaleWidget()

        self.addWidget(self._left, 1)
        self.addPermanentWidget(self._diff_label)
        self.addPermanentWidget(self._font_scale)
        self.addPermanentWidget(self._right, 1)

        self._left.encoding_changed.connect(self.encoding_changed)
        self._right.encoding_changed.connect(self.encoding_changed)
        self._font_scale.scale_changed.connect(self.font_size_changed)
        self._font_scale.family_changed.connect(self.font_family_changed)

    def update_left(self, path, encoding, line_ending, line_count):
        self._left.update_info(path, encoding, line_ending, line_count)

    def update_right(self, path, encoding, line_ending, line_count):
        self._right.update_info(path, encoding, line_ending, line_count)

    def update_diff_count(self, count: int):
        self._diff_label.setText(f"{count} differences" if count else "Files identical")

    def set_font_size(self, size: int):
        self._font_scale.set_size(size)
