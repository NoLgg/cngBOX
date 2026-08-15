"""main — 应用入口。

启动流程（Design Doc）：
ConfigStore → 单实例锁 → QApplication → 主题应用 → 工具注册 →
TrayApp → HotkeyManager 注册 → 常驻。
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QLockFile
from PySide6.QtWidgets import QApplication

from cng_toolbox import APP_NAME, __version__
from cng_toolbox.resources import load_icon
from cng_toolbox.shell.config_store import ConfigStore, default_app_dir
from cng_toolbox.shell.hotkey_manager import HotkeyManager
from cng_toolbox.shell.main_window import MainWindow
from cng_toolbox.shell.tool_registry import Tool, ToolRegistry
from cng_toolbox.shell.tray_app import TrayApp
from cng_toolbox.storage.history_db import HistoryDB
from cng_toolbox.storage.image_store import ImageStore
from cng_toolbox.theme import build_qss
from cng_toolbox.tools.clipboard_tool import ClipboardTool
from cng_toolbox.tools.color_picker import ColorPickerTool
from cng_toolbox.tools.pin import PinManager
from cng_toolbox.tools.screenshot import ScreenshotTool
from cng_toolbox.tools.settings_dialog import SettingsDialog


class CaoNiGeApp:
    """应用装配根。"""

    def __init__(self, qapp: QApplication, app_dir: Path) -> None:
        self.qapp = qapp
        self.app_dir = app_dir

        # 基础设施
        self.config = ConfigStore(app_dir)
        self.registry = ToolRegistry()
        self.hotkeys = HotkeyManager(self.config)
        self.tray = TrayApp()

        # 存储
        self.db = HistoryDB(app_dir / "clipboard.db")
        self.images = ImageStore(app_dir / "images")

        # 工具
        self.pins = PinManager(self.config)
        self.screenshot = ScreenshotTool()
        self.clipboard = ClipboardTool(self.config, self.db, self.images, self.pins)
        self.color_picker = ColorPickerTool(self.config, app_dir)

        # UI
        self.main_window: MainWindow | None = None
        self.settings_dialog: SettingsDialog | None = None

        self._register_tools()
        self._wire_signals()
        self._apply_theme()

    # -- 装配 ------------------------------------------------------------------

    def _register_tools(self) -> None:
        self.registry.register(
            Tool(
                tool_id="screenshot",
                name="截图置顶",
                description="框选屏幕区域，截图即钉在屏幕上",
                icon="icon-tool-screenshot",
                hotkey_id="screenshot",
                invoke=self.screenshot.start,
            )
        )
        self.registry.register(
            Tool(
                tool_id="clipboard",
                name="粘贴板",
                description="剪贴板历史 · 贴屏 · 搜索固定",
                icon="icon-tool-clipboard",
                hotkey_id="clipboard_panel",
                invoke=self.clipboard.show_panel,
            )
        )
        self.registry.register(
            Tool(
                tool_id="color_picker",
                name="取色器",
                description="屏幕取色，复制 HEX/RGB",
                icon="icon-tool-colorpicker",
                hotkey_id="color_picker",
                invoke=self.color_picker.start,
            )
        )

    def _wire_signals(self) -> None:
        # 热键分发
        self.hotkeys.hotkey_triggered.connect(self._on_hotkey)
        self.hotkeys.conflict.connect(
            lambda hid, seq: self.tray.notify(
                "热键冲突", f"「{seq}」注册失败，可能被其他程序占用"
            )
        )
        # 托盘
        self.tray.show_panel.connect(self.show_main_window)
        self.tray.invoke_screenshot.connect(self.screenshot.start)
        self.tray.invoke_clipboard.connect(self.clipboard.show_panel)
        self.tray.invoke_color_picker.connect(self.color_picker.start)
        self.tray.close_all_pins.connect(self.pins.close_all)
        self.tray.quit_app.connect(self.quit)

        # 截图完成 → 贴图 + 复制到剪贴板
        self.screenshot.completed.connect(self._on_screenshot_done)

        # 贴图上限提示
        self.pins.limit_reached.connect(
            lambda: self.tray.notify("贴图数量已达上限", "最多同时保留 20 张贴图")
        )

        # 剪贴板提示
        self.clipboard.clipboard_too_big.connect(
            lambda: self.tray.notify("剪贴板", "图片体积超过上限，未记录")
        )
        self.clipboard.clip_empty.connect(
            lambda: self.tray.notify("贴屏", "剪贴板为空，无法贴屏")
        )

        # 防回环：自身写入剪贴板（取色复制、贴图复制）不进入历史
        self.color_picker.picked.connect(self.clipboard.mark_self_write_text)
        self.pins.copied.connect(self.clipboard.mark_self_write_pixmap)

        # 配置变更 → 主题/工具开关联动
        self.config.changed.connect(self._on_config_changed)

    def _on_hotkey(self, hotkey_id: str) -> None:
        if hotkey_id == "screenshot":
            self.screenshot.start()
        elif hotkey_id == "clipboard_panel":
            self.clipboard.show_panel()
        elif hotkey_id == "color_picker":
            self.color_picker.start()
        elif hotkey_id == "show_panel":
            self.show_main_window()
        elif hotkey_id == "close_all_pins":
            self.pins.close_all()

    def _on_screenshot_done(self, result) -> None:
        # 默认：生成贴图 + 图片复制到剪贴板
        self.pins.create(result.pixmap, title="截图贴图")
        QApplication.clipboard().setPixmap(result.pixmap)

    def _on_config_changed(self, keys: list[str]) -> None:
        if any(k.startswith("accent") or k.startswith("theme") for k in keys):
            self._apply_theme()
        if any(k.startswith("tools.") for k in keys):
            self._apply_tool_switches()

    def _apply_theme(self) -> None:
        self.qapp.setStyleSheet(build_qss(self.config.get("accent", "teal")))

    def _apply_tool_switches(self) -> None:
        tools = self.config.get("tools", {}) or {}
        for tool in self.registry.all():
            enabled = bool(tools.get(tool.tool_id, True))
            self.registry.set_enabled(tool.tool_id, enabled)
        # 热键联动：禁用的工具热键注销
        enabled_ids = {
            tool.hotkey_id
            for tool in self.registry.all()
            if tool.enabled and tool.hotkey_id
        }
        self.hotkeys.apply_all(enabled_ids=enabled_ids)
        if self.main_window is not None:
            self.main_window.rebuild(self.registry, self._hotkey_texts())

    def _hotkey_texts(self) -> dict[str, str]:
        hotkeys = self.config.get("hotkeys", {}) or {}
        return {k: v for k, v in hotkeys.items() if v}

    # -- UI --------------------------------------------------------------------

    def show_main_window(self) -> None:
        if self.main_window is None:
            self.main_window = MainWindow(self.registry, self._hotkey_texts())
            self.main_window.tool_invoked.connect(self._on_tool_invoked)
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def _on_tool_invoked(self, tool_id: str) -> None:
        if tool_id == "settings":
            self._show_settings()
            return
        tool = self.registry.get(tool_id)
        if tool:
            tool.invoke()

    def _show_settings(self) -> None:
        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(
                self.config,
                self.hotkeys,
                [t.tool_id for t in self.registry.all()],
            )
            self.settings_dialog.settings_changed.connect(self._on_settings_changed)
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def _on_settings_changed(self) -> None:
        # 热键/主题/工具开关已在各自处理中联动；这里兜底刷新主面板
        if self.main_window is not None:
            self.main_window.rebuild(self.registry, self._hotkey_texts())

    # -- 生命周期 ----------------------------------------------------------------

    def start(self) -> None:
        self.hotkeys.start()
        self.clipboard.start()
        self._apply_tool_switches()
        self.tray.show()
        # 首次启动显示主面板
        self.show_main_window()

    def quit(self) -> None:
        self.hotkeys.stop()
        self.clipboard.stop()
        self.db.close()
        self.tray.hide()
        self.qapp.quit()


def main() -> int:
    app_dir = default_app_dir()
    app_dir.mkdir(parents=True, exist_ok=True)

    qapp = QApplication(sys.argv)
    qapp.setApplicationName(APP_NAME)
    qapp.setApplicationVersion(__version__)
    # 应用图标（任务栏/窗口）
    qapp.setWindowIcon(load_icon("icon-app"))

    # 单实例锁
    lock = QLockFile(str(app_dir / "singleton.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        print(f"{APP_NAME} 已在运行", file=sys.stderr)
        return 1

    app = CaoNiGeApp(qapp, app_dir)
    app.start()
    code = qapp.exec()
    lock.unlock()
    return code


if __name__ == "__main__":
    sys.exit(main())
