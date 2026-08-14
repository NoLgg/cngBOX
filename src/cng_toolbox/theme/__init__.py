"""theme — 游戏化主题：配色方案、QSS 生成、图标。

主题结构：
- 深色游戏化基调（#1a1d24 系背景 + 高饱和主色）
- 三种强调色方案：teal（青绿，默认）/ orange（橙黄）/ violet（紫罗兰）
"""

from __future__ import annotations

ACCENTS: dict[str, dict[str, str]] = {
    "teal": {
        "primary": "#2dd4bf",
        "primary_dim": "#14b8a6",
        "on_primary": "#0b1220",
    },
    "orange": {
        "primary": "#fbbf24",
        "primary_dim": "#f59e0b",
        "on_primary": "#1c1005",
    },
    "violet": {
        "primary": "#a78bfa",
        "primary_dim": "#8b5cf6",
        "on_primary": "#140a2e",
    },
}

BASE = {
    "bg": "#1a1d24",
    "bg_alt": "#22262f",
    "bg_card": "#262b36",
    "bg_hover": "#2f3542",
    "border": "#3a4150",
    "text": "#e8ecf3",
    "text_dim": "#9aa4b5",
    "text_strong": "#ffffff",
    "danger": "#f87171",
    "ok": "#4ade80",
}


def build_qss(accent: str = "teal") -> str:
    """生成全局 QSS（基于指定强调色）。"""
    a = ACCENTS.get(accent, ACCENTS["teal"])
    b = BASE

    return f"""
* {{
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
    color: {b['text']};
}}
QMainWindow, QDialog {{
    background-color: {b['bg']};
}}
QWidget#Card {{
    background-color: {b['bg_card']};
    border: 1px solid {b['border']};
    border-radius: 12px;
}}
QWidget#Card:hover {{
    background-color: {b['bg_hover']};
    border-color: {a['primary']};
}}
QLabel#CardTitle {{
    color: {b['text_strong']};
    font-size: 15px;
    font-weight: bold;
}}
QLabel#CardIcon {{
    font-size: 34px;
}}
QLabel#CardDesc {{
    color: {b['text_dim']};
    font-size: 12px;
}}
QLabel#CardHotkey {{
    color: {a['primary']};
    font-size: 11px;
    background-color: {b['bg_alt']};
    border-radius: 8px;
    padding: 2px 8px;
}}
QPushButton {{
    background-color: {b['bg_alt']};
    border: 1px solid {b['border']};
    border-radius: 8px;
    padding: 6px 14px;
}}
QPushButton:hover {{
    border-color: {a['primary']};
    color: {b['text_strong']};
}}
QPushButton#Primary {{
    background-color: {a['primary']};
    color: {a['on_primary']};
    font-weight: bold;
    border: none;
}}
QPushButton#Primary:hover {{
    background-color: {a['primary_dim']};
}}
QListWidget {{
    background-color: {b['bg']};
    border: 1px solid {b['border']};
    border-radius: 10px;
    outline: none;
}}
QListWidget::item {{
    padding: 6px;
    border-radius: 8px;
    margin: 2px 4px;
}}
QListWidget::item:selected {{
    background-color: {a['primary_dim']};
    color: {b['text_strong']};
}}
QListWidget::item:hover {{
    background-color: {b['bg_hover']};
}}
QLineEdit, QComboBox, QSpinBox {{
    background-color: {b['bg_alt']};
    border: 1px solid {b['border']};
    border-radius: 8px;
    padding: 5px 10px;
    selection-background-color: {a['primary_dim']};
}}
QLineEdit:focus, QComboBox:focus {{
    border-color: {a['primary']};
}}
QTabWidget::pane {{
    border: 1px solid {b['border']};
    border-radius: 10px;
    background: {b['bg']};
}}
QTabBar::tab {{
    background: {b['bg_alt']};
    padding: 8px 18px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background: {a['primary']};
    color: {a['on_primary']};
    font-weight: bold;
}}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border-radius: 4px;
    border: 1px solid {b['border']};
    background: {b['bg_alt']};
}}
QCheckBox::indicator:checked {{
    background: {a['primary']};
    border-color: {a['primary']};
}}
QMenu {{
    background-color: {b['bg_card']};
    border: 1px solid {b['border']};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 6px;
}}
QMenu::item:selected {{
    background-color: {a['primary_dim']};
}}
QToolTip {{
    background-color: {b['bg_card']};
    color: {b['text']};
    border: 1px solid {b['border']};
    border-radius: 6px;
    padding: 4px 8px;
}}
QScrollBar:vertical {{
    background: transparent; width: 8px;
}}
QScrollBar::handle:vertical {{
    background: {b['border']}; border-radius: 4px; min-height: 30px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
"""


# 贴图边框预设 -> 绘制参数（见 tools/pin.py）
PIN_BORDER_PRESETS = ("none", "thin", "thick", "dashed", "glow", "rounded")
