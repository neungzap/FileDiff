from __future__ import annotations
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QCheckBox, QPushButton
from PyQt6.QtCore import pyqtSignal, Qt


class FilterBar(QWidget):
    filter_changed = pyqtSignal(str, bool)  # pattern, is_regex  (only on Apply/Enter)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(6)

        label = QLabel("Ignore pattern:")
        label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(label)

        self._edit = QLineEdit()
        self._edit.setPlaceholderText(r"e.g. \d{2}:\d{2}:\d{2}  (timestamps)  — press Enter or Apply")
        self._edit.setMaximumWidth(360)
        self._edit.returnPressed.connect(self._emit)   # Enter key
        layout.addWidget(self._edit)

        self._regex_cb = QCheckBox("Regex")
        self._regex_cb.setChecked(True)
        layout.addWidget(self._regex_cb)

        btn = QPushButton("Apply")
        btn.setFixedWidth(56)
        btn.setToolTip("Apply ignore pattern (Enter)")
        btn.clicked.connect(self._emit)
        layout.addWidget(btn)

        layout.addStretch()

    def _emit(self):
        self.filter_changed.emit(self._edit.text(), self._regex_cb.isChecked())

    def clear(self):
        self._edit.clear()
