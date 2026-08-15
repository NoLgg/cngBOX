"""main_window — 主面板（手绘便当盒布局）。

铅笔手绘风 × Bento Grid：
- 无边框窗口 + 自绘标题栏（拖动移动、贴纸感）
- 米色纸张背景 + 虚线边框卡片 + 硬阴影
- 便当盒不规则网格：横幅贴纸、吉祥物大卡、工具卡、状态卡
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cng_toolbox.resources import load_pixmap
from cng_toolbox.shell.tool_registry import ToolRegistry

# 工具 id -> 图标资源文件名
TOOL_ICONS = {
    "screenshot": "icon-tool-screenshot",
    "clipboard": "icon-tool-clipboard",
    "color_picker": "icon-tool-colorpicker",
    "settings": "icon-settings",
}

INK = "#2c2c2c"
PAPER = "#f5f0e8"
PAPER_DEEP = "#e8e2d8"
PAPER_INPUT = "#faf5ed"
TEAL_DEEP = "#2f6f66"
ORANGE = "#d99a3d"
INK_SOFT = "#5a5a5a"


def _hard_shadow(widget: QWidget, offset: int = 3, blur: int = 0) -> None:
    """贴纸硬阴影（铅笔投影）。"""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setOffset(offset, offset)
    effect.setBlurRadius(blur)
    effect.setColor(QColor(44, 44, 44, 80))
    widget.setGraphicsEffect(effect)


class SketchCard(QFrame):
    """手绘虚线边框卡片（悬停上浮动画）。"""

    clicked = Signal(str)  # tool_id

    def __init__(self, tool_id: str = "") -> None:
        super().__init__()
        self._tool_id = tool_id
        self.setObjectName("Card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(170, 150)
        self._hover_anim: QPropertyAnimation | None = None
        _hard_shadow(self)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._tool_id:
            self.clicked.emit(self._tool_id)

    def enterEvent(self, event) -> None:
        """悬停：轻微上浮（便当盒交互反馈）。"""
        self._animate_hover(-3)

    def leaveEvent(self, event) -> None:
        self._animate_hover(0)

    def _animate_hover(self, dy: int) -> None:
        from PySide6.QtCore import QEasingCurve

        self._hover_anim = QPropertyAnimation(self, b"pos", self)
        self._hover_anim.setDuration(110)
        self._hover_anim.setStartValue(self.pos())
        self._hover_anim.setEndValue(QPoint(self.x(), self.y() + dy))
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_anim.start()


class TitleBar(QWidget):
    """自绘标题栏：吉祥物 + 标题 + 设置按钮 + 关闭。"""

    settings_clicked = Signal()

    def __init__(self, parent: QMainWindow) -> None:
        super().__init__(parent)
        self._win = parent
        self._drag_pos: QPoint | None = None
        self.setFixedHeight(52)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)

        # 吉祥物小图
        mascot = load_pixmap("mascot-full")
        mascot_label = QLabel()
        if not mascot.isNull():
            mascot_label.setPixmap(
                mascot.scaled(34, 34, Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
            )
        layout.addWidget(mascot_label)

        title = QLabel("草泥鸽工具箱")
        title.setStyleSheet(
            f"font-family: 'KaiTi','楷体'; font-size: 19px; font-weight: bold;"
            f"color: {INK}; letter-spacing: 2px;"
        )
        layout.addWidget(title)

        layout.addStretch(1)

        settings_btn = QPushButton("设置")
        settings_btn.setObjectName("Primary")
        settings_icon = load_pixmap(TOOL_ICONS["settings"])
        if not settings_icon.isNull():
            settings_btn.setIcon(settings_icon)
        settings_btn.clicked.connect(self.settings_clicked)
        layout.addWidget(settings_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet(
            f"QPushButton {{ background: {PAPER}; border: 2px dashed {INK};"
            f"border-radius: 6px; font-size: 13px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: #c96a5e; color: {PAPER}; }}"
        )
        close_btn.clicked.connect(parent.close)
        layout.addWidget(close_btn)

    # -- 拖动窗口 -------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self._win.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self._win.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None


class MainWindow(QMainWindow):
    """工具箱主面板（手绘便当盒）。"""

    tool_invoked = Signal(str)  # tool_id

    def __init__(self, registry: ToolRegistry, hotkey_texts: dict[str, str]) -> None:
        super().__init__()
        self._registry = registry
        self._hotkey_texts = hotkey_texts
        # 无边框窗口：边框/背景全部由内部手绘风格呈现。
        # 注意：不加 WindowStaysOnTopHint —— 主面板不需要一直置顶，
        # 否则会压住设置窗口/其他应用（设置窗口置顶逻辑问题修复）。
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle("草泥鸽工具箱")
        self.resize(860, 620)
        self._build()

    def showEvent(self, event) -> None:
        """显示时置顶 + 淡入动画。"""
        super().showEvent(event)
        self.raise_()
        self.activateWindow()

    def _build(self) -> None:
        # 外层容器：纸张背景 + 墨线边框 + 贴纸阴影（模拟窗口边框）
        outer = QWidget()
        outer.setObjectName("WindowShell")
        outer.setStyleSheet(
            f"#WindowShell {{ background: {PAPER};"
            f"border: 3px solid {INK}; border-radius: 10px; }}"
        )
        self.setCentralWidget(outer)
        _hard_shadow(outer, offset=8, blur=0)

        main_layout = QVBoxLayout(outer)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 自绘标题栏
        title_bar = TitleBar(self)
        title_bar.settings_clicked.connect(lambda: self.tool_invoked.emit("settings"))
        main_layout.addWidget(title_bar)

        # 内容区
        content = QWidget()
        content.setStyleSheet(f"background: {PAPER};")
        body = QVBoxLayout(content)
        body.setContentsMargins(22, 14, 22, 20)
        body.setSpacing(16)
        main_layout.addWidget(content, 1)

        # 横幅贴纸（白底图 + 虚线框 + 轻微旋转感）
        banner = self._make_banner()
        body.addWidget(banner)

        # 便当盒网格
        grid = QGridLayout()
        grid.setSpacing(16)
        self._layout_bento(grid)
        body.addLayout(grid, 1)

        footer = QLabel("纯本地运行 · 无网络依赖 · 右键贴图有更多选项")
        footer.setStyleSheet(
            f"color: {INK_SOFT}; font-size: 11.5px;"
            f"font-family: 'KaiTi','楷体'; padding-top: 6px;"
        )
        footer.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        body.addWidget(footer)

    # -- 横幅 ------------------------------------------------------------------

    def _make_banner(self) -> QWidget:
        wrap = QFrame()
        wrap.setStyleSheet(
            f"QFrame {{ background: #ffffff; border: 2px solid {INK};"
            f"border-radius: 8px; }}"
        )
        _hard_shadow(wrap, offset=3)
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        img = load_pixmap("banner-startup")
        if not img.isNull():
            label = QLabel()
            label.setPixmap(img.scaled(
                816, 240, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            ))
            label.setFixedHeight(190)
            label.setScaledContents(False)
            lay.addWidget(label)
        else:
            t = QLabel("草泥鸽工具箱 · 一只鸽子全搞定")
            t.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {INK}; padding: 40px;")
            lay.addWidget(t)
        return wrap

    # -- 便当盒网格 -------------------------------------------------------------

    def _layout_bento(self, grid: QGridLayout) -> None:
        # 吉祥物大卡（2x2）
        mascot_card = SketchCard()
        m_layout = QVBoxLayout(mascot_card)
        m_layout.setContentsMargins(14, 14, 14, 10)
        m_layout.setSpacing(4)
        mascot_img = load_pixmap("mascot-full")
        if not mascot_img.isNull():
            m_label = QLabel()
            m_label.setPixmap(mascot_img.scaled(
                220, 220, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
            m_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            m_layout.addWidget(m_label, 1)
        m_name = QLabel("草泥鸽 · 咕咕")
        m_name.setStyleSheet(
            f"font-family: 'KaiTi','楷体'; font-size: 17px; font-weight: bold;"
            f"color: {ORANGE};"
        )
        m_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        m_layout.addWidget(m_name)
        m_tag = QLabel("看板娘 · 身兼数职 · 只吃小米")
        m_tag.setStyleSheet(f"font-family: 'KaiTi','楷体'; color: {INK_SOFT}; font-size: 12px;")
        m_tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        m_layout.addWidget(m_tag)
        grid.addWidget(mascot_card, 0, 0, 2, 2)

        # 工具卡：从第 3 列开始排（0,2)(0,3)(1,2)，第 3 个落在 (1,3) 之前由状态卡占据
        tools = self._registry.enabled()
        positions = [(0, 2), (0, 3), (1, 2)]
        for tool, (row, col) in zip(tools, positions):
            card = self._make_tool_card(tool.tool_id, tool.name, tool.description,
                                        tool.hotkey_id or None)
            grid.addWidget(card, row, col)

        # 状态卡（1,3）：真实数据由 update_status 刷新
        self._status_card = self._make_status_card()
        grid.addWidget(self._status_card, 1, 3)

        # 关闭全部贴图 + 设置卡（第 3 行）
        close_card = self._make_close_pins_card()
        grid.addWidget(close_card, 2, 0, 1, 2)
        settings_card = self._make_settings_card()
        grid.addWidget(settings_card, 2, 2, 1, 2)

    def _make_tool_card(self, tool_id: str, name: str, desc: str,
                        hotkey_id: str | None) -> SketchCard:
        card = SketchCard(tool_id)
        card.clicked.connect(self.tool_invoked.emit)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 12)
        layout.setSpacing(6)

        hotkey = self._hotkey_texts.get(hotkey_id or "", "")
        if hotkey:
            hotkey_label = QLabel(hotkey)
            hotkey_label.setObjectName("CardHotkey")
            hotkey_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            layout.addWidget(hotkey_label)

        icon_box = QFrame()
        icon_box.setFixedSize(58, 58)
        icon_box.setStyleSheet(
            f"QFrame {{ background: {PAPER_DEEP}; border: 2px solid {INK};"
            f"border-radius: 7px; }}"
        )
        icon_lay = QVBoxLayout(icon_box)
        icon_lay.setContentsMargins(6, 6, 6, 6)
        pixmap = load_pixmap(TOOL_ICONS.get(tool_id, ""))
        if not pixmap.isNull():
            icon_label = QLabel()
            icon_label.setPixmap(pixmap.scaled(
                44, 44, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
            icon_lay.addWidget(icon_label)
        layout.addWidget(icon_box)

        title = QLabel(name)
        title.setObjectName("CardTitle")
        layout.addWidget(title)

        desc_label = QLabel(desc)
        desc_label.setObjectName("CardDesc")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        return card

    def _make_status_card(self) -> SketchCard:
        card = SketchCard()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)
        dot = QLabel("●")
        dot.setStyleSheet(f"color: #6b9e62; font-size: 14px;")
        layout.addWidget(dot)
        self._status_pins = QLabel("0")
        self._status_pins.setStyleSheet(
            f"font-family: 'KaiTi','楷体'; font-size: 26px; font-weight: bold;"
            f"color: {TEAL_DEEP};"
        )
        layout.addWidget(self._status_pins)
        label = QLabel("贴图在屏")
        label.setStyleSheet(f"color: {INK_SOFT}; font-size: 12px;")
        layout.addWidget(label)
        return card

    def update_status(self, pins: int) -> None:
        """刷新状态卡真实数据。"""
        if hasattr(self, "_status_pins"):
            self._status_pins.setText(str(pins))

    def _make_close_pins_card(self) -> SketchCard:
        card = SketchCard("close_pins")
        card.clicked.connect(self.tool_invoked.emit)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        icon_box = QFrame()
        icon_box.setFixedSize(44, 44)
        icon_box.setStyleSheet(
            f"QFrame {{ background: {PAPER_DEEP}; border: 2px solid {INK};"
            f"border-radius: 7px; }}"
        )
        icon_lay = QVBoxLayout(icon_box)
        icon_lay.setContentsMargins(4, 4, 4, 4)
        pixmap = load_pixmap("icon-pin")
        if not pixmap.isNull():
            icon_label = QLabel()
            icon_label.setPixmap(pixmap.scaled(
                34, 34, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
            icon_lay.addWidget(icon_label)
        layout.addWidget(icon_box)
        text_lay = QVBoxLayout()
        text_lay.setSpacing(2)
        title = QLabel("关闭全部贴图")
        title.setObjectName("CardTitle")
        text_lay.addWidget(title)
        desc = QLabel("一键清空屏幕上的所有置顶贴图")
        desc.setObjectName("CardDesc")
        text_lay.addWidget(desc)
        layout.addLayout(text_lay)
        layout.addStretch(1)
        return card

    def _make_settings_card(self) -> SketchCard:
        card = SketchCard("settings")
        card.clicked.connect(self.tool_invoked.emit)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        icon_box = QFrame()
        icon_box.setFixedSize(44, 44)
        icon_box.setStyleSheet(
            f"QFrame {{ background: {PAPER_DEEP}; border: 2px solid {INK};"
            f"border-radius: 7px; }}"
        )
        icon_lay = QVBoxLayout(icon_box)
        icon_lay.setContentsMargins(4, 4, 4, 4)
        pixmap = load_pixmap(TOOL_ICONS["settings"])
        if not pixmap.isNull():
            icon_label = QLabel()
            icon_label.setPixmap(pixmap.scaled(
                34, 34, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))
            icon_lay.addWidget(icon_label)
        layout.addWidget(icon_box)
        text_lay = QVBoxLayout()
        text_lay.setSpacing(2)
        title = QLabel("设置")
        title.setObjectName("CardTitle")
        text_lay.addWidget(title)
        desc = QLabel("热键 · 外观 · 贴图边框 · 开机自启 · 工具开关")
        desc.setObjectName("CardDesc")
        text_lay.addWidget(desc)
        layout.addLayout(text_lay)
        layout.addStretch(1)
        return card

    # -- 生命周期 ----------------------------------------------------------------

    def closeEvent(self, event) -> None:
        # 关闭主窗口不退出（托盘常驻），仅隐藏
        event.ignore()
        self.hide()

    def rebuild(self, registry: ToolRegistry, hotkey_texts: dict[str, str]) -> None:
        """工具开关变更后重建。"""
        self._registry = registry
        self._hotkey_texts = hotkey_texts
        self._build()
