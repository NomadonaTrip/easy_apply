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
from .instrumented_provider import InstrumentedProvider
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
    "InstrumentedProvider",
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
    "get_llm_provider_for_generation",
    "reset_provider",
]


# Singleton instances
_provider_instance: LLMProvider | None = None
_generation_provider_instance: LLMProvider | None = None
_generation_model_name: str | None = None


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

        concrete = _create_provider(config)
        # Wrap with instrumentation
        from .instrumented_provider import DefaultCallLogger

        call_logger = DefaultCallLogger()
        _provider_instance = InstrumentedProvider(
            inner=concrete, logger=call_logger, provider_name=config.provider
        )

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


def get_llm_provider_for_generation() -> LLMProvider:
    """Get an LLM provider for generation tasks (resume/cover letter).

    When LLM_MODEL_GEN is set, returns a cached provider using the override
    model. Cache is invalidated if the model name changes.
    When empty, returns the default singleton.
    """
    global _generation_provider_instance, _generation_model_name

    from app.config import settings

    if not settings.llm_model_gen:
        return get_llm_provider()

    # Return cached instance if model hasn't changed
    if (
        _generation_provider_instance is not None
        and _generation_model_name == settings.llm_model_gen
    ):
        return _generation_provider_instance

    # Create a cached provider with the generation-specific model
    config = LLMConfig(
        provider=settings.llm_provider,
        api_key=settings.llm_api_key,
        model=settings.llm_model_gen,
    )
    concrete = _create_provider(config)

    from .instrumented_provider import DefaultCallLogger

    call_logger = DefaultCallLogger()
    _generation_provider_instance = InstrumentedProvider(
        inner=concrete, logger=call_logger, provider_name=config.provider
    )
    _generation_model_name = settings.llm_model_gen

    return _generation_provider_instance


def reset_provider() -> None:
    """
    Reset the provider singleton(s).

    Useful for testing or when configuration changes.
    """
    global _provider_instance, _generation_provider_instance, _generation_model_name
    _provider_instance = None
    _generation_provider_instance = None
    _generation_model_name = None
