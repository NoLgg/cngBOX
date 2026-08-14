"""ToolRegistry — 工具模块注册表。

工具模块实现 Tool 协议（注册/注销时挂载/卸载），应用壳通过注册表
统一管理工具生命周期，工具之间互不依赖。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Tool:
    """一个工具箱工具的描述与入口。"""

    tool_id: str
    name: str
    description: str
    icon: str  # emoji 或 SVG 标识
    invoke: Callable[[], None]  # 唤起工具（截图/面板/取色模式）
    hotkey_id: str | None = None  # 关联热键 id（config hotkeys.*）
    enabled: bool = True
    meta: dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    """工具注册表：注册/反注册/枚举/按 id 查询。"""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.tool_id] = tool

    def unregister(self, tool_id: str) -> None:
        self._tools.pop(tool_id, None)

    def get(self, tool_id: str) -> Tool | None:
        return self._tools.get(tool_id)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def enabled(self) -> list[Tool]:
        return [t for t in self._tools.values() if t.enabled]

    def set_enabled(self, tool_id: str, enabled: bool) -> None:
        tool = self._tools.get(tool_id)
        if tool:
            tool.enabled = enabled
