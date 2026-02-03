"""Shared types for LLM provider abstraction."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Role(Enum):
    """Message role in conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class ToolCall:
    """Represents a tool/function call from the LLM."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Message:
    """A message in the conversation."""

    role: Role
    content: str
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None  # For tool response messages


@dataclass
class ToolResult:
    """Result from executing a tool."""

    success: bool
    content: str
    error: str | None = None


@dataclass
class GenerationConfig:
    """Configuration for text generation."""

    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 0.95
    top_k: int = 40
    stop_sequences: list[str] = field(default_factory=list)


@dataclass
class ResearchProgress:
    """Progress update during research phase."""

    source: str  # e.g., "company_profile", "glassdoor", "news"
    status: str  # "searching", "found", "not_found", "error"
    content: str | None = None
    error: str | None = None


@dataclass
class ResearchResult:
    """Complete research result for a company."""

    company_name: str
    sources: dict[str, Any]  # source_name -> content
    gaps: list[str]  # Sources that failed or returned no data
    summary: str | None = None
