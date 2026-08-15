"""tray_app — 系统托盘。

托盘菜单：显示主面板 / 截图置顶 / 粘贴板 / 取色器 / 关闭全部贴图 / 退出。
气泡通知用于热键冲突、贴图上限、剪贴板提示等。
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from cng_toolbox.resources import load_icon


class TrayApp(QObject):
    """托盘图标与菜单。"""

    show_panel = Signal()
    invoke_screenshot = Signal()
    invoke_clipboard = Signal()
    invoke_color_picker = Signal()
    clip_to_screen = Signal()
    close_all_pins = Signal()
    quit_app = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tray = QSystemTrayIcon(load_icon("icon-tray"), self)
        self._tray.setToolTip("草泥鸽工具箱")

        menu = QMenu()
        act_panel = QAction(load_icon("icon-app"), "显示主面板", self)
        act_panel.triggered.connect(self.show_panel)
        menu.addAction(act_panel)
        menu.addSeparator()

        act_shot = QAction(load_icon("icon-tool-screenshot"), "截图置顶", self)
        act_shot.triggered.connect(self.invoke_screenshot)
        menu.addAction(act_shot)

        act_clip = QAction(load_icon("icon-tool-clipboard"), "粘贴板", self)
        act_clip.triggered.connect(self.invoke_clipboard)
        menu.addAction(act_clip)

        act_clip_screen = QAction(load_icon("icon-pin"), "贴出剪贴板", self)
        act_clip_screen.triggered.connect(self.clip_to_screen)
        menu.addAction(act_clip_screen)

        act_color = QAction(load_icon("icon-tool-colorpicker"), "取色器", self)
        act_color.triggered.connect(self.invoke_color_picker)
        menu.addAction(act_color)

        menu.addSeparator()
        act_close_pins = QAction(load_icon("icon-pin"), "关闭全部贴图", self)
        act_close_pins.triggered.connect(self.close_all_pins)
        menu.addAction(act_close_pins)

        menu.addSeparator()
        act_quit = QAction("退出", self)
        act_quit.triggered.connect(self.quit_app)
        menu.addAction(act_quit)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_activated)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_panel.emit()

    def show(self) -> None:
        self._tray.show()

    def hide(self) -> None:
        self._tray.hide()

    def notify(self, title: str, message: str) -> None:
        self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)
