"""HotkeyManager — 全局热键注册与分发。

设计（Design Doc D3）：
- HotkeyEngine 接口抽象；主实现 Win32HotkeyEngine（ctypes RegisterHotKey +
  WM_HOTKEY 拦截），零第三方依赖（qthotkey 在 PyPI 不可用，按 plan 兜底预案采用）。
- HotkeyManager 负责：按配置注册全部热键、冲突提示、热键变更重注册、
  工具禁用联动注销、事件分发。

线程模型：Win32HotkeyEngine 在 GUI 线程通过 QAbstractNativeEventFilter
接收 WM_HOTKEY 消息，触发 Qt 信号；分发在 GUI 线程完成。
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, QSignalBlocker, Signal

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

_VK_MAP = {
    "A": 0x41, "B": 0x42, "C": 0x43, "D": 0x44, "E": 0x45, "F": 0x46,
    "G": 0x47, "H": 0x48, "I": 0x49, "J": 0x4A, "K": 0x4B, "L": 0x4C,
    "M": 0x4D, "N": 0x4E, "O": 0x4F, "P": 0x50, "Q": 0x51, "R": 0x52,
    "S": 0x53, "T": 0x54, "U": 0x55, "V": 0x56, "W": 0x57, "X": 0x58,
    "Y": 0x59, "Z": 0x5A,
    "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
    "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73, "F5": 0x74,
    "F6": 0x75, "F7": 0x76, "F8": 0x77, "F9": 0x78, "F10": 0x79,
    "F11": 0x7A, "F12": 0x7B,
    "Space": 0x20, "Enter": 0x0D, "Tab": 0x09, "Esc": 0x1B,
    "Backspace": 0x08, "Delete": 0x2E, "Insert": 0x2D,
    "Home": 0x24, "End": 0x23, "PageUp": 0x21, "PageDown": 0x22,
    "Up": 0x26, "Down": 0x28, "Left": 0x25, "Right": 0x27,
    "`": 0xC0, "-": 0xBD, "=": 0xBB, "[": 0xDB, "]": 0xDD,
    "\\": 0xDC, ";": 0xBA, "'": 0xDE, ",": 0xBC, ".": 0xBE, "/": 0xBF,
}


def parse_sequence(sequence: str | None) -> tuple[int, int] | None:
    """解析 'Ctrl+Shift+A' 形式的快捷键为 (modifiers, vk)。

    返回 None 表示空/非法序列（调用方视为禁用）。
    """
    if not sequence:
        return None
    parts = [p.strip() for p in sequence.split("+") if p.strip()]
    if not parts:
        return None
    mods = 0
    key = None
    for part in parts:
        lower = part.lower()
        if lower in ("ctrl", "control"):
            mods |= MOD_CONTROL
        elif lower in ("alt",):
            mods |= MOD_ALT
        elif lower in ("shift",):
            mods |= MOD_SHIFT
        elif lower in ("win", "meta", "cmd"):
            mods |= MOD_WIN
        else:
            key = part
    if key is None:
        return None
    vk = _VK_MAP.get(key)
    if vk is None:
        return None
    return (mods | MOD_NOREPEAT, vk)


class Win32HotkeyEngine(QAbstractNativeEventFilter, QObject):
    """基于 Win32 RegisterHotKey 的全局热键引擎。"""

    triggered = Signal(str)  # hotkey_id

    def __init__(self, parent: QObject | None = None) -> None:
        QObject.__init__(self, parent)
        QAbstractNativeEventFilter.__init__(self)
        self._registrations: dict[int, str] = {}  # id -> hotkey_id
        self._by_key: dict[tuple[int, int], int] = {}  # (mods,vk) -> id
        self._next_id = 1
        self._user32 = ctypes.windll.user32

    # -- 生命周期 ------------------------------------------------------------

    def start(self) -> None:
        from PySide6.QtCore import QCoreApplication

        QCoreApplication.instance().installNativeEventFilter(self)

    def stop(self) -> None:
        from PySide6.QtCore import QCoreApplication

        QCoreApplication.instance().removeNativeEventFilter(self)
        for hotkey_id in list(self._registrations.values()):
            self.unregister(hotkey_id)

    # -- 注册 ----------------------------------------------------------------

    def register(self, hotkey_id: str, sequence: str) -> bool:
        parsed = parse_sequence(sequence)
        if parsed is None:
            return False
        mods, vk = parsed
        if (mods, vk) in self._by_key:
            return False  # 冲突（本引擎内）
        hwnd = None  # 注册到当前线程
        hotkey_int = self._next_id
        self._next_id += 1
        ok = self._user32.RegisterHotKey(hwnd, hotkey_int, mods, vk)
        if not ok:
            return False
        self._registrations[hotkey_int] = hotkey_id
        self._by_key[(mods, vk)] = hotkey_int
        return True

    def unregister(self, hotkey_id: str) -> None:
        hotkey_int = next(
            (k for k, v in self._registrations.items() if v == hotkey_id), None
        )
        if hotkey_int is None:
            return
        self._user32.UnregisterHotKey(None, hotkey_int)
        del self._registrations[hotkey_int]
        for key in list(self._by_key):
            if self._by_key[key] == hotkey_int:
                del self._by_key[key]

    def unregister_all(self) -> None:
        for hotkey_id in list(self._registrations.values()):
            self.unregister(hotkey_id)

    # -- 消息拦截 --------------------------------------------------------------

    def nativeEventFilter(self, event_type: bytes, message) -> bool:
        try:
            # PySide6 6.5+: message 为 int；旧版本为 voidptr，均可转 int
            msg_ptr = int(message)
        except (TypeError, ValueError):
            return False
        try:
            msg = ctypes.cast(msg_ptr, ctypes.POINTER(wintypes.MSG)).contents
        except (TypeError, ValueError):
            return False
        if msg.message == WM_HOTKEY:
            hotkey_int = msg.wParam
            hotkey_id = self._registrations.get(hotkey_int)
            if hotkey_id:
                self.triggered.emit(hotkey_id)
                return True
        return False


class HotkeyManager(QObject):
    """统一热键管理：配置驱动注册、冲突提示、变更重注册。"""

    hotkey_triggered = Signal(str)  # hotkey_id
    conflict = Signal(str, str)  # hotkey_id, sequence

    def __init__(self, config: "ConfigStore", engine: Win32HotkeyEngine | None = None) -> None:
        super().__init__()
        self._config = config
        self._engine = engine or Win32HotkeyEngine()
        self._active: dict[str, str] = {}  # hotkey_id -> sequence
        self._engine.triggered.connect(self.hotkey_triggered)
        self._config.changed.connect(self._on_config_changed)

    @property
    def engine(self) -> Win32HotkeyEngine:
        return self._engine

    # -- 注册管理 --------------------------------------------------------------

    def apply_all(self, enabled_ids: set[str] | None = None) -> None:
        """按配置注册全部热键；enabled_ids 之外的忽略（工具禁用联动）。"""
        self._engine.unregister_all()
        self._active.clear()
        hotkeys = self._config.get("hotkeys", {}) or {}
        for hotkey_id, sequence in hotkeys.items():
            if enabled_ids is not None and hotkey_id not in enabled_ids:
                continue
            if not sequence:
                continue
            if self._engine.register(hotkey_id, sequence):
                self._active[hotkey_id] = sequence
            else:
                self.conflict.emit(hotkey_id, sequence)

    def _on_config_changed(self, keys: list[str]) -> None:
        if any(k.startswith("hotkeys.") for k in keys):
            self.apply_all()

    # -- 生命周期 --------------------------------------------------------------

    def start(self) -> None:
        self._engine.start()
        self.apply_all()

    def stop(self) -> None:
        self._engine.stop()
