"""Tool registry for managing available tools."""

from typing import Type

from ..base import Tool
from .web_fetch import WebFetchTool
from .web_search import WebSearchTool


class ToolRegistry:
    """
    Registry for LLM tools.

    Provides centralized management of available tools and their
    instantiation based on configuration.
    """

    # Built-in tool classes
    BUILTIN_TOOLS: dict[str, Type[Tool]] = {
        "web_search": WebSearchTool,
        "web_fetch": WebFetchTool,
    }

    def __init__(self, config: dict | None = None):
        """
        Initialize tool registry.

        Args:
            config: Tool configuration dict, e.g.:
                {
                    "web_search": {"api_key": "..."},
                    "web_fetch": {},
                }
        """
        self._config = config or {}
        self._instances: dict[str, Tool] = {}

    def get(self, name: str) -> Tool:
        """
        Get a tool instance by name.

        Args:
            name: Tool name

        Returns:
            Tool instance

        Raises:
            ValueError: If tool not found
        """
        if name not in self._instances:
            self._instances[name] = self._create_tool(name)
        return self._instances[name]

    def get_all(self, names: list[str] | None = None) -> list[Tool]:
        """
        Get multiple tool instances.

        Args:
            names: List of tool names, or None for all available

        Returns:
            List of tool instances
        """
        if names is None:
            names = list(self.BUILTIN_TOOLS.keys())

        return [self.get(name) for name in names if self._is_available(name)]

    def _create_tool(self, name: str) -> Tool:
        """Create a tool instance."""
        if name not in self.BUILTIN_TOOLS:
            raise ValueError(f"Unknown tool: {name}")

        tool_class = self.BUILTIN_TOOLS[name]
        tool_config = self._config.get(name, {})

        return tool_class(**tool_config)

    def _is_available(self, name: str) -> bool:
        """Check if a tool is available (has required config)."""
        if name not in self.BUILTIN_TOOLS:
            return False

        # Check if tool has required API key
        if name == "web_search":
            return bool(self._config.get("web_search", {}).get("api_key"))

        # web_fetch doesn't need API key
        return True

    def available_tools(self) -> list[str]:
        """List available tool names."""
        return [name for name in self.BUILTIN_TOOLS if self._is_available(name)]

    def register(self, name: str, tool_class: Type[Tool]) -> None:
        """
        Register a custom tool.

        Args:
            name: Tool name
            tool_class: Tool class (not instance)
        """
        self.BUILTIN_TOOLS[name] = tool_class
        # Clear cached instance if exists
        self._instances.pop(name, None)
