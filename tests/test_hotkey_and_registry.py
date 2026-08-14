"""热键序列化解析与工具注册表测试。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cng_toolbox.shell.hotkey_manager import MOD_CONTROL, MOD_SHIFT, parse_sequence
from cng_toolbox.shell.tool_registry import Tool, ToolRegistry


def test_parse_sequence_basic() -> None:
    mods, vk = parse_sequence("Ctrl+Shift+A")
    assert vk == 0x41
    assert mods & MOD_CONTROL
    assert mods & MOD_SHIFT


def test_parse_sequence_no_modifier() -> None:
    mods, vk = parse_sequence("F5")
    assert vk == 0x74
    assert mods & 0x4000  # MOD_NOREPEAT


def test_parse_sequence_empty() -> None:
    assert parse_sequence("") is None
    assert parse_sequence(None) is None
    assert parse_sequence("Ctrl+") is None


def test_parse_sequence_unknown_key() -> None:
    assert parse_sequence("Ctrl+あ") is None


def test_parse_sequence_case_insensitive_modifier() -> None:
    mods, vk = parse_sequence("ctrl+alt+v")
    assert vk == 0x56
    assert mods & MOD_CONTROL


def test_tool_registry_lifecycle() -> None:
    registry = ToolRegistry()
    tool = Tool(
        tool_id="demo",
        name="Demo",
        description="d",
        icon="🎯",
        invoke=lambda: None,
        hotkey_id="demo_hotkey",
    )
    registry.register(tool)
    assert registry.get("demo") is tool
    assert len(registry.all()) == 1
    registry.set_enabled("demo", False)
    assert registry.enabled() == []
    registry.unregister("demo")
    assert registry.get("demo") is None
