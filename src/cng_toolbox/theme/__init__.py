"""theme — 手绘便当盒主题（Sketch Bento）。

基于 StyleKit「铅笔手绘风」token：
- 纸张米色底 #f5f0e8 / #e8e2d8
- 炭黑墨线 #2c2c2c，虚线边框，硬铅笔阴影
- 小圆角（禁 rounded-xl/2xl），楷体手写感
- 彩铅点缀：青绿 #3d8b80 / 橙黄 #d99a3d / 紫罗兰 #8b7bb8
"""

from __future__ import annotations

ACCENTS: dict[str, dict[str, str]] = {
    "teal": {
        "primary": "#3d8b80",   # 彩铅青绿
        "primary_dim": "#2f6f66",
        "on_primary": "#f5f0e8",
    },
    "orange": {
        "primary": "#d99a3d",
        "primary_dim": "#b87f2a",
        "on_primary": "#f5f0e8",
    },
    "violet": {
        "primary": "#8b7bb8",
        "primary_dim": "#6f5f9e",
        "on_primary": "#f5f0e8",
    },
}

BASE = {
    "paper": "#f5f0e8",        # 背景主色（素描纸）
    "paper_deep": "#e8e2d8",   # 背景辅色
    "paper_input": "#faf5ed",  # 输入框底色
    "ink": "#2c2c2c",          # 墨线 / 文字主色
    "ink_soft": "#5a5a5a",     # 正文辅色
    "ink_faint": "#8a8a8a",    # 弱化色
    "orange": "#d99a3d",       # 彩铅橙黄
    "violet": "#8b7bb8",       # 彩铅紫
    "red": "#c96a5e",          # 彩铅红
    "green": "#6b9e62",        # 彩铅绿
}


def build_qss(accent: str = "teal") -> str:
    """生成全局 QSS（铅笔手绘风，基于指定彩铅强调色）。"""
    a = ACCENTS.get(accent, ACCENTS["teal"])
    b = BASE
    return f"""
* {{
    font-family: "KaiTi", "楷体", "STKaiti", "Microsoft YaHei UI", sans-serif;
    font-size: 13px;
    color: {b['ink']};
}}
QMainWindow, QDialog {{
    background-color: {b['paper']};
}}
QWidget#Card {{
    background-color: {b['paper']};
    border: 2px dashed {b['ink']};
    border-radius: 7px;
}}
QWidget#Card:hover {{
    background-color: {b['paper_deep']};
}}
QLabel#CardTitle {{
    color: {b['ink']};
    font-size: 16px;
    font-weight: bold;
}}
QLabel#CardDesc {{
    color: {b['ink_soft']};
    font-size: 12px;
}}
QLabel#CardHotkey {{
    color: {a['primary_dim']};
    font-size: 11px;
    background-color: {b['paper_input']};
    border: 1.5px solid {b['ink']};
    border-radius: 4px;
    padding: 2px 8px;
    font-family: Consolas, monospace;
}}
QPushButton {{
    background-color: {b['paper']};
    border: 2px dashed {b['ink']};
    border-radius: 7px;
    padding: 6px 14px;
    font-weight: bold;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {b['paper_deep']};
}}
QPushButton:pressed {{
    background-color: {b['ink']};
    color: {b['paper']};
}}
QPushButton#Primary {{
    background-color: {b['ink']};
    color: {b['paper']};
    border: 2px solid {b['ink']};
    font-weight: bold;
}}
QPushButton#Primary:hover {{
    background-color: {b['ink_soft']};
}}
QListWidget {{
    background-color: {b['paper']};
    border: 2px dashed {b['ink']};
    border-radius: 7px;
    outline: none;
}}
QListWidget::item {{
    padding: 6px;
    border-radius: 5px;
    margin: 2px 4px;
}}
QListWidget::item:selected {{
    background-color: {a['primary']};
    color: {b['paper']};
}}
QListWidget::item:hover {{
    background-color: {b['paper_deep']};
}}
QLineEdit, QComboBox, QSpinBox {{
    background-color: {b['paper_input']};
    border: 2px dashed {b['ink']};
    border-radius: 7px;
    padding: 5px 10px;
    color: {b['ink']};
    selection-background-color: {a['primary']};
}}
QLineEdit:focus, QComboBox:focus {{
    border-color: {a['primary']};
}}
QTabWidget::pane {{
    border: 2px dashed {b['ink']};
    border-radius: 7px;
    background: {b['paper']};
}}
QTabBar::tab {{
    background: {b['paper']};
    border: 2px dashed {b['ink']};
    padding: 6px 16px;
    border-radius: 6px;
    margin-right: 4px;
    font-weight: bold;
}}
QTabBar::tab:selected {{
    background: {b['ink']};
    color: {b['paper']};
}}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border-radius: 4px;
    border: 2px solid {b['ink']};
    background: {b['paper_input']};
}}
QCheckBox::indicator:checked {{
    background: {a['primary']};
}}
QMenu {{
    background-color: {b['paper']};
    border: 2px solid {b['ink']};
    border-radius: 7px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 5px;
}}
QMenu::item:selected {{
    background-color: {b['paper_deep']};
}}
QToolTip {{
    background-color: {b['paper_input']};
    color: {b['ink']};
    border: 1.5px solid {b['ink']};
    border-radius: 4px;
    padding: 4px 8px;
}}
QScrollBar:vertical {{
    background: transparent; width: 8px;
}}
QScrollBar::handle:vertical {{
    background: {b['ink_faint']}; border-radius: 4px; min-height: 30px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
"""


# 贴图边框预设 -> 绘制参数（见 tools/pin.py）
PIN_BORDER_PRESETS = ("none", "thin", "thick", "dashed", "glow", "rounded")
