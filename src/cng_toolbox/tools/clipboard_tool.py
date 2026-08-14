"""clipboard_tool — 剪贴板监听 + 历史 + 贴屏。

- 监听 QClipboard.dataChanged：文本/图片分类、hash 去重、体积上限、
  自身写入防回环。
- 历史面板：列表展示（文本预览 / 图片大缩略图）、类型筛选、搜索、
  单击复制、右键固定/删除/贴屏、双击图片放大预览。
- 贴屏：文本自动排版为贴图（最大宽度 TEXT_PIN_MAX_WIDTH），图片原尺寸。
"""

from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from cng_toolbox.config import TEXT_PIN_MAX_WIDTH
from cng_toolbox.shell.config_store import ConfigStore
from cng_toolbox.storage.history_db import HistoryDB
from cng_toolbox.storage.image_store import ImageStore, hash_bytes

SELF_WRITE_WINDOW_MS = 500


def _hash_text(text: str) -> str:
    return hash_bytes(text.encode("utf-8", errors="replace"))


def render_text_pixmap(text: str, max_width: int = TEXT_PIN_MAX_WIDTH) -> QPixmap:
    """将文本排版为贴图 pixmap（自动换行）。"""
    from PySide6.QtGui import QFontMetrics

    font = QFont("Microsoft YaHei UI", 12)
    fm = QFontMetrics(font)
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for word in paragraph:
            trial = current + word
            if fm.horizontalAdvance(trial) > max_width and current:
                lines.append(current)
                current = word
            else:
                current = trial
        lines.append(current)
    line_height = fm.height() + 4
    width = max_width
    height = max(1, line_height * len(lines)) + 16
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor(26, 29, 36))
    painter = QPainter(pixmap)
    painter.setFont(font)
    painter.setPen(QColor("#e8ecf3"))
    y = 8
    for line in lines:
        painter.drawText(8, y + fm.ascent(), line)
        y += line_height
    painter.end()
    return pixmap


class HistoryPanel(QDialog):
    """剪贴板历史面板。"""

    copied = Signal()  # 条目被复制（供外部提示）
    pinned_changed = Signal()
    deleted = Signal()
    clip_to_screen = Signal(object)  # entry dict

    def __init__(
        self,
        db: HistoryDB,
        image_store: ImageStore,
        config: ConfigStore,
        parent: QWidget | None = None,
        on_self_copy=None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._images = image_store
        self._config = config
        self._on_self_copy = on_self_copy  # 回调：自身复制标记（防回环）
        self.setWindowTitle("粘贴板 — 剪贴板历史")
        self.resize(520, 620)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("搜索历史…")
        self._search.textChanged.connect(self._reload)
        self._filter = QComboBox()
        self._filter.addItems(["全部", "文本", "图片"])
        self._filter.currentIndexChanged.connect(self._reload)
        top.addWidget(self._search, 1)
        top.addWidget(self._filter)
        layout.addLayout(top)

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._list, 1)

        self._reload()

    # -- 数据加载 ----------------------------------------------------------------

    def _type_filter(self) -> str | None:
        idx = self._filter.currentIndex()
        return {0: None, 1: "text", 2: "image"}[idx]

    def _reload(self) -> None:
        self._list.clear()
        entries = self._db.list_entries(
            limit=self._config.get("clipboard.history_limit", 500),
            type_filter=self._type_filter(),
            search=self._search.text().strip() or None,
        )
        for entry in entries:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, entry)
            widget = self._build_item_widget(entry)
            item.setSizeHint(widget.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, widget)

    def _build_item_widget(self, entry: dict) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        header = QHBoxLayout()
        type_label = QLabel("📄 文本" if entry["type"] == "text" else "🖼️ 图片")
        type_label.setStyleSheet("color: #2dd4bf; font-size: 11px;")
        header.addWidget(type_label)
        header.addStretch(1)
        time_label = QLabel(self._format_time(entry["created_at"]))
        time_label.setStyleSheet("color: #9aa4b5; font-size: 10px;")
        header.addWidget(time_label)
        if entry["pinned"]:
            pin_label = QLabel("📌")
            pin_label.setStyleSheet("font-size: 10px;")
            header.addWidget(pin_label)
        layout.addLayout(header)

        if entry["type"] == "text":
            text = entry["text_content"] or ""
            preview = text.replace("\n", " ")[:120]
            label = QLabel(preview)
            label.setWordWrap(True)
            label.setStyleSheet("color: #e8ecf3;")
            layout.addWidget(label)
        else:
            thumb = self._images.thumbnail(entry["content_hash"])
            img_label = QLabel()
            if thumb and not thumb.isNull():
                img_label.setPixmap(thumb)
            else:
                img_label.setText("(图片不可用)")
            img_label.setStyleSheet("color: #9aa4b5;")
            layout.addWidget(img_label)
        return container

    @staticmethod
    def _format_time(ts: int) -> str:
        import datetime

        return datetime.datetime.fromtimestamp(ts).strftime("%m-%d %H:%M")

    # -- 交互 --------------------------------------------------------------------

    def _entry_of(self, item: QListWidgetItem | None) -> dict | None:
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        entry = self._entry_of(item)
        if entry is None:
            return
        self._copy_entry(entry)

    def _copy_entry(self, entry: dict) -> None:
        if entry["type"] == "text":
            QApplication.clipboard().setText(entry["text_content"] or "")
            if self._on_self_copy:
                self._on_self_copy(entry)
        else:
            pm = self._images.load_pixmap(entry["content_hash"])
            if pm:
                QApplication.clipboard().setPixmap(pm)
                if self._on_self_copy:
                    self._on_self_copy(entry)
        self.copied.emit()

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        entry = self._entry_of(item)
        if entry is not None and entry["type"] == "image":
            self._show_image_preview(entry)

    def _show_image_preview(self, entry: dict) -> None:
        pm = self._images.load_pixmap(entry["content_hash"])
        if pm is None or pm.isNull():
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("图片预览")
        layout = QVBoxLayout(dialog)
        scroll = QScrollArea()
        label = QLabel()
        label.setPixmap(pm)
        scroll.setWidget(label)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        dialog.resize(min(pm.width() + 40, 900), min(pm.height() + 40, 700))
        dialog.exec()

    def _on_context_menu(self, pos) -> None:
        item = self._list.itemAt(pos)
        entry = self._entry_of(item)
        if entry is None:
            return
        menu = QMenu(self._list)
        act_copy = menu.addAction("复制")
        act_pin = menu.addAction("取消固定" if entry["pinned"] else "固定")
        act_clip = menu.addAction("贴屏")
        menu.addSeparator()
        act_del = menu.addAction("删除")
        chosen = menu.exec(self._list.mapToGlobal(pos))
        if chosen == act_copy:
            self._copy_entry(entry)
        elif chosen == act_pin:
            self._db.set_pinned(entry["id"], not entry["pinned"])
            self._reload()
        elif chosen == act_clip:
            self.clip_to_screen.emit(entry)
        elif chosen == act_del:
            self._db.delete(entry["id"])
            self.deleted.emit()
            self._reload()

    def refresh(self) -> None:
        self._reload()


class ClipboardTool(QObject):
    """剪贴板监听 + 贴屏入口。"""

    entry_added = Signal()
    clipboard_too_big = Signal()
    clip_empty = Signal()

    def __init__(
        self,
        config: ConfigStore,
        db: HistoryDB,
        image_store: ImageStore,
        pin_manager,
    ) -> None:
        super().__init__()
        self._config = config
        self._db = db
        self._images = image_store
        self._pins = pin_manager
        self._last_self_write: tuple[float, str | None] = (0.0, None)
        self._last_hash: str | None = None
        self._panel: HistoryPanel | None = None
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(120)
        self._debounce.timeout.connect(self._on_data_changed)

    # -- 监听 --------------------------------------------------------------------

    def start(self) -> None:
        QApplication.clipboard().dataChanged.connect(self._debounce.start)

    def stop(self) -> None:
        QApplication.clipboard().dataChanged.disconnect(self._debounce.start)

    def _on_data_changed(self) -> None:
        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()

        # 防回环：自身写入窗口内且 hash 一致 → 忽略
        if mime.hasText():
            text = mime.text()
            h = _hash_text(text)
        elif mime.hasImage():
            image = clipboard.image()
            if image.isNull():
                return
            h = hash_bytes(image_bytes(image))
        else:
            return

        now = time.monotonic()
        if self._last_self_write[0] and (now - self._last_self_write[0]) * 1000 < SELF_WRITE_WINDOW_MS:
            if self._last_self_write[1] == h:
                return

        if h == self._last_hash:
            return  # 连续相同内容去重

        self._last_hash = h

        if mime.hasText():
            self._db.upsert_text(text, h)
            self._cleanup()
            self.entry_added.emit()
        elif mime.hasImage():
            image = clipboard.image()
            max_bytes = self._config.get("clipboard.max_image_mb", 20) * 1024 * 1024
            if len(image_bytes(image)) > max_bytes:
                self.clipboard_too_big.emit()
                return
            data = image_bytes(image)
            self._images.save(data)
            self._db.upsert_image(h, str(self._images.path_for(h)))
            self._cleanup()
            self.entry_added.emit()

    def _cleanup(self) -> None:
        limit = self._config.get("clipboard.history_limit", 500)
        orphan_paths = self._db.cleanup(limit)
        for p in orphan_paths:
            self._images.remove_by_path(p)

    # -- 自身写入标记 --------------------------------------------------------------

    def mark_self_write(self, content_hash: str | None) -> None:
        self._last_self_write = (time.monotonic(), content_hash)

    def mark_self_write_text(self, text: str) -> None:
        self.mark_self_write(_hash_text(text))

    def mark_self_write_pixmap(self, pixmap) -> None:
        self.mark_self_write(hash_bytes(image_bytes(pixmap.toImage())))

    # -- 贴屏 ----------------------------------------------------------------------

    def clip_to_screen(self) -> None:
        """把剪贴板内容贴到屏幕（托盘/面板入口）。"""
        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()
        if mime.hasImage():
            pm = clipboard.pixmap()
            if not pm.isNull():
                self._pins.create(pm, title="贴屏")
                return
        if mime.hasText():
            text = mime.text()
            if text.strip():
                pixmap = render_text_pixmap(text)
                self._pins.create(pixmap, title="文本贴图")
                return
        self.clip_empty.emit()

    def clip_entry_to_screen(self, entry: dict) -> None:
        """从历史面板条目贴屏。"""
        if entry["type"] == "text":
            pixmap = render_text_pixmap(entry["text_content"] or "")
            self._pins.create(pixmap, title="文本贴图")
        else:
            pm = self._images.load_pixmap(entry["content_hash"])
            if pm:
                self._pins.create(pm, title="贴屏")

    # -- 面板 ----------------------------------------------------------------------

    def show_panel(self) -> None:
        if self._panel is None:
            self._panel = HistoryPanel(
                self._db, self._images, self._config,
                on_self_copy=self._mark_entry_self_write,
            )
            self._panel.clip_to_screen.connect(self.clip_entry_to_screen)
        self._panel.refresh()
        self._panel.show()
        self._panel.raise_()
        self._panel.activateWindow()

    def _mark_entry_self_write(self, entry: dict) -> None:
        if entry["type"] == "text":
            self.mark_self_write_text(entry["text_content"] or "")
        else:
            pm = self._images.load_pixmap(entry["content_hash"])
            if pm:
                self.mark_self_write_pixmap(pm)


def image_bytes(image: QImage) -> bytes:
    """QImage -> PNG bytes。"""
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice

    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buf, "PNG")
    buf.close()
    return bytes(ba.data())
