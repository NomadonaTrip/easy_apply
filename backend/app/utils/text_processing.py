"""Output constraint enforcement for LLM-generated text."""

import logging
import re

logger = logging.getLogger(__name__)

# AI cliche terms to detect in generated output (observability safety net)
AI_CLICHES = [
    "synergy",
    "leverage my expertise",
    "passionate about",
    "results-driven",
    "think outside the box",
    "go-getter",
    "team player",
    "detail-oriented",
    "self-starter",
    "proven track record",
    "dynamic environment",
    "fast-paced environment",
    "hit the ground running",
    "wear many hats",
    "deep dive",
    "move the needle",
    "low-hanging fruit",
    "circle back",
    "paradigm shift",
    "cutting-edge",
]


def detect_ai_cliches(text: str) -> list[str]:
    """Detect AI cliches in generated text.

    Returns list of detected cliches. Logs a warning for each.
    Does NOT modify the text - prompts handle avoidance, this is a safety net.
    """
    if not text:
        return []

    text_lower = text.lower()
    found = [cliche for cliche in AI_CLICHES if cliche in text_lower]

    for cliche in found:
        logger.warning("AI cliche detected in generated text: %s", cliche)

    return found


def enforce_output_constraints(text: str) -> str:
    """Enforce output constraints on generated text.

    - Replace em-dashes and en-dashes with hyphens
    - Replace smart quotes with straight quotes
    - Clean up excessive whitespace
    - Detect AI cliches (log warnings, no modification)
    """
    if not text:
        return text

    # Replace em-dashes with hyphens
    text = text.replace("\u2014", "-")
    # Replace en-dashes with hyphens
    text = text.replace("\u2013", "-")

    # Replace smart quotes with straight quotes
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")

    # Clean up excessive whitespace (3+ newlines -> 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)

    result = text.strip()

    # Cliche detection (observability only, does not modify text)
    detect_ai_cliches(result)

    return result
