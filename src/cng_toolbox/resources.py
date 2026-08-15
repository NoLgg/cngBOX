"""resources — 资源定位与加载。

同时支持两种运行环境：
- 开发模式：直接读取项目 assets/ 目录
- PyInstaller 打包：读取 _MEIPASS 内嵌资源
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon, QPixmap


def assets_dir() -> Path:
    """返回 assets 目录（开发 or 打包环境自适应）。"""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parents[2]  # src/cng_toolbox/.. = 项目根
    return base / "assets"


def icon_path(name: str) -> str:
    """图标文件路径（assets/icons/<name>.png）。"""
    return str(assets_dir() / "icons" / name)


def app_icon_path() -> str:
    """exe 应用图标路径（assets/icon-app.ico）。"""
    return str(assets_dir() / "icon-app.ico")


def load_pixmap(name: str) -> QPixmap:
    """加载 assets/icons/<name>.png 为 QPixmap（失败时返回空）。"""
    return QPixmap(icon_path(name))


def load_icon(name: str) -> QIcon:
    """加载 assets/icons/<name>.png 为 QIcon（失败时返回空）。"""
    return QIcon(icon_path(name))
