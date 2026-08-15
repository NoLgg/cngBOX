"""resources — 资源定位与加载。

同时支持两种运行环境：
- 开发模式：直接读取项目 assets/ 目录
- PyInstaller 打包：读取 _MEIPASS 内嵌资源
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap

# 加载时预缩放到合理尺寸：UI 显示分辨率远小于原始 AI 图，
# 预缩放可大幅减少 resize/绘制时的 CPU/内存开销（性能优化）
_LOAD_CACHE: dict[str, QPixmap] = {}


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


def load_pixmap(name: str, max_edge: int = 1024) -> QPixmap:
    """加载 assets/icons/<name>.png 为 QPixmap（带缓存 + 预缩放）。

    max_edge：最长边预缩放上限（默认 1024px）。UI 展示最大 ~800px，
    原始图 1024~2048px 预缩放后绘制与缩放开销显著下降。
    """
    if name in _LOAD_CACHE:
        return _LOAD_CACHE[name]
    pm = QPixmap(icon_path(name))
    if not pm.isNull():
        longest = max(pm.width(), pm.height())
        if longest > max_edge:
            pm = pm.scaled(
                max_edge, max_edge,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        _LOAD_CACHE[name] = pm
    return pm


def load_icon(name: str) -> QIcon:
    """加载 assets/icons/<name>.png 为 QIcon（失败时返回空）。"""
    return QIcon(icon_path(name))
