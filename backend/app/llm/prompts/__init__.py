"""
LLM prompts for extraction tasks.

This module provides prompt templates for:
- SKILL_EXTRACTION_PROMPT: Extract professional skills from resume text
- ACCOMPLISHMENT_EXTRACTION_PROMPT: Extract achievements from resume text

Both prompts expect a {resume_text} placeholder and return structured JSON.
"""

from .extraction import SKILL_EXTRACTION_PROMPT, ACCOMPLISHMENT_EXTRACTION_PROMPT

__all__ = ["SKILL_EXTRACTION_PROMPT", "ACCOMPLISHMENT_EXTRACTION_PROMPT"]
