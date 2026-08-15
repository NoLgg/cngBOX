"""screenshot — 屏幕区域截图。

流程（Design Doc D4）：
1. 抓取虚拟桌面（逐屏 grabWindow 按 virtualGeometry 拼接）
2. 显示全屏半透明遮罩（基于已抓画面，保证画面一致）
3. 鼠标框选 → 实时显示选区尺寸 → Esc/右键取消
4. 完成回调返回选区 QPixmap
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, QRect, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

from cng_toolbox.config import MIN_SELECTION


def grab_virtual_desktop() -> QPixmap:
    """抓取全部显示器组成的虚拟桌面，返回拼接 QPixmap。"""
    screens = QGuiApplication.screens()
    if not screens:
        return QPixmap()
    geometry = QGuiApplication.primaryScreen().virtualGeometry()
    canvas = QPixmap(geometry.size())
    canvas.fill(QColor(0, 0, 0))
    painter = QPainter(canvas)
    for screen in screens:
        g = screen.geometry()
        shot = screen.grabWindow(0, g.x(), g.y(), g.width(), g.height())
        painter.drawPixmap(g.x() - geometry.x(), g.y() - geometry.y(), shot)
    painter.end()
    return canvas


@dataclass
class ScreenshotResult:
    pixmap: QPixmap
    rect: QRect  # 虚拟桌面坐标


class ScreenshotOverlay(QWidget):
    """全屏遮罩 + 框选。"""

    completed = Signal(object)  # ScreenshotResult
    cancelled = Signal()

    def __init__(self, desktop: QPixmap, geometry: QRect) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self._desktop = desktop
        self._geometry = geometry
        self._origin: QRect | None = None
        self._current: QRect | None = None
        self.setGeometry(geometry)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)

    # -- 事件 ------------------------------------------------------------------

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.close()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = QRect(event.position().toPoint(), event.position().toPoint())
            self._current = QRect(event.position().toPoint(), event.position().toPoint())

    def mouseMoveEvent(self, event) -> None:
        if self._origin is not None:
            self._current = QRect(
                self._origin.topLeft(), event.position().toPoint()
            ).normalized()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._current is None:
            return
        rect = self._current
        self._origin = None
        self._current = None
        if rect.width() < MIN_SELECTION or rect.height() < MIN_SELECTION:
            self.cancelled.emit()
            self.close()
            return
        result = ScreenshotResult(
            pixmap=self._desktop.copy(rect), rect=rect
        )
        self.completed.emit(result)
        self.close()

    # -- 绘制 ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        # 遮罩：半透明黑 + 已抓画面（画面被压暗，选区高亮）
        painter.drawPixmap(self.rect(), self._desktop)
        overlay = QColor(20, 24, 32, 170)
        painter.fillRect(self.rect(), overlay)

        if self._current is not None:
            rect = self._current
            # 选区恢复原画面
            painter.drawPixmap(rect, self._desktop, rect)
            # 选区边框
            painter.setPen(QPen(QColor("#3d8b80"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)
            # 尺寸标注
            size_text = f"{rect.width()} × {rect.height()}"
            painter.setPen(QColor("#ffffff"))
            font = painter.font()
            font.setPointSize(9)
            painter.setFont(font)
            painter.drawText(
                rect.right() - 100, rect.top() - 8, 110, 20,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                size_text,
            )


class ScreenshotTool(QObject):
    """截图工具入口。"""

    completed = Signal(object)  # ScreenshotResult
    cancelled = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._overlay: ScreenshotOverlay | None = None

    def start(self) -> None:
        if self._overlay is not None:
            return
        desktop = grab_virtual_desktop()
        geometry = QGuiApplication.primaryScreen().virtualGeometry()
        self._overlay = ScreenshotOverlay(desktop, geometry)
        self._overlay.completed.connect(self._on_completed)
        self._overlay.cancelled.connect(self._on_cancelled)
        self._overlay.show()
        self._overlay.activateWindow()

    def _on_completed(self, result: ScreenshotResult) -> None:
        self._overlay = None
        self.completed.emit(result)

    def _on_cancelled(self) -> None:
        self._overlay = None
        self.cancelled.emit()
