"""Output constraint enforcement for LLM-generated text."""

import logging
import re
from dataclasses import dataclass, field

from app.utils.constraints import (
    CHARACTER_REPLACEMENTS,
    Violation,
    ViolationSeverity,
    detect_character_violations,
    detect_cliches,
    detect_ats_violations,
)

logger = logging.getLogger(__name__)


@dataclass
class ConstraintResult:
    cleaned_text: str
    violations: list[Violation] = field(default_factory=list)
    violations_fixed: int = 0
    violations_remaining: int = 0


def enforce_output_constraints(text: str | None) -> str:
    """Enforce output constraints and return cleaned text.

    For detailed results, use enforce_output_constraints_detailed.
    """
    if not text:
        return ""

    result = enforce_output_constraints_detailed(text)
    return result.cleaned_text


def enforce_output_constraints_detailed(text: str | None) -> ConstraintResult:
    """Enforce output constraints with detailed violation reporting.

    Returns cleaned text plus violation details.
    """
    if not text:
        return ConstraintResult(
            cleaned_text=text if text is not None else "",
            violations=[],
            violations_fixed=0,
            violations_remaining=0,
        )

    cleaned = text
    all_violations: list[Violation] = []
    fixed_count = 0

    # 1. Detect character violations and count them before fixing
    char_violations = detect_character_violations(cleaned)
    fixed_count = len(char_violations)

    # Apply character replacements
    for char, replacement in CHARACTER_REPLACEMENTS.items():
        cleaned = cleaned.replace(char, replacement)

    # 2. Detect clichés (not auto-fixed, but logged)
    cliche_violations = detect_cliches(cleaned)
    all_violations.extend(cliche_violations)

    if cliche_violations:
        logger.warning(
            "AI cliches detected in output: %d instances. Terms: %s",
            len(cliche_violations),
            [v.message for v in cliche_violations[:5]],
        )

    # 3. Detect ATS issues
    ats_violations = detect_ats_violations(cleaned)
    all_violations.extend(ats_violations)

    # 4. Clean up whitespace
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = re.sub(r' {2,}', ' ', cleaned)
    cleaned = cleaned.strip()

    return ConstraintResult(
        cleaned_text=cleaned,
        violations=all_violations,
        violations_fixed=fixed_count,
        violations_remaining=len(all_violations),
    )
