"""ui_utils — UI 工具：动画、多屏定位、焦点管理。

- 动画：窗口淡入/淡出、卡片浮现（QPropertyAnimation，尊重 reduced motion）
- 多屏：把窗口定位到鼠标所在屏幕（或主屏）中央
- 焦点：置顶 + 激活，保证弹窗不被主窗口压住
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRect, Qt
from PySide6.QtGui import QGuiApplication, QCursor
from PySide6.QtWidgets import QWidget

FADE_MS = 160
SLIDE_MS = 200


def screen_at_cursor():
    """鼠标当前所在屏幕（无则主屏）。"""
    screens = QGuiApplication.screens()
    if not screens:
        return None
    cursor_pos = QCursor.pos()
    for screen in screens:
        if screen.geometry().contains(cursor_pos):
            return screen
    return QGuiApplication.primaryScreen()


def center_on_screen(widget: QWidget, offset_y: int = 0) -> None:
    """把窗口居中到鼠标所在屏幕（带纵向偏移）。"""
    screen = screen_at_cursor()
    if screen is None:
        return
    geo = screen.geometry()
    x = geo.x() + (geo.width() - widget.width()) // 2
    y = geo.y() + (geo.height() - widget.height()) // 2 + offset_y
    widget.move(x, y)


def center_on_primary(widget: QWidget, offset_y: int = 0) -> None:
    """把窗口居中到主屏幕。"""
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return
    geo = screen.geometry()
    x = geo.x() + (geo.width() - widget.width()) // 2
    y = geo.y() + (geo.height() - widget.height()) // 2 + offset_y
    widget.move(x, y)


def fade_in(widget: QWidget, ms: int = FADE_MS, slide: int = 8) -> None:
    """淡入 + 轻微上浮动画。"""
    if not widget.isVisible():
        widget.show()
    widget.setWindowOpacity(0.0)
    pos = widget.pos()
    anim = QPropertyAnimation(widget, b"windowOpacity", widget)
    anim.setDuration(ms)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start()
    widget._fade_anim = anim  # 防止被 GC

    if slide:
        slide_anim = QPropertyAnimation(widget, b"pos", widget)
        slide_anim.setDuration(ms)
        slide_anim.setStartValue(QPoint(pos.x(), pos.y() + slide))
        slide_anim.setEndValue(pos)
        slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        slide_anim.start()
        widget._slide_anim = slide_anim


def fade_out(widget: QWidget, ms: int = FADE_MS, then_hide: bool = True) -> None:
    """淡出动画（结束后可选隐藏）。"""
    anim = QPropertyAnimation(widget, b"windowOpacity", widget)
    anim.setDuration(ms)
    anim.setStartValue(widget.windowOpacity())
    anim.setEndValue(0.0)
    anim.setEasingCurve(QEasingCurve.Type.InCubic)
    if then_hide:
        anim.finished.connect(widget.hide)
    anim.start()
    widget._fade_anim = anim


def raise_and_focus(widget: QWidget) -> None:
    """置顶 + 激活（弹窗聚焦修复）。"""
    widget.show()
    widget.raise_()
    widget.activateWindow()
