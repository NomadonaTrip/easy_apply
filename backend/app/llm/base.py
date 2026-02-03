"""Abstract base classes for LLM provider abstraction."""

from abc import ABC, abstractmethod
from typing import AsyncIterator

from .types import GenerationConfig, Message, ToolCall, ToolResult


class Tool(ABC):
    """Abstract base class for tools that can be called by LLMs."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name for function calling."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the tool does (shown to LLM)."""
        pass

    @property
    @abstractmethod
    def parameters_schema(self) -> dict:
        """JSON Schema for the tool parameters."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given arguments."""
        pass


class LLMProvider(ABC):
    """Abstract base class for LLM providers (Gemini, Claude, etc.)."""

    @abstractmethod
    async def generate(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
    ) -> Message:
        """
        Generate a single response.

        Args:
            messages: Conversation history
            config: Generation configuration

        Returns:
            Assistant message with response
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response.

        Args:
            messages: Conversation history
            config: Generation configuration

        Yields:
            Text chunks as they are generated
        """
        pass

    @abstractmethod
    async def generate_with_tools(
        self,
        messages: list[Message],
        tools: list[Tool],
        config: GenerationConfig | None = None,
    ) -> tuple[Message, list[ToolCall]]:
        """
        Generate a response with tool/function calling support.

        Args:
            messages: Conversation history
            tools: Available tools the LLM can call
            config: Generation configuration

        Returns:
            Tuple of (assistant message, list of tool calls)
        """
        pass

    @abstractmethod
    def set_system_instruction(self, instruction: str) -> None:
        """
        Set the system instruction/prompt.

        This is used to load skills (like SKILL.md) as context.

        Args:
            instruction: System instruction text
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the name of the model being used."""
        pass
