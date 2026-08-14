"""shell 包 — 应用壳：配置、热键、托盘、工具注册表、主面板。"""

from cng_toolbox.shell.config_store import ConfigStore, DEFAULTS, deep_merge
from cng_toolbox.shell.hotkey_manager import HotkeyManager, Win32HotkeyEngine, parse_sequence
from cng_toolbox.shell.main_window import MainWindow
from cng_toolbox.shell.tool_registry import Tool, ToolRegistry
from cng_toolbox.shell.tray_app import TrayApp

__all__ = [
    "ConfigStore",
    "DEFAULTS",
    "deep_merge",
    "HotkeyManager",
    "Win32HotkeyEngine",
    "parse_sequence",
    "MainWindow",
    "Tool",
    "ToolRegistry",
    "TrayApp",
]
