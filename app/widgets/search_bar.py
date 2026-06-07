from __future__ import annotations
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QCheckBox, QPushButton
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QKeySequence, QShortcut


class SearchBar(QWidget):
    search_requested = pyqtSignal(str, bool, bool)  # pattern, is_regex, case_sensitive
    navigate         = pyqtSignal(int)               # +1 next, -1 prev
    closed           = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(6)

        layout.addWidget(QLabel("🔍 Find:"))

        self._edit = QLineEdit()
        self._edit.setPlaceholderText("Search in both panes…")
        self._edit.setMaximumWidth(300)
        self._edit.returnPressed.connect(lambda: self.navigate.emit(+1))
        self._edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._edit)

        self._regex_cb = QCheckBox("Regex")
        self._regex_cb.stateChanged.connect(self._emit)
        layout.addWidget(self._regex_cb)

        self._case_cb = QCheckBox("Case")
        self._case_cb.setToolTip("Case-sensitive search")
        self._case_cb.stateChanged.connect(self._emit)
        layout.addWidget(self._case_cb)

        btn_prev = QPushButton("▲")
        btn_prev.setFixedWidth(28)
        btn_prev.setToolTip("Previous match  (Shift+Enter)")
        btn_prev.clicked.connect(lambda: self.navigate.emit(-1))
        layout.addWidget(btn_prev)

        btn_next = QPushButton("▼")
        btn_next.setFixedWidth(28)
        btn_next.setToolTip("Next match  (Enter)")
        btn_next.clicked.connect(lambda: self.navigate.emit(+1))
        layout.addWidget(btn_next)

        self._count_label = QLabel("")
        self._count_label.setMinimumWidth(80)
        layout.addWidget(self._count_label)

        btn_close = QPushButton("✕")
        btn_close.setFixedWidth(28)
        btn_close.setToolTip("Close search  (Esc)")
        btn_close.clicked.connect(self._close)
        layout.addWidget(btn_close)

        layout.addStretch()

        # Shift+Enter → previous
        sc = QShortcut(QKeySequence("Shift+Return"), self)
        sc.activated.connect(lambda: self.navigate.emit(-1))

    # ── Public ────────────────────────────────────────────────────────────

    def focus(self):
        self._edit.setFocus()
        self._edit.selectAll()

    def update_count(self, current: int, total: int):
        if total == 0:
            self._count_label.setText("No match")
            self._count_label.setStyleSheet("color: #CC0000;")
        else:
            self._count_label.setText(f"{current} / {total}")
            self._count_label.setStyleSheet("")

    def clear_count(self):
        self._count_label.setText("")

    # ── Private ───────────────────────────────────────────────────────────

    def _on_text_changed(self, text: str):
        self._emit()

    def _emit(self):
        self.search_requested.emit(
            self._edit.text(),
            self._regex_cb.isChecked(),
            self._case_cb.isChecked(),
        )

    def _close(self):
        self._edit.clear()
        self._emit()
        self.closed.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._close()
        else:
            super().keyPressEvent(event)
