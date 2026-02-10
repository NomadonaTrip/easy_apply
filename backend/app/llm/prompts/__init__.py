"""
LLM Prompt Registry.

All LLM prompts are externalized into versioned template files.
No inline prompt strings in service files.

Usage:
    from app.llm.prompts import PromptRegistry
    prompt = PromptRegistry.get("keyword_extraction", job_posting=text)
"""

import logging

logger = logging.getLogger(__name__)


class PromptRegistry:
    """Named, versioned prompt template registry."""

    _prompts: dict[str, str] = {}

    @classmethod
    def register(cls, name: str, template: str):
        if name in cls._prompts:
            logger.warning("Overwriting existing prompt: %s", name)
        cls._prompts[name] = template

    @classmethod
    def get(cls, prompt_name: str, **kwargs) -> str:
        template = cls._prompts.get(prompt_name)
        if template is None:
            raise ValueError(f"Unknown prompt: {prompt_name}")
        try:
            return template.format(**kwargs) if kwargs else template
        except KeyError as e:
            raise ValueError(
                f"Missing placeholder {e} in prompt '{prompt_name}'. "
                f"Available placeholders can be found in the prompt template."
            ) from e

    @classmethod
    def list(cls) -> list[str]:
        return list(cls._prompts.keys())

    @classmethod
    def _reset_for_testing(cls, prompts: dict[str, str]):
        cls._prompts = prompts


# --- Auto-registration imports ---
# Each module registers its prompts at import time.
from .extraction import SKILL_EXTRACTION_PROMPT, ACCOMPLISHMENT_EXTRACTION_PROMPT  # noqa: E402, F401
from .keyword import KEYWORD_EXTRACTION_PROMPT  # noqa: E402, F401
from .scrape import JOB_DESCRIPTION_EXTRACTION_PROMPT  # noqa: E402, F401
from . import research  # noqa: E402, F401
from . import resume  # noqa: E402, F401
from . import cover_letter  # noqa: E402, F401

__all__ = [
    "PromptRegistry",
    "SKILL_EXTRACTION_PROMPT",
    "ACCOMPLISHMENT_EXTRACTION_PROMPT",
    "KEYWORD_EXTRACTION_PROMPT",
    "JOB_DESCRIPTION_EXTRACTION_PROMPT",
]
