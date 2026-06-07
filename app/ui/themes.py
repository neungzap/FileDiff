from PyQt6.QtGui import QColor

THEMES = {
    "light": {
        "search_match":   "#FFD700",
        "search_current": "#FF8C00",
        "bg": "#FFFFFF",
        "line_num_bg": "#F5F5F5",
        "line_num_fg": "#888888",
        "text": "#000000",
        "added_bg": "#E6FFED",
        "deleted_bg": "#FFEEF0",
        "modified_bg": "#FFF8C5",
        "char_diff_bg": "#FF9999",
        "phantom_bg": "#F0F0F0",
        "gutter_bg": "#EBEBEB",
        "gutter_border": "#CCCCCC",
        "minimap_bg": "#F8F8F8",
        "minimap_diff": "#FF4444",
        "minimap_viewport": "#0000FF",
        "selection_bg": "#ADD6FF",
        "toolbar_bg": "#F3F3F3",
        "current_line": "#F8F8F8",
    },
    "dark": {
        "search_match":   "#B8860B",
        "search_current": "#FF8C00",
        "bg": "#1E1E1E",
        "line_num_bg": "#252526",
        "line_num_fg": "#858585",
        "text": "#D4D4D4",
        "added_bg": "#1A3A1A",
        "deleted_bg": "#3A1A1A",
        "modified_bg": "#3A3000",
        "char_diff_bg": "#8B1A1A",
        "phantom_bg": "#2A2A2A",
        "gutter_bg": "#2D2D2D",
        "gutter_border": "#3C3C3C",
        "minimap_bg": "#252526",
        "minimap_diff": "#FF5555",
        "minimap_viewport": "#4444AA",
        "selection_bg": "#264F78",
        "toolbar_bg": "#252526",
        "current_line": "#2A2A2A",
    },
}

_current = "light"


def current() -> dict:
    return THEMES[_current]


def set_theme(name: str):
    global _current
    if name in THEMES:
        _current = name


def toggle() -> str:
    global _current
    _current = "dark" if _current == "light" else "light"
    return _current


def color(key: str) -> QColor:
    return QColor(current()[key])
