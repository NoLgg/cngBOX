"""ConfigStore 与 deep_merge 单元测试。"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cng_toolbox.shell.config_store import ConfigStore, DEFAULTS, deep_merge


def test_deep_merge_overrides_nested(tmp_path: Path) -> None:
    base = {"a": {"b": 1, "c": 2}, "x": [1, 2]}
    override = {"a": {"c": 3}}
    result = deep_merge(base, override)
    assert result["a"]["b"] == 1
    assert result["a"]["c"] == 3
    assert result["x"] == [1, 2]
    # 不修改原 dict
    assert base["a"]["c"] == 2


def test_config_defaults_written(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path)
    config_file = tmp_path / "config.json"
    assert config_file.exists()
    data = json.loads(config_file.read_text(encoding="utf-8"))
    assert data == DEFAULTS


def test_config_roundtrip(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path)
    store.set("hotkeys.screenshot", "Ctrl+Alt+S")
    store2 = ConfigStore(tmp_path)
    assert store2.get("hotkeys.screenshot") == "Ctrl+Alt+S"


def test_config_corrupt_falls_back(tmp_path: Path) -> None:
    config_file = tmp_path / "config.json"
    config_file.write_text("{ not valid json !!", encoding="utf-8")
    store = ConfigStore(tmp_path)
    assert store.get("autostart") is False
    # 备份文件存在
    assert (tmp_path / "config.json.bak").exists()
    # 新配置文件已重建
    assert config_file.exists()


def test_config_set_emits_changed(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path)
    received: list[list[str]] = []
    store.changed.connect(received.append)
    store.set("accent", "orange")
    assert received == [["accent"]]


def test_config_unknown_key_returns_default(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path)
    assert store.get("no.such.key", 42) == 42


def test_config_migrates_legacy_hotkeys(tmp_path: Path) -> None:
    """旧默认热键（Ctrl+Shift+*）自动迁移为新默认（Ctrl+Alt+*）。"""
    legacy = {
        "hotkeys": {
            "screenshot": "Ctrl+Shift+A",
            "clipboard_panel": "Ctrl+Shift+V",
            "show_panel": "Ctrl+Shift+P",
        }
    }
    (tmp_path / "config.json").write_text(
        json.dumps(legacy, ensure_ascii=False), encoding="utf-8"
    )
    store = ConfigStore(tmp_path)
    assert store.get("hotkeys.screenshot") == "Ctrl+Alt+A"
    assert store.get("hotkeys.clipboard_panel") == "Ctrl+Alt+V"
    assert store.get("hotkeys.show_panel") == "Ctrl+Alt+P"
    # 迁移结果已持久化
    saved = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert saved["hotkeys"]["screenshot"] == "Ctrl+Alt+A"


def test_config_keeps_custom_hotkeys(tmp_path: Path) -> None:
    """用户自定义热键不应被迁移覆盖。"""
    custom = {"hotkeys": {"screenshot": "Ctrl+F9", "color_picker": "Ctrl+Shift+C"}}
    (tmp_path / "config.json").write_text(
        json.dumps(custom, ensure_ascii=False), encoding="utf-8"
    )
    store = ConfigStore(tmp_path)
    assert store.get("hotkeys.screenshot") == "Ctrl+F9"
