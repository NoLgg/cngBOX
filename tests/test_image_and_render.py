"""ImageStore 与文本贴图渲染测试。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cng_toolbox.storage.image_store import ImageStore, hash_bytes
from cng_toolbox.tools.clipboard_tool import render_text_pixmap
from cng_toolbox.tools.color_picker import rgb_to_hex


def test_hash_bytes_stable() -> None:
    assert hash_bytes(b"abc") == hash_bytes(b"abc")
    assert hash_bytes(b"abc") != hash_bytes(b"abd")


def test_image_store_save_and_path(tmp_path: Path) -> None:
    store = ImageStore(tmp_path / "images")
    h = store.save(b"\x89PNG fake bytes")
    p = store.path_for(h)
    assert p is not None and p.exists()
    assert p.name == f"{h}.png"


def test_image_store_remove(tmp_path: Path) -> None:
    store = ImageStore(tmp_path / "images")
    h = store.save(b"\x89PNG fake bytes")
    store.remove(h)
    assert store.path_for(h) is None


def test_rgb_to_hex() -> None:
    assert rgb_to_hex(0, 0, 0) == "#000000"
    assert rgb_to_hex(255, 255, 255) == "#FFFFFF"
    assert rgb_to_hex(45, 212, 191) == "#2DD4BF"


def test_render_text_pixmap(qapp) -> None:
    pm = render_text_pixmap("hello 草泥鸽")
    assert not pm.isNull()
    assert pm.width() > 0 and pm.height() > 0


def test_render_text_pixmap_multiline(qapp) -> None:
    pm = render_text_pixmap("line1\nline2\n\nline4")
    assert not pm.isNull()
