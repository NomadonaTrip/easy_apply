"""LLM tools for function calling."""

from .web_fetch import WebFetchTool
from .web_search import WebSearchTool
from .registry import ToolRegistry

__all__ = ["WebSearchTool", "WebFetchTool", "ToolRegistry"]
