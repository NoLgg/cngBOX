"""pin — 置顶贴图：PinWindow + PinManager。

- PinWindow：无边框置顶窗口（Qt.Tool 不入任务栏），支持拖动、滚轮缩放、
  右键菜单、双击复制、点击穿透切换、边框样式绘制。
- PinManager：贴图注册表（上限 PIN_LIMIT=20）、关闭全部、隐藏/显示切换、
  边框配置变更广播。

边框预设（Design Doc D5）：none / thin / thick / dashed / glow / rounded。
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QContextMenuEvent,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGraphicsDropShadowEffect,
    QMenu,
    QWidget,
)

from cng_toolbox.config import PIN_LIMIT, PIN_SCALE_MAX, PIN_SCALE_MIN
from cng_toolbox.shell.config_store import ConfigStore


class PinWindow(QWidget):
    """一张置顶贴图。"""

    closed = Signal(object)  # self
    copied = Signal(object)  # QPixmap（内容被复制到剪贴板时发出）

    def __init__(
        self,
        pixmap: QPixmap,
        config: ConfigStore,
        pin_manager: "PinManager",
        title: str = "贴图",
    ) -> None:
        super().__init__(None, Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.Tool)
        self._config = config
        self._manager = pin_manager
        self._title = title
        self._pixmap = pixmap
        self._scale = 1.0
        self._drag_offset = None
        self._click_through = False
        self._content = pixmap  # 原始内容（含文本贴图渲染）

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle(title)
        self.setToolTip(title)
        self._apply_border_effect()
        self._resize_to_content()

    # -- 几何 ------------------------------------------------------------------

    def _border_width(self) -> int:
        preset = self._config.get("pin_border.preset", "thin")
        if preset in ("none", "glow", "rounded"):
            return 0
        if preset == "thick":
            return 6
        if preset == "dashed":
            # 虚线跟随用户配置的粗细（至少 2px 保证可见）
            return max(2, self._config.get("pin_border.width", 2))
        return self._config.get("pin_border.width", 2)

    def _resize_to_content(self) -> None:
        w = max(1, int(self._content.width() * self._scale))
        h = max(1, int(self._content.height() * self._scale))
        pad = self._border_width()
        self.resize(w + pad * 2, h + pad * 2)

    def set_content(self, pixmap: QPixmap) -> None:
        self._content = pixmap
        self._resize_to_content()
        self.update()

    def content(self) -> QPixmap:
        return self._content

    # -- 绘制 ------------------------------------------------------------------

    def _apply_border_effect(self) -> None:
        preset = self._config.get("pin_border.preset", "thin")
        if preset == "glow":
            effect = QGraphicsDropShadowEffect(self)
            color = QColor(self._config.get("pin_border.color", "#3d8b80"))
            effect.setColor(color)
            effect.setBlurRadius(22)
            effect.setOffset(0, 0)
            self.setGraphicsEffect(effect)
        elif preset in ("thin", "thick", "dashed", "rounded"):
            # 贴纸硬阴影（铅笔投影）
            effect = QGraphicsDropShadowEffect(self)
            effect.setColor(QColor(44, 44, 44, 90))
            effect.setBlurRadius(0)
            effect.setOffset(3, 3)
            self.setGraphicsEffect(effect)
        else:
            self.setGraphicsEffect(None)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        preset = self._config.get("pin_border.preset", "thin")
        pad = self._border_width()
        rect = self.rect()

        # 纸张底色（贴纸感）
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(rect)

        # 内容
        target = rect.adjusted(pad, pad, -pad, -pad)
        painter.drawPixmap(target, self._content)

        # 边框（手绘墨线 / 彩铅）
        if preset == "rounded":
            color = QColor(self._config.get("pin_border.color", "#d99a3d"))
            pen = QPen(color, 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 14, 14)
        elif preset in ("thin", "thick"):
            color = QColor(self._config.get("pin_border.color", "#2c2c2c"))
            width = self._border_width()
            painter.setPen(QPen(color, width))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect.adjusted(1, 1, -1, -1))
        elif preset == "dashed":
            color = QColor(self._config.get("pin_border.color", "#2f6f66"))
            pen = QPen(color, 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect.adjusted(2, 2, -2, -2))
        # none / glow：无边框

    # -- 交互 ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None

    def mouseDoubleClickEvent(self, event) -> None:
        self.copy_to_clipboard()

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = 1.1 if delta > 0 else 1 / 1.1
        new_scale = max(PIN_SCALE_MIN, min(PIN_SCALE_MAX, self._scale * factor))
        if new_scale == self._scale:
            return
        # 以鼠标位置为锚点缩放
        cursor_pos = event.position()
        old_w, old_h = self.width(), self.height()
        anchor_x = cursor_pos.x() / old_w
        anchor_y = cursor_pos.y() / old_h
        self._scale = new_scale
        self._resize_to_content()
        new_w, new_h = self.width(), self.height()
        self.move(
            self.x() + int(anchor_x * (old_w - new_w)),
            self.y() + int(anchor_y * (old_h - new_h)),
        )

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = QMenu(self)
        act_copy = QAction("复制", self)
        act_copy.triggered.connect(self.copy_to_clipboard)
        menu.addAction(act_copy)

        act_passthrough = QAction("点击穿透", self, checkable=True)
        act_passthrough.setChecked(self._click_through)
        act_passthrough.triggered.connect(self.toggle_click_through)
        menu.addAction(act_passthrough)

        act_save = QAction("保存到文件…", self)
        act_save.triggered.connect(self.save_to_file)
        menu.addAction(act_save)

        menu.addSeparator()
        act_close = QAction("关闭", self)
        act_close.triggered.connect(self.close)
        menu.addAction(act_close)

        menu.exec(event.globalPos())

    # -- 行为 ------------------------------------------------------------------

    def copy_to_clipboard(self) -> None:
        QApplication.clipboard().setPixmap(self._content)
        self.copied.emit(self._content)

    def toggle_click_through(self, checked: bool | None = None) -> None:
        if checked is None:
            checked = not self._click_through
        self._click_through = bool(checked)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, self._click_through)
        self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, self._click_through)
        self.show()  # 窗口标志变更后需重新显示

    def save_to_file(self) -> None:
        from pathlib import Path

        default_dir = Path.home() / "Pictures" / "CaoNiGeToolbox"
        default_dir.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(
            self, "保存贴图", str(default_dir / f"{self._title}.png"), "PNG 图片 (*.png)"
        )
        if path:
            self._content.save(path, "PNG")

    def refresh_border(self) -> None:
        self._apply_border_effect()
        self._resize_to_content()
        self.update()


class PinManager(QObject):
    """贴图统一管理。"""

    limit_reached = Signal()
    copied = Signal(object)  # QPixmap（贴图被复制时发出，供防回环）
    count_changed = Signal(int)  # 贴图数量变化（供状态卡刷新）

    def __init__(self, config: ConfigStore, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._pins: dict[int, PinWindow] = {}
        self._next_id = 1
        self._hidden = False
        config.changed.connect(self._on_config_changed)

    def _on_config_changed(self, keys: list[str]) -> None:
        if any(k.startswith("pin_border.") for k in keys):
            for pin in list(self._pins.values()):
                pin.refresh_border()

    def create(self, pixmap: QPixmap, title: str = "贴图") -> PinWindow | None:
        if len(self._pins) >= PIN_LIMIT:
            self.limit_reached.emit()
            return None
        pin = PinWindow(pixmap, self._config, self, title=title)
        pin.closed.connect(self._on_pin_closed)
        pin.copied.connect(self.copied)
        pin_id = self._next_id
        self._next_id += 1
        self._pins[pin_id] = pin
        pin.show()
        self.count_changed.emit(len(self._pins))
        return pin

    def _on_pin_closed(self, pin: PinWindow) -> None:
        for pin_id, p in list(self._pins.items()):
            if p is pin:
                del self._pins[pin_id]
                break
        self.count_changed.emit(len(self._pins))

    def close_all(self) -> None:
        for pin in list(self._pins.values()):
            pin.close()
        self._pins.clear()
        self.count_changed.emit(0)

    def toggle_hide_all(self) -> None:
        self._hidden = not self._hidden
        for pin in self._pins.values():
            pin.setVisible(not self._hidden)

    def hide_all(self) -> None:
        self._hidden = True
        for pin in self._pins.values():
            pin.hide()

    def show_all(self) -> None:
        self._hidden = False
        for pin in self._pins.values():
            pin.show()

    @property
    def count(self) -> int:
        return len(self._pins)

    @property
    def pins(self) -> list[PinWindow]:
        return list(self._pins.values())
