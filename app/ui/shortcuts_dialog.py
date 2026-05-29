from __future__ import annotations
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from app.ui import themes

SECTIONS = [
    ("File", [
        ("Ctrl+L",       "Open Left File"),
        ("Ctrl+R",       "Open Right File"),
        ("Ctrl+E",       "Export Both (auto-name)"),
        ("Ctrl+Shift+L", "Save Left As…"),
        ("Ctrl+Shift+R", "Save Right As…"),
        ("Cmd+Q",        "Quit"),
    ]),
    ("Navigate", [
        ("F7", "Previous Diff"),
        ("F8", "Next Diff"),
    ]),
    ("Search", [
        ("Ctrl+F",       "Focus Search Bar"),
        ("Enter",        "Next Match"),
        ("Shift+Enter",  "Previous Match"),
        ("Esc",          "Clear Search"),
    ]),
    ("View", [
        ("Ctrl+T", "Toggle Light / Dark Theme"),
        ("Ctrl+B", "Toggle File Browser"),
        ("Ctrl+=", "Zoom In"),
        ("Ctrl+-", "Zoom Out"),
        ("Ctrl+0", "Reset Zoom"),
    ]),
]


class ShortcutsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.setFixedSize(420, 520)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(0)

        title = QLabel("Keyboard Shortcuts")
        tf = QFont()
        tf.setPointSize(16)
        tf.setBold(True)
        title.setFont(tf)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addSpacing(16)

        for section_name, rows in SECTIONS:
            layout.addWidget(self._section_header(section_name))
            layout.addSpacing(4)
            for key, desc in rows:
                layout.addWidget(self._row(key, desc))
            layout.addSpacing(10)
            layout.addWidget(self._divider())
            layout.addSpacing(10)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("  Close  ")
        close_btn.setFixedWidth(90)
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._apply_theme()

    def _section_header(self, text: str) -> QLabel:
        lbl = QLabel(text)
        f = QFont()
        f.setPointSize(10)
        f.setBold(True)
        lbl.setFont(f)
        return lbl

    def _row(self, key: str, desc: str) -> QWidget:
        from PyQt6.QtWidgets import QWidget
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 1, 0, 1)

        key_lbl = QLabel(key)
        key_font = QFont("Menlo, Courier New, monospace")
        key_font.setPointSize(10)
        key_lbl.setFont(key_font)
        key_lbl.setFixedWidth(130)
        key_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        desc_lbl = QLabel(desc)
        desc_font = QFont()
        desc_font.setPointSize(10)
        desc_lbl.setFont(desc_font)

        h.addWidget(key_lbl)
        h.addWidget(desc_lbl)
        h.addStretch()
        return w

    def _divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line

    def _apply_theme(self):
        t = themes.current()
        bg = t["bg"]
        fg = t["text"]
        bdr = t["gutter_border"]
        sel = t["selection_bg"]
        self.setStyleSheet(f"""
            QDialog  {{ background-color: {bg}; color: {fg}; }}
            QLabel   {{ color: {fg}; background: transparent; }}
            QWidget  {{ background-color: {bg}; }}
            QFrame   {{ color: {bdr}; }}
            QPushButton {{
                background-color: {sel}; color: {fg};
                border: 1px solid {bdr}; border-radius: 5px;
                padding: 4px 12px; font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {t["minimap_viewport"]}; }}
        """)
