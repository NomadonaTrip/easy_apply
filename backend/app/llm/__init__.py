"""
LLM Provider Abstraction Layer.

This module provides a provider-agnostic interface for LLM operations,
allowing easy switching between different LLM providers (Gemini, Claude, etc.).

Usage:
    from app.llm import get_llm_provider
    from app.llm.types import Message, Role

    provider = get_llm_provider()
    response = await provider.generate([
        Message(role=Role.USER, content="Hello!")
    ])

With skills:
    from app.llm import get_llm_provider
    from app.llm.skills import SkillLoader

    provider = get_llm_provider()
    skill_content = SkillLoader.load("resume_tailoring")
    provider.set_system_instruction(skill_content)

With tools:
    from app.llm import get_llm_provider
    from app.llm.tools import ToolRegistry

    provider = get_llm_provider()
    registry = ToolRegistry(config=settings.tool_config)
    tools = registry.get_all(["web_search", "web_fetch"])

    response, tool_calls = await provider.generate_with_tools(messages, tools)
"""

from typing import TYPE_CHECKING

from .base import LLMProvider, Tool
from .config import LLMConfig
from .types import (
    GenerationConfig,
    Message,
    ResearchProgress,
    ResearchResult,
    Role,
    ToolCall,
    ToolResult,
)

if TYPE_CHECKING:
    pass

__all__ = [
    # Core classes
    "LLMProvider",
    "Tool",
    "LLMConfig",
    # Types
    "Message",
    "Role",
    "ToolCall",
    "ToolResult",
    "GenerationConfig",
    "ResearchProgress",
    "ResearchResult",
    # Factory
    "get_llm_provider",
    "reset_provider",
]


# Singleton instance
_provider_instance: LLMProvider | None = None


def get_llm_provider(config: LLMConfig | None = None) -> LLMProvider:
    """
    Get the configured LLM provider (singleton).

    On first call, creates the provider based on configuration.
    Subsequent calls return the same instance.

    Args:
        config: Optional config override. If not provided, uses app settings.

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If provider type is unknown
        NotImplementedError: If provider not yet implemented

    Example:
        provider = get_llm_provider()
        response = await provider.generate(messages)
    """
    global _provider_instance

    if _provider_instance is None:
        if config is None:
            # Import here to avoid circular imports
            from app.config import settings

            config = LLMConfig.from_settings(settings)

        _provider_instance = _create_provider(config)

    return _provider_instance


def _create_provider(config: LLMConfig) -> LLMProvider:
    """Create a provider instance based on config."""
    if config.provider == "gemini":
        from .providers.gemini import GeminiProvider

        return GeminiProvider(
            api_key=config.api_key,
            model=config.model,
        )

    elif config.provider == "claude":
        # Future implementation
        raise NotImplementedError(
            "Claude provider not yet implemented. "
            "This is planned for when Claude API access becomes available."
        )

    else:
        raise ValueError(f"Unknown LLM provider: {config.provider}")


def reset_provider() -> None:
    """
    Reset the provider singleton.

    Useful for testing or when configuration changes.
    """
    global _provider_instance
    _provider_instance = None
