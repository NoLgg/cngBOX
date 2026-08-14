"""HistoryDB — 剪贴板历史 SQLite 存储。

表 entries：
- id INTEGER PRIMARY KEY AUTOINCREMENT
- type TEXT CHECK(type IN ('text','image'))
- content_hash TEXT UNIQUE
- text_content TEXT
- image_path TEXT
- pinned INTEGER DEFAULT 0
- created_at INTEGER (unix 秒)

索引：(pinned DESC, created_at DESC)。
清理策略：插入后/启动时，删除超过上限的最旧未固定条目。
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path


class HistoryDB:
    def __init__(self, db_path: Path | str) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL CHECK(type IN ('text','image')),
                content_hash TEXT NOT NULL UNIQUE,
                text_content TEXT,
                image_path TEXT,
                pinned INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_entries_order "
            "ON entries (pinned DESC, created_at DESC)"
        )
        self._conn.commit()

    # -- 写入 ------------------------------------------------------------------

    def upsert_text(self, text: str, content_hash: str) -> int:
        """插入/更新文本条目（按 hash 去重，存在则更新时间戳）。返回条目 id。"""
        now = int(time.time())
        self._conn.execute(
            """
            INSERT INTO entries (type, content_hash, text_content, pinned, created_at)
            VALUES ('text', ?, ?, 0, ?)
            ON CONFLICT(content_hash) DO UPDATE SET
                text_content = excluded.text_content,
                created_at = excluded.created_at
            """,
            (content_hash, text, now),
        )
        self._conn.commit()
        return self._conn.execute(
            "SELECT id FROM entries WHERE content_hash = ?", (content_hash,)
        ).fetchone()[0]

    def upsert_image(self, content_hash: str, image_path: str) -> int:
        now = int(time.time())
        self._conn.execute(
            """
            INSERT INTO entries (type, content_hash, image_path, pinned, created_at)
            VALUES ('image', ?, ?, 0, ?)
            ON CONFLICT(content_hash) DO UPDATE SET
                image_path = excluded.image_path,
                created_at = excluded.created_at
            """,
            (content_hash, image_path, now),
        )
        self._conn.commit()
        return self._conn.execute(
            "SELECT id FROM entries WHERE content_hash = ?", (content_hash,)
        ).fetchone()[0]

    # -- 查询 ------------------------------------------------------------------

    def list_entries(
        self,
        limit: int = 200,
        type_filter: str | None = None,
        search: str | None = None,
    ) -> list[dict]:
        """按时间倒序（固定条目优先）查询。"""
        clauses: list[str] = []
        params: list = []
        if type_filter in ("text", "image"):
            clauses.append("type = ?")
            params.append(type_filter)
        if search:
            clauses.append("text_content LIKE ?")
            params.append(f"%{search}%")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"""
            SELECT id, type, content_hash, text_content, image_path, pinned, created_at
            FROM entries {where}
            ORDER BY pinned DESC, created_at DESC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
        return [
            {
                "id": r[0], "type": r[1], "content_hash": r[2],
                "text_content": r[3], "image_path": r[4],
                "pinned": bool(r[5]), "created_at": r[6],
            }
            for r in rows
        ]

    def get(self, entry_id: int) -> dict | None:
        row = self._conn.execute(
            "SELECT id, type, content_hash, text_content, image_path, pinned, created_at "
            "FROM entries WHERE id = ?",
            (entry_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row[0], "type": row[1], "content_hash": row[2],
            "text_content": row[3], "image_path": row[4],
            "pinned": bool(row[5]), "created_at": row[6],
        }

    def set_pinned(self, entry_id: int, pinned: bool) -> None:
        self._conn.execute(
            "UPDATE entries SET pinned = ? WHERE id = ?", (int(pinned), entry_id)
        )
        self._conn.commit()

    def delete(self, entry_id: int) -> None:
        self._conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        self._conn.commit()

    def cleanup(self, limit: int) -> list[str]:
        """清理超出上限的最旧未固定条目，返回被删条目的 image_path 列表。"""
        rows = self._conn.execute(
            """
            SELECT id, image_path FROM entries
            WHERE pinned = 0
              AND id NOT IN (
                  SELECT id FROM entries
                  WHERE pinned = 0
                  ORDER BY created_at DESC
                  LIMIT ?
              )
            """,
            (limit,),
        ).fetchall()
        if not rows:
            return []
        ids = [r[0] for r in rows]
        paths = [r[1] for r in rows if r[1]]
        placeholders = ",".join("?" for _ in ids)
        self._conn.execute(f"DELETE FROM entries WHERE id IN ({placeholders})", ids)
        self._conn.commit()
        return paths

    def close(self) -> None:
        self._conn.close()
