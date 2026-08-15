"""HistoryDB 单元测试：CRUD、去重、清理、固定保护、筛选搜索。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cng_toolbox.storage.history_db import HistoryDB


@pytest.fixture()
def db(tmp_path: Path) -> HistoryDB:
    return HistoryDB(tmp_path / "test.db")


def test_upsert_text_dedup(db: HistoryDB) -> None:
    id1 = db.upsert_text("hello", "hash-1")
    id2 = db.upsert_text("hello", "hash-1")  # 同 hash 去重 → 更新
    assert id1 == id2
    entries = db.list_entries()
    assert len(entries) == 1


def test_list_entries_order(db: HistoryDB) -> None:
    db.upsert_text("first", "h1")
    db.upsert_text("second", "h2")
    db.upsert_image("himg", "/tmp/a.png")
    entries = db.list_entries()
    assert [e["text_content"] for e in entries] == [None, "second", "first"]


def test_type_filter(db: HistoryDB) -> None:
    db.upsert_text("text-item", "h1")
    db.upsert_image("himg", "/tmp/a.png")
    texts = db.list_entries(type_filter="text")
    images = db.list_entries(type_filter="image")
    assert len(texts) == 1 and texts[0]["type"] == "text"
    assert len(images) == 1 and images[0]["type"] == "image"


def test_search(db: HistoryDB) -> None:
    db.upsert_text("alpha beta", "h1")
    db.upsert_text("gamma delta", "h2")
    found = db.list_entries(search="beta")
    assert len(found) == 1 and found[0]["text_content"] == "alpha beta"


def test_pinned(db: HistoryDB) -> None:
    eid = db.upsert_text("keep me", "h1")
    db.set_pinned(eid, True)
    entry = db.get(eid)
    assert entry is not None and entry["pinned"] is True


def test_cleanup_removes_oldest_unpinned(db: HistoryDB) -> None:
    for i in range(5):
        db.upsert_text(f"item-{i}", f"h{i}")
    deleted_paths = db.cleanup(limit=3)
    entries = db.list_entries()
    assert len(entries) == 3
    texts = {e["text_content"] for e in entries}
    assert texts == {"item-4", "item-3", "item-2"}


def test_cleanup_protects_pinned(db: HistoryDB) -> None:
    for i in range(5):
        db.upsert_text(f"item-{i}", f"h{i}")
    # 固定最旧的 item-0
    entries = db.list_entries()
    oldest = entries[-1]
    db.set_pinned(oldest["id"], True)
    db.cleanup(limit=3)
    remaining = db.list_entries()
    ids = {e["id"] for e in remaining}
    assert oldest["id"] in ids  # 固定条目保留


def test_delete(db: HistoryDB) -> None:
    eid = db.upsert_text("bye", "h1")
    db.delete(eid)
    assert db.get(eid) is None


def test_clear_unpinned_keeps_pinned(db: HistoryDB) -> None:
    for i in range(4):
        db.upsert_text(f"item-{i}", f"h{i}")
    entries = db.list_entries()
    pinned = entries[0]
    db.set_pinned(pinned["id"], True)
    db.clear_unpinned()
    remaining = db.list_entries()
    assert len(remaining) == 1
    assert remaining[0]["id"] == pinned["id"]


def test_clear_unpinned_returns_image_paths(db: HistoryDB) -> None:
    db.upsert_text("txt", "h1")
    db.upsert_image("img", "/tmp/orphan.png")
    paths = db.clear_unpinned()
    assert "/tmp/orphan.png" in paths
    assert db.list_entries() == []
