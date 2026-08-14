"""ConfigStore — 配置持久化（~/.cng-toolbox/config.json）。

职责：
- 默认值定义（DEFAULTS，所有可配置项集中于此）
- 加载：深合并用户配置，JSON 损坏时回退默认值并备份 .bak
- 保存：原子写（临时文件 + os.replace）
- 变更通知：changed 信号（Qt），携带变更 key 列表
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

APP_DIR_NAME = ".cng-toolbox"


def default_app_dir() -> Path:
    """~/.cng-toolbox/ 运行时目录。"""
    return Path.home() / APP_DIR_NAME


# ---------------------------------------------------------------------------
# 默认配置：所有可配置项的单一事实源
# ---------------------------------------------------------------------------

DEFAULTS: dict[str, Any] = {
    # 通用
    "autostart": False,
    # 全局热键（None 表示禁用）
    "hotkeys": {
        "screenshot": "Ctrl+Shift+A",
        "color_picker": "Ctrl+Shift+C",
        "clipboard_panel": "Ctrl+Shift+V",
        "show_panel": "Ctrl+Shift+P",
        "close_all_pins": "Ctrl+Shift+Q",
    },
    # 外观
    "theme": "game-dark",
    "accent": "teal",
    # 贴图边框
    "pin_border": {
        "preset": "thin",  # none | thin | thick | dashed | glow | rounded
        "color": "#2dd4bf",
        "width": 2,
    },
    # 粘贴板
    "clipboard": {
        "history_limit": 500,
        "max_image_mb": 20,
    },
    # 工具开关
    "tools": {
        "screenshot": True,
        "clipboard": True,
        "color_picker": True,
    },
}

# 贴图上限（spec: 上限 20 张）
PIN_LIMIT = 20
# 取色历史上限（spec: 最近 10 个）
COLOR_HISTORY_LIMIT = 10
# 缩放范围（spec: 20% ~ 500%）
PIN_SCALE_MIN = 0.2
PIN_SCALE_MAX = 5.0


def deep_merge(base: dict, override: dict) -> dict:
    """递归合并两个 dict（override 优先），返回新 dict。"""
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


class ConfigStore(QObject):
    """配置存储。线程安全不做保证——仅在 GUI 线程使用。"""

    changed = Signal(list)  # 变更的 key 路径列表，如 ["hotkeys.screenshot"]

    def __init__(self, app_dir: Path | None = None) -> None:
        super().__init__()
        self.app_dir = Path(app_dir) if app_dir else default_app_dir()
        self.config_path = self.app_dir / "config.json"
        self._config: dict[str, Any] = deepcopy(DEFAULTS)
        self._load()

    # -- 加载/保存 ----------------------------------------------------------

    def _load(self) -> None:
        self.app_dir.mkdir(parents=True, exist_ok=True)
        if not self.config_path.exists():
            self._save()
            return
        try:
            raw = json.loads(self.config_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("config root must be an object")
            self._config = deep_merge(DEFAULTS, raw)
        except (json.JSONDecodeError, ValueError, OSError):
            # 损坏回退：备份 + 默认值
            try:
                self.config_path.replace(self.config_path.with_suffix(".json.bak"))
            except OSError:
                pass
            self._config = deepcopy(DEFAULTS)
            self._save()

    def _save(self) -> None:
        tmp = self.config_path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(self._config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp, self.config_path)

    # -- 访问器 --------------------------------------------------------------

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """按 'a.b.c' 路径读取。"""
        node: Any = self._config
        for part in dotted_key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, dotted_key: str, value: Any) -> None:
        """按 'a.b.c' 路径写入并持久化，发出 changed 信号。"""
        parts = dotted_key.split(".")
        node = self._config
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = deepcopy(value)
        self._save()
        self.changed.emit([dotted_key])

    @property
    def config(self) -> dict:
        return self._config
