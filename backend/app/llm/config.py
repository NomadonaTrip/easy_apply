"""LLM provider configuration."""

from dataclasses import dataclass
from typing import Literal


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""

    provider: Literal["gemini", "claude"]
    api_key: str
    model: str

    @classmethod
    def from_settings(cls, settings) -> "LLMConfig":
        """Create config from application settings."""
        return cls(
            provider=settings.llm_provider,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
        )
