"""main_window — 主面板（工具箱卡片网格）。

游戏化个性风格：深色卡片 + emoji 图标 + 高亮主色热键徽章。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cng_toolbox.shell.tool_registry import ToolRegistry


class ToolCard(QWidget):
    """一张工具卡片。"""

    clicked = Signal(str)  # tool_id

    def __init__(self, tool_id: str, icon: str, name: str,
                 description: str, hotkey_text: str | None) -> None:
        super().__init__()
        self._tool_id = tool_id
        self.setObjectName("Card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(180, 150)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        icon_label = QLabel(icon)
        icon_label.setObjectName("CardIcon")
        layout.addWidget(icon_label)

        title_label = QLabel(name)
        title_label.setObjectName("CardTitle")
        layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setObjectName("CardDesc")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        layout.addStretch(1)

        if hotkey_text:
            hotkey_label = QLabel(hotkey_text)
            hotkey_label.setObjectName("CardHotkey")
            hotkey_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(hotkey_label)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._tool_id)


class MainWindow(QMainWindow):
    """工具箱主面板。"""

    tool_invoked = Signal(str)  # tool_id

    def __init__(self, registry: ToolRegistry, hotkey_texts: dict[str, str]) -> None:
        super().__init__()
        self._registry = registry
        self._hotkey_texts = hotkey_texts
        self.setWindowTitle("草泥鸽工具箱")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(760, 420)

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(20, 16, 20, 16)
        outer.setSpacing(14)

        # 标题区
        header = QHBoxLayout()
        title = QLabel("🐦 草泥鸽工具箱")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        header.addWidget(title)
        header.addStretch(1)
        settings_btn = QPushButton("⚙️ 设置")
        settings_btn.setObjectName("Primary")
        settings_btn.clicked.connect(lambda: self.tool_invoked.emit("settings"))
        header.addWidget(settings_btn)
        outer.addLayout(header)

        # 卡片网格
        grid = QGridLayout()
        grid.setSpacing(14)
        col = 0
        row = 0
        for tool in self._registry.enabled():
            card = ToolCard(
                tool.tool_id, tool.icon, tool.name, tool.description,
                self._hotkey_texts.get(tool.hotkey_id or "", tool.hotkey_id or None),
            )
            card.clicked.connect(self.tool_invoked.emit)
            grid.addWidget(card, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1
        outer.addLayout(grid, 1)

        footer = QLabel("纯本地运行 · 无网络依赖 · 右键贴图有更多选项")
        footer.setStyleSheet("color: #9aa4b5; font-size: 11px;")
        outer.addWidget(footer, 0, Qt.AlignmentFlag.AlignHCenter)

    def closeEvent(self, event) -> None:
        # 关闭主窗口不退出（托盘常驻），仅隐藏
        event.ignore()
        self.hide()

    def rebuild(self, registry: ToolRegistry, hotkey_texts: dict[str, str]) -> None:
        """工具开关变更后重建卡片网格。"""
        self._registry = registry
        self._hotkey_texts = hotkey_texts
        old = self.centralWidget()
        if old is not None:
            old.setParent(None)
            old.deleteLater()
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(20, 16, 20, 16)
        outer.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("🐦 草泥鸽工具箱")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        header.addWidget(title)
        header.addStretch(1)
        settings_btn = QPushButton("⚙️ 设置")
        settings_btn.setObjectName("Primary")
        settings_btn.clicked.connect(lambda: self.tool_invoked.emit("settings"))
        header.addWidget(settings_btn)
        outer.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(14)
        col = 0
        row = 0
        for tool in registry.enabled():
            card = ToolCard(
                tool.tool_id, tool.icon, tool.name, tool.description,
                hotkey_texts.get(tool.hotkey_id or "", None),
            )
            card.clicked.connect(self.tool_invoked.emit)
            grid.addWidget(card, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1
        outer.addLayout(grid, 1)

        footer = QLabel("纯本地运行 · 无网络依赖 · 右键贴图有更多选项")
        footer.setStyleSheet("color: #9aa4b5; font-size: 11px;")
        outer.addWidget(footer, 0, Qt.AlignmentFlag.AlignHCenter)
