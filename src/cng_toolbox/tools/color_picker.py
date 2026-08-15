"""color_picker — 屏幕取色器。

- 全屏遮罩（基于已抓画面）：鼠标移动实时显示放大镜 + HEX/RGB。
- 单击复制 HEX 并退出；Esc 取消。
- 取色历史（最近 10 个）持久化到 ~/.cng-toolbox/color_history.json。
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, QRect, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

from cng_toolbox.config import COLOR_HISTORY_LIMIT
from cng_toolbox.shell.config_store import ConfigStore
from cng_toolbox.tools.screenshot import grab_virtual_desktop

MAGNIFY_RADIUS = 10  # 放大镜取样半径（像素）
MAGNIFY_SCALE = 8    # 放大倍数
MAGNIFY_SIZE = MAGNIFY_RADIUS * 2 * MAGNIFY_SCALE


def rgb_to_hex(r: int, g: int, b: int) -> str:
    return "#{:02X}{:02X}{:02X}".format(r, g, b)


class ColorPickerOverlay(QWidget):
    """全屏取色遮罩。"""

    picked = Signal(str)  # hex
    cancelled = Signal()

    def __init__(self, desktop: QPixmap, geometry: QRect) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self._desktop = desktop
        self._desktop_image = desktop.toImage()  # 缓存，避免每帧转换
        self._geometry = geometry
        self._mouse_pos = geometry.center()
        self.setGeometry(geometry)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

    # -- 事件 ------------------------------------------------------------------

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.close()

    def mouseMoveEvent(self, event) -> None:
        self._mouse_pos = event.position().toPoint()
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            r, g, b = self._pixel_rgb(self._mouse_pos)
            self.picked.emit(rgb_to_hex(r, g, b))
            self.close()

    def _pixel_rgb(self, pos) -> tuple[int, int, int]:
        # overlay 局部坐标与 desktop pixmap 坐标一一对应
        # （overlay 原点 = virtualGeometry.topLeft = desktop (0,0)）
        x = max(0, min(pos.x(), self._desktop.width() - 1))
        y = max(0, min(pos.y(), self._desktop.height() - 1))
        color = self._desktop_image.pixelColor(x, y)
        return color.red(), color.green(), color.blue()

    # -- 绘制 ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self._desktop)
        dim = QColor(15, 18, 26, 120)
        painter.fillRect(self.rect(), dim)

        pos = self._mouse_pos
        r, g, b = self._pixel_rgb(pos)

        # 放大镜
        center = QRect(
            pos.x() + 24, pos.y() + 24, MAGNIFY_SIZE, MAGNIFY_SIZE
        )
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.setBrush(QColor(26, 29, 36))
        painter.drawRect(center)
        sample = self._desktop.copy(
            pos.x() - MAGNIFY_RADIUS,
            pos.y() - MAGNIFY_RADIUS,
            MAGNIFY_RADIUS * 2, MAGNIFY_RADIUS * 2,
        ).scaled(MAGNIFY_SIZE, MAGNIFY_SIZE)
        painter.drawPixmap(center, sample)
        # 中心十字
        painter.setPen(QPen(QColor("#ffffff"), 1))
        cx, cy = center.center().x(), center.center().y()
        painter.drawLine(cx - 8, cy, cx + 8, cy)
        painter.drawLine(cx, cy - 8, cx, cy + 8)

        # 色值面板
        hex_text = rgb_to_hex(r, g, b)
        panel = QRect(pos.x() + 24, pos.y() + 24 + MAGNIFY_SIZE + 8, 190, 52)
        painter.setPen(QPen(QColor("#3a4150"), 1))
        painter.setBrush(QColor(26, 29, 36))
        painter.drawRect(panel)
        painter.setPen(QColor("#e8ecf3"))
        painter.drawText(panel.adjusted(10, 6, -10, -6),
                         f"{hex_text}   RGB({r}, {g}, {b})")
        painter.end()


class ColorPickerTool(QObject):
    """取色器工具。"""

    picked = Signal(str)

    def __init__(self, config: ConfigStore, app_dir: Path) -> None:
        super().__init__()
        self._config = config
        self._history_path = Path(app_dir) / "color_history.json"
        self._history: list[str] = self._load_history()
        self._overlay: ColorPickerOverlay | None = None

    # -- 历史 ------------------------------------------------------------------

    def _load_history(self) -> list[str]:
        try:
            data = json.loads(self._history_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [h for h in data if isinstance(h, str)][:COLOR_HISTORY_LIMIT]
        except (OSError, json.JSONDecodeError):
            pass
        return []

    def _save_history(self) -> None:
        self._history_path.write_text(
            json.dumps(self._history, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def history(self) -> list[str]:
        return list(self._history)

    def _record(self, hex_color: str) -> None:
        if hex_color in self._history:
            self._history.remove(hex_color)
        self._history.insert(0, hex_color)
        del self._history[COLOR_HISTORY_LIMIT:]
        self._save_history()

    # -- 取色 ------------------------------------------------------------------

    def start(self) -> None:
        if self._overlay is not None:
            return
        desktop = grab_virtual_desktop()
        geometry = QGuiApplication.primaryScreen().virtualGeometry()
        self._overlay = ColorPickerOverlay(desktop, geometry)
        self._overlay.picked.connect(self._on_picked)
        self._overlay.cancelled.connect(self._on_cancelled)
        from cng_toolbox.ui_utils import fade_in

        self._overlay.show()
        fade_in(self._overlay, ms=140, slide=0)
        self._overlay.activateWindow()

    def _on_picked(self, hex_color: str) -> None:
        self._overlay = None
        self._record(hex_color)
        QApplication.clipboard().setText(hex_color)
        self.picked.emit(hex_color)

    def _on_cancelled(self) -> None:
        self._overlay = None
