"""settings_dialog — 设置面板。

分组：通用（开机自启）/ 热键（自定义+禁用+冲突检测）/ 外观（主题/配色/
贴图边框预设+颜色+粗细）/ 剪贴板（上限/图片上限）/ 工具（开关联动）。
"""

from __future__ import annotations

import sys
import winreg
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from cng_toolbox.shell.config_store import ConfigStore
from cng_toolbox.shell.hotkey_manager import HotkeyManager
from cng_toolbox.theme import ACCENTS, PIN_BORDER_PRESETS

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "CaoNiGeToolbox"

_HOTKEY_LABELS = {
    "screenshot": "截图置顶",
    "color_picker": "取色器",
    "clipboard_panel": "粘贴板面板",
    "show_panel": "显示主面板",
    "close_all_pins": "关闭全部贴图",
}


class HotkeyEdit(QLineEdit):
    """点击聚焦后按下组合键即完成设置；空内容表示禁用。"""

    def __init__(self, hotkey_id: str, parent=None) -> None:
        super().__init__(parent)
        self._hotkey_id = hotkey_id
        self.setReadOnly(True)
        self.setPlaceholderText("点击后按下组合键…")
        self.setFixedWidth(180)

    def keyPressEvent(self, event) -> None:
        mods = []
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            mods.append("Ctrl")
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            mods.append("Alt")
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            mods.append("Shift")
        if event.modifiers() & Qt.KeyboardModifier.MetaModifier:
            mods.append("Win")
        key = event.key()
        if key in (
            Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Shift,
            Qt.Key.Key_Meta,
        ):
            return  # 仅修饰键，忽略
        text = QKeySequence(key).toString()
        if not text or text.startswith("Key"):
            return  # 未知键
        self.setText("+".join(mods + [text]))
        self.clearFocus()

    def keyReleaseEvent(self, event) -> None:
        pass  # 吞掉，避免焦点转移


class SettingsDialog(QDialog):
    """设置面板。"""

    settings_changed = Signal()

    def __init__(
        self,
        config: ConfigStore,
        hotkey_manager: HotkeyManager,
        tool_ids: list[str],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._hotkeys = hotkey_manager
        self._tool_ids = tool_ids
        self._hotkey_edits: dict[str, HotkeyEdit] = {}
        self.setWindowTitle("设置 — 草泥鸽工具箱")
        self.resize(520, 520)

        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._build_general_tab(), "通用")
        tabs.addTab(self._build_hotkey_tab(), "热键")
        tabs.addTab(self._build_appearance_tab(), "外观")
        tabs.addTab(self._build_clipboard_tab(), "剪贴板")
        tabs.addTab(self._build_tools_tab(), "工具")
        layout.addWidget(tabs, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

    # -- 通用 ------------------------------------------------------------------

    def _build_general_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self._autostart = QCheckBox("开机自动启动")
        self._autostart.setChecked(bool(self._config.get("autostart", False)))
        self._autostart.toggled.connect(self._on_autostart_toggled)
        form.addRow("启动", self._autostart)
        form.addRow("", QLabel("常驻系统托盘 · 关闭主窗口不退出"))
        return page

    def _on_autostart_toggled(self, checked: bool) -> None:
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
            )
        except OSError:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY)
        try:
            if checked:
                exe = sys.executable
                if exe.lower().endswith("python.exe"):
                    # 开发模式：python -m cng_toolbox.main
                    exe = f'"{exe}" -m cng_toolbox.main'
                winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, exe)
            else:
                try:
                    winreg.DeleteValue(key, RUN_VALUE)
                except OSError:
                    pass
        finally:
            winreg.CloseKey(key)
        self._config.set("autostart", bool(checked))

    # -- 热键 ------------------------------------------------------------------

    def _build_hotkey_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        hotkeys = self._config.get("hotkeys", {}) or {}
        for hotkey_id, label in _HOTKEY_LABELS.items():
            edit = HotkeyEdit(hotkey_id)
            edit.setText(hotkeys.get(hotkey_id) or "")
            edit.editingFinished.connect(
                lambda hid=hotkey_id, e=edit: self._on_hotkey_changed(hid, e)
            )
            self._hotkey_edits[hotkey_id] = edit
            form.addRow(f"{label}：", edit)
        form.addRow("", QLabel("点击输入框后按下新组合键；清空内容 = 禁用"))
        return page

    def _on_hotkey_changed(self, hotkey_id: str, edit: HotkeyEdit) -> None:
        sequence = edit.text().strip()
        # 冲突检测：与其它已设置热键比较
        for other_id, other_edit in self._hotkey_edits.items():
            if other_id != hotkey_id and other_edit.text().strip() == sequence and sequence:
                QMessageBox.warning(
                    self, "热键冲突",
                    f"「{sequence}」已被 {_HOTKEY_LABELS[other_id]} 占用",
                )
                edit.setText(self._config.get(f"hotkeys.{hotkey_id}", ""))
                return
        self._config.set(f"hotkeys.{hotkey_id}", sequence)
        self.settings_changed.emit()

    # -- 外观 ------------------------------------------------------------------

    def _build_appearance_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        # 主题（v1 仅深色）
        theme_box = QComboBox()
        theme_box.addItem("游戏化深色", "game-dark")
        theme_box.setCurrentIndex(0)
        form.addRow("主题", theme_box)

        # 配色
        accent_box = QComboBox()
        accent_box.addItem("青绿（默认）", "teal")
        accent_box.addItem("橙黄", "orange")
        accent_box.addItem("紫罗兰", "violet")
        accent_box.setCurrentIndex(
            {"teal": 0, "orange": 1, "violet": 2}.get(
                self._config.get("accent", "teal"), 0
            )
        )
        accent_box.currentIndexChanged.connect(
            lambda i: self._on_accent_changed(accent_box.itemData(i))
        )
        form.addRow("强调色", accent_box)

        # 贴图边框
        border_box = QGroupBox("贴图边框")
        bform = QFormLayout(border_box)
        preset_box = QComboBox()
        preset_labels = {
            "none": "无边框", "thin": "细线", "thick": "粗线",
            "dashed": "虚线", "glow": "发光", "rounded": "圆角",
        }
        for preset in PIN_BORDER_PRESETS:
            preset_box.addItem(preset_labels.get(preset, preset), preset)
        current_preset = self._config.get("pin_border.preset", "thin")
        idx = preset_box.findData(current_preset)
        preset_box.setCurrentIndex(max(0, idx))
        preset_box.currentIndexChanged.connect(
            lambda i: self._on_border_preset_changed(preset_box.itemData(i))
        )
        bform.addRow("预设", preset_box)

        color_row = QHBoxLayout()
        color_label = QLabel(self._config.get("pin_border.color", "#3d8b80"))
        color_btn = QPushButton("选择颜色…")
        color_btn.clicked.connect(
            lambda: self._on_border_color_changed(color_label)
        )
        color_row.addWidget(color_label)
        color_row.addWidget(color_btn)
        color_row.addStretch(1)
        bform.addRow("颜色", color_row)

        width_spin = QSpinBox()
        width_spin.setRange(1, 12)
        width_spin.setValue(int(self._config.get("pin_border.width", 2)))
        width_spin.valueChanged.connect(self._on_border_width_changed)
        bform.addRow("粗细", width_spin)
        form.addRow(border_box)

        return page

    def _on_accent_changed(self, accent: str) -> None:
        if accent:
            self._config.set("accent", accent)
            self.settings_changed.emit()

    def _on_border_preset_changed(self, preset: str) -> None:
        if preset:
            self._config.set("pin_border.preset", preset)
            self.settings_changed.emit()

    def _on_border_color_changed(self, label: QLabel) -> None:
        color = QColorDialog.getColor(
            QColor(self._config.get("pin_border.color", "#3d8b80")), self
        )
        if color.isValid():
            hex_color = color.name().upper()
            label.setText(hex_color)
            self._config.set("pin_border.color", hex_color)
            self.settings_changed.emit()

    def _on_border_width_changed(self, value: int) -> None:
        self._config.set("pin_border.width", int(value))
        self.settings_changed.emit()

    # -- 剪贴板 ------------------------------------------------------------------

    def _build_clipboard_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        limit_spin = QSpinBox()
        limit_spin.setRange(50, 5000)
        limit_spin.setValue(int(self._config.get("clipboard.history_limit", 500)))
        limit_spin.valueChanged.connect(
            lambda v: self._config.set("clipboard.history_limit", int(v))
        )
        form.addRow("历史上限（条）", limit_spin)

        image_spin = QSpinBox()
        image_spin.setRange(1, 100)
        image_spin.setValue(int(self._config.get("clipboard.max_image_mb", 20)))
        image_spin.valueChanged.connect(
            lambda v: self._config.set("clipboard.max_image_mb", int(v))
        )
        form.addRow("图片上限（MB）", image_spin)
        return page

    # -- 工具 ------------------------------------------------------------------

    def _build_tools_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        labels = {
            "screenshot": "截图置顶",
            "clipboard": "粘贴板",
            "color_picker": "取色器",
        }
        self._tool_checks: dict[str, QCheckBox] = {}
        tools = self._config.get("tools", {}) or {}
        for tool_id in self._tool_ids:
            check = QCheckBox()
            check.setChecked(bool(tools.get(tool_id, True)))
            check.toggled.connect(
                lambda checked, tid=tool_id: self._on_tool_toggled(tid, checked)
            )
            self._tool_checks[tool_id] = check
            form.addRow(f"{labels.get(tool_id, tool_id)}：", check)
        return page

    def _on_tool_toggled(self, tool_id: str, checked: bool) -> None:
        self._config.set(f"tools.{tool_id}", bool(checked))
        self.settings_changed.emit()
