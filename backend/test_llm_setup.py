"""Test script for LLM provider setup."""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """Test that all modules import correctly."""
    print("Testing imports...")

    from app.llm import (
        get_llm_provider,
        reset_provider,
        LLMProvider,
        Tool,
        Message,
        Role,
        ToolCall,
        ToolResult,
        GenerationConfig,
    )
    print("  ✓ Core imports successful")

    from app.llm.providers import GeminiProvider
    print("  ✓ GeminiProvider import successful")

    from app.llm.tools import WebSearchTool, WebFetchTool, ToolRegistry
    print("  ✓ Tools import successful")

    from app.llm.skills import SkillLoader
    print("  ✓ SkillLoader import successful")

    return True


def test_skill_loader():
    """Test skill loading."""
    print("\nTesting SkillLoader...")

    from app.llm.skills import SkillLoader

    # List available skills
    skills = SkillLoader.available_skills()
    print(f"  ✓ Available skills: {skills}")

    # Load resume_tailoring skill
    if SkillLoader.skill_exists("resume_tailoring"):
        content = SkillLoader.load("resume_tailoring")
        print(f"  ✓ Loaded resume_tailoring skill ({len(content)} chars)")
    else:
        print("  ✗ resume_tailoring skill not found")
        return False

    return True


def test_tool_registry():
    """Test tool registry."""
    print("\nTesting ToolRegistry...")

    from app.llm.tools import ToolRegistry

    # Without API keys
    registry = ToolRegistry(config={})
    available = registry.available_tools()
    print(f"  ✓ Available tools (no config): {available}")

    # With mock config
    registry_with_config = ToolRegistry(config={
        "web_search": {"api_key": "test-key"},
        "web_fetch": {},
    })
    available_with_config = registry_with_config.available_tools()
    print(f"  ✓ Available tools (with config): {available_with_config}")

    # Get web_fetch tool (doesn't need API key)
    web_fetch = registry.get("web_fetch")
    print(f"  ✓ WebFetchTool: name={web_fetch.name}")

    return True


def test_provider_factory():
    """Test provider factory."""
    print("\nTesting provider factory...")

    from app.llm import get_llm_provider, reset_provider, LLMConfig
    from app.config import settings

    print(f"  Config: provider={settings.llm_provider}, model={settings.llm_model}")
    print(f"  API key configured: {bool(settings.llm_api_key)}")

    if not settings.llm_api_key:
        print("  ⚠ No API key set - skipping provider instantiation")
        print("    Set LLM_API_KEY in .env to test full functionality")
        return True

    # Reset any existing provider
    reset_provider()

    # Get provider
    provider = get_llm_provider()
    print(f"  ✓ Provider created: {type(provider).__name__}")
    print(f"  ✓ Model: {provider.get_model_name()}")

    return True


async def test_provider_generation():
    """Test actual generation (requires API key)."""
    print("\nTesting generation...")

    from app.llm import get_llm_provider, Message, Role
    from app.config import settings

    if not settings.llm_api_key:
        print("  ⚠ Skipped - no API key configured")
        return True

    provider = get_llm_provider()

    messages = [
        Message(role=Role.USER, content="Say 'Hello, Easy Apply!' and nothing else.")
    ]

    try:
        response = await provider.generate(messages)
        print(f"  ✓ Generation successful: {response.content[:100]}")
        return True
    except Exception as e:
        print(f"  ✗ Generation failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 50)
    print("LLM Provider Setup Test")
    print("=" * 50)

    all_passed = True

    # Test imports
    if not test_imports():
        all_passed = False

    # Test skill loader
    if not test_skill_loader():
        all_passed = False

    # Test tool registry
    if not test_tool_registry():
        all_passed = False

    # Test provider factory
    if not test_provider_factory():
        all_passed = False

    # Test generation (async)
    if not asyncio.run(test_provider_generation()):
        all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("All tests passed! ✓")
    else:
        print("Some tests failed. ✗")
    print("=" * 50)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
