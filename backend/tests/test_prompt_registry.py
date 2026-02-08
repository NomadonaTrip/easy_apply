"""Tests for the PromptRegistry class."""

import logging

import pytest
from app.llm.prompts import PromptRegistry, SKILL_EXTRACTION_PROMPT


class TestPromptRegistry:
    """Tests for the PromptRegistry class."""

    def setup_method(self):
        """Save registry state before each test."""
        self._original = PromptRegistry._prompts.copy()

    def teardown_method(self):
        """Restore original registry state."""
        PromptRegistry._reset_for_testing(self._original)

    def test_register_and_get_raw(self):
        PromptRegistry.register("test_prompt", "Hello {name}")
        result = PromptRegistry.get("test_prompt")
        assert result == "Hello {name}"

    def test_get_with_kwargs_formats(self):
        PromptRegistry.register("test_prompt", "Hello {name}, you are {role}")
        result = PromptRegistry.get("test_prompt", name="Alice", role="admin")
        assert result == "Hello Alice, you are admin"

    def test_get_unknown_raises_valueerror(self):
        with pytest.raises(ValueError, match="Unknown prompt: nonexistent"):
            PromptRegistry.get("nonexistent")

    def test_get_wrong_kwargs_raises_valueerror(self):
        """Passing wrong kwargs gives a helpful ValueError, not a bare KeyError."""
        PromptRegistry.register("test_prompt", "Hello {name}")
        with pytest.raises(ValueError, match="Missing placeholder.*'test_prompt'"):
            PromptRegistry.get("test_prompt", wrong_key="value")

    def test_register_duplicate_logs_warning(self, caplog):
        """Overwriting a prompt logs a warning."""
        PromptRegistry.register("dupe_test", "original")
        with caplog.at_level(logging.WARNING, logger="app.llm.prompts"):
            PromptRegistry.register("dupe_test", "overwritten")
        assert "Overwriting existing prompt: dupe_test" in caplog.text
        assert PromptRegistry.get("dupe_test") == "overwritten"

    def test_list_returns_registered_names(self):
        PromptRegistry.register("alpha", "a")
        PromptRegistry.register("beta", "b")
        names = PromptRegistry.list()
        assert "alpha" in names
        assert "beta" in names

    def test_all_expected_prompts_registered(self):
        """After full import, all migrated prompts should be in the registry."""
        expected = [
            "skill_extraction",
            "accomplishment_extraction",
            "keyword_extraction",
            "job_description_extraction",
        ]
        registered = PromptRegistry.list()
        for name in expected:
            assert name in registered, f"Expected prompt '{name}' not found in registry"

    def test_keyword_extraction_formats(self):
        prompt = PromptRegistry.get("keyword_extraction", job_posting="We need Python devs")
        assert "We need Python devs" in prompt
        assert "{job_posting}" not in prompt

    def test_job_description_extraction_formats(self):
        prompt = PromptRegistry.get("job_description_extraction", raw_content="<html>Job here</html>")
        assert "<html>Job here</html>" in prompt
        assert "{raw_content}" not in prompt

    def test_backward_compat_direct_import(self):
        """SKILL_EXTRACTION_PROMPT should still be importable directly."""
        assert isinstance(SKILL_EXTRACTION_PROMPT, str)
        assert "{resume_text}" in SKILL_EXTRACTION_PROMPT

    def test_all_prompt_constants_importable(self):
        """All prompt constants should be directly importable from app.llm.prompts."""
        from app.llm.prompts import (
            SKILL_EXTRACTION_PROMPT,
            ACCOMPLISHMENT_EXTRACTION_PROMPT,
            KEYWORD_EXTRACTION_PROMPT,
            JOB_DESCRIPTION_EXTRACTION_PROMPT,
        )
        assert isinstance(SKILL_EXTRACTION_PROMPT, str)
        assert isinstance(ACCOMPLISHMENT_EXTRACTION_PROMPT, str)
        assert isinstance(KEYWORD_EXTRACTION_PROMPT, str)
        assert isinstance(JOB_DESCRIPTION_EXTRACTION_PROMPT, str)
