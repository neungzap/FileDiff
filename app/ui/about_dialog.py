from __future__ import annotations
import sys
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame,
)
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt
from app.ui import themes

ICON_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "icon_1024.png")


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About FileDiff")
        self.setFixedSize(400, 560)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(0)

        # ── App icon ──────────────────────────────────────────────────────
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pix_path = os.path.abspath(ICON_PATH)
        if os.path.exists(pix_path):
            pix = QPixmap(pix_path).scaled(
                80, 80,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_label.setPixmap(pix)
        layout.addWidget(icon_label)
        layout.addSpacing(12)

        # ── App name ──────────────────────────────────────────────────────
        name_label = QLabel("FileDiff")
        name_font = QFont()
        name_font.setPointSize(22)
        name_font.setBold(True)
        name_label.setFont(name_font)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

        ver_label = QLabel("Version 1.0.1")
        ver_font = QFont()
        ver_font.setPointSize(11)
        ver_label.setFont(ver_font)
        ver_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver_label)
        layout.addSpacing(6)

        desc_label = QLabel(
            "A fast, lightweight file diff & comparison tool\n"
            "with syntax-aware highlighting, encoding detection,\n"
            "and regex filter support. Inspired by Beyond Compare."
        )
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_font = QFont()
        desc_font.setPointSize(10)
        desc_label.setFont(desc_font)
        layout.addWidget(desc_label)
        layout.addSpacing(14)

        layout.addWidget(self._divider())
        layout.addSpacing(14)

        # ── Developer section ─────────────────────────────────────────────
        dev_title = QLabel("Developer")
        dev_title_font = QFont()
        dev_title_font.setPointSize(10)
        dev_title_font.setBold(True)
        dev_title.setFont(dev_title_font)
        layout.addWidget(dev_title)
        layout.addSpacing(6)

        dev_name = QLabel("Sittichai Taykum")
        dev_name_font = QFont()
        dev_name_font.setPointSize(13)
        dev_name_font.setBold(True)
        dev_name.setFont(dev_name_font)
        layout.addWidget(dev_name)
        layout.addSpacing(4)

        # CCIE badge
        ccie_label = QLabel("  CCIE #67220")
        ccie_font = QFont()
        ccie_font.setPointSize(11)
        ccie_font.setBold(True)
        ccie_label.setFont(ccie_font)
        ccie_label.setStyleSheet(
            "color: white; background-color: #1A5276;"
            "border-radius: 6px; padding: 2px 10px;"
        )
        ccie_label.setFixedWidth(130)
        layout.addWidget(ccie_label)
        layout.addSpacing(6)

        # Email (selectable plain text)
        email_label = QLabel("neung983@hotmail.com")
        email_font = QFont()
        email_font.setPointSize(11)
        email_label.setFont(email_font)
        email_label.setStyleSheet(f"color: {themes.current()['text']}; background: transparent;")
        email_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        email_label.setCursor(Qt.CursorShape.IBeamCursor)
        email_label.setToolTip("Click and drag to select · Ctrl+C to copy")
        layout.addWidget(email_label)
        layout.addSpacing(6)

        fb_label = QLabel()
        fb_font = QFont()
        fb_font.setPointSize(11)
        fb_label.setFont(fb_font)
        fb_label.setOpenExternalLinks(True)
        fb_label.setText('<a href="https://www.facebook.com/neung.zap" style="color:#1877F2; text-decoration:none;">📘 facebook.com/neung.zap</a>')
        fb_label.setTextFormat(Qt.TextFormat.RichText)
        fb_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        fb_label.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(fb_label)
        layout.addSpacing(4)

        # GitHub link
        gh_label = QLabel()
        gh_font = QFont()
        gh_font.setPointSize(11)
        gh_label.setFont(gh_font)
        gh_label.setOpenExternalLinks(True)
        gh_label.setText('<a href="https://github.com/neungzap/FileDiff" style="color:#0969DA; text-decoration:none;">🐙 github.com/neungzap/FileDiff</a>')
        gh_label.setTextFormat(Qt.TextFormat.RichText)
        gh_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        gh_label.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(gh_label)
        layout.addSpacing(14)

        layout.addWidget(self._divider())
        layout.addSpacing(14)

        # ── Built with ────────────────────────────────────────────────────
        built_title = QLabel("Built with")
        built_title_font = QFont()
        built_title_font.setPointSize(10)
        built_title_font.setBold(True)
        built_title.setFont(built_title_font)
        layout.addWidget(built_title)
        layout.addSpacing(4)

        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        built_label = QLabel(f"Python {py_ver}  •  PyQt6  •  charset-normalizer")
        built_label.setFont(QFont("", 10))
        layout.addWidget(built_label)
        layout.addSpacing(16)

        # ── License ───────────────────────────────────────────────────────
        lic_label = QLabel()
        lic_label.setOpenExternalLinks(True)
        lic_label.setText(
            '<a href="https://opensource.org/licenses/MIT" '
            'style="color:#2E7D32; text-decoration:none;">'
            '⚖️ MIT License — Open Source</a>'
        )
        lic_label.setTextFormat(Qt.TextFormat.RichText)
        lic_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        lic_label.setCursor(Qt.CursorShape.PointingHandCursor)
        lic_label.setFont(QFont("", 10))
        lic_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lic_label)
        layout.addSpacing(4)

        # ── Copyright ─────────────────────────────────────────────────────
        copy_label = QLabel("© 2026 Sittichai Taykum")
        copy_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copy_font = QFont()
        copy_font.setPointSize(9)
        copy_label.setFont(copy_font)
        layout.addWidget(copy_label)

        layout.addStretch()

        # ── Close button ──────────────────────────────────────────────────
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
            QFrame   {{ color: {bdr}; }}
            QPushButton {{
                background-color: {sel}; color: {fg};
                border: 1px solid {bdr}; border-radius: 5px;
                padding: 4px 12px; font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {t["minimap_viewport"]}; }}
        """)
