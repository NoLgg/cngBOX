"""ImageStore — 图片文件存取 + 缩略图 LRU 缓存。

图片以 content_hash 命名存储：<app_dir>/images/<hash>.png。
缩略图（最长边 512px）内存缓存，LRU 上限 100 张。
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from pathlib import Path

from PySide6.QtGui import QImage, QPixmap

THUMB_MAX_EDGE = 512
CACHE_LIMIT = 100


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ImageStore:
    def __init__(self, images_dir: Path | str) -> None:
        self._dir = Path(images_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._thumbs: OrderedDict[str, QPixmap] = OrderedDict()

    # -- 写入 ------------------------------------------------------------------

    def save(self, data: bytes) -> str:
        """保存图片字节，返回 content_hash。"""
        content_hash = hash_bytes(data)
        path = self._dir / f"{content_hash}.png"
        if not path.exists():
            path.write_bytes(data)
        return content_hash

    def save_from_image(self, image: QImage) -> str:
        ba = bytearray()
        buf = bytes(ba)
        image.save(buf, "PNG")  # type: ignore[arg-type]
        return self.save(bytes(buf))

    def path_for(self, content_hash: str) -> Path | None:
        p = self._dir / f"{content_hash}.png"
        return p if p.exists() else None

    # -- 读取 ------------------------------------------------------------------

    def load_pixmap(self, content_hash: str) -> QPixmap | None:
        p = self.path_for(content_hash)
        if p is None:
            return None
        return QPixmap(str(p))

    def thumbnail(self, content_hash: str) -> QPixmap | None:
        """取缩略图（LRU 缓存）。"""
        if content_hash in self._thumbs:
            self._thumbs.move_to_end(content_hash)
            return self._thumbs[content_hash]
        pm = self.load_pixmap(content_hash)
        if pm is None or pm.isNull():
            return None
        scaled = pm.scaled(
            THUMB_MAX_EDGE,
            THUMB_MAX_EDGE,
            aspectMode=1,  # KeepAspectRatio
            mode=1,  # SmoothTransformation
        )
        self._thumbs[content_hash] = scaled
        while len(self._thumbs) > CACHE_LIMIT:
            self._thumbs.popitem(last=False)
        return scaled

    # -- 维护 ------------------------------------------------------------------

    def remove(self, content_hash: str) -> None:
        self._thumbs.pop(content_hash, None)
        p = self.path_for(content_hash)
        if p:
            try:
                p.unlink()
            except OSError:
                pass

    def remove_by_path(self, image_path: str) -> None:
        """按存储路径删除（供 cleanup 孤儿清理用）。"""
        p = Path(image_path)
        self._thumbs.pop(p.stem, None)
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass
