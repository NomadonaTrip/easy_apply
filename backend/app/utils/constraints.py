"""Output constraint definitions and enforcement utilities."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import TypedDict


class ViolationSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Violation:
    type: str
    severity: ViolationSeverity
    message: str
    position: int | None = None
    suggestion: str | None = None
    auto_fixable: bool = False


# AI clichés organized by category
AI_CLICHES: dict[str, list[str]] = {
    "corporate_buzzwords": [
        "leverage", "leveraging", "leveraged",
        "synergy", "synergies", "synergistic",
        "paradigm", "paradigm shift",
        "disrupt", "disruptive", "disrupting",
        "innovative", "innovate", "innovation",
        "holistic", "holistically",
        "robust", "robustly",
        "scalable", "scalability",
        "agile", "agility",
        "pivot", "pivoting",
        "actionable", "actionable insights",
        "bandwidth",
        "circle back",
        "deep dive",
        "drill down",
        "low-hanging fruit",
        "move the needle",
        "touch base",
        "value-add",
        "win-win",
    ],
    "action_verbs_overused": [
        "spearhead", "spearheaded", "spearheading",
        "utilize", "utilized", "utilizing",
        "facilitate", "facilitated", "facilitating",
        "orchestrate", "orchestrated", "orchestrating",
        "champion", "championed", "championing",
        "helm", "helmed", "helming",
        "architect", "architected",
    ],
    "self_description_cliches": [
        "passionate about",
        "passionate professional",
        "results-driven",
        "results-oriented",
        "detail-oriented",
        "team player",
        "self-starter",
        "self-motivated",
        "go-getter",
        "hard worker",
        "fast learner",
        "people person",
        "problem solver",
        "thought leader",
        "strategic thinker",
        "highly motivated",
        "dynamic individual",
        "proven track record",
    ],
    "filler_phrases": [
        "in order to",
        "in terms of",
        "at the end of the day",
        "think outside the box",
        "hit the ground running",
        "take it to the next level",
        "best-in-class",
        "world-class",
        "cutting-edge",
        "state-of-the-art",
        "best of breed",
        "game-changer",
        "next-generation",
    ],
}

# Flatten for simple lookup
ALL_CLICHES: list[str] = []
for _category, _terms in AI_CLICHES.items():
    ALL_CLICHES.extend(_terms)

# Character replacements (find -> replace)
CHARACTER_REPLACEMENTS: dict[str, str] = {
    "\u2014": "-",   # em-dash
    "\u2013": "-",   # en-dash
    "\u201c": '"',   # left double quote
    "\u201d": '"',   # right double quote
    "\u2018": "'",   # left single quote
    "\u2019": "'",   # right single quote
    "\u2026": "...", # ellipsis
    "\u2022": "-",   # bullet (for ATS)
}

_CHAR_VIOLATION_RE = re.compile(
    '[' + re.escape(''.join(CHARACTER_REPLACEMENTS.keys())) + ']'
)


class ATSRulesConfig(TypedDict):
    max_line_length: int
    avoid_tables: bool
    avoid_columns: bool
    avoid_graphics: bool
    standard_sections: list[str]
    date_format: str


# ATS formatting rules
ATS_RULES: ATSRulesConfig = {
    "max_line_length": 100,
    "avoid_tables": True,
    "avoid_columns": True,
    "avoid_graphics": True,
    "standard_sections": ["Summary", "Experience", "Skills", "Education"],
    "date_format": "MMM YYYY",
}


def detect_cliches(text: str) -> list[Violation]:
    """Detect AI clichés in text. Returns violations with positions."""
    if not text:
        return []

    violations = []
    for cliche in ALL_CLICHES:
        pattern = re.compile(r'\b' + re.escape(cliche) + r'\b', re.IGNORECASE)
        for match in pattern.finditer(text):
            violations.append(Violation(
                type="ai_cliche",
                severity=ViolationSeverity.WARNING,
                message=f"AI cliche detected: '{match.group()}'",
                position=match.start(),
                suggestion=get_cliche_alternative(cliche),
                auto_fixable=False,
            ))

    return violations


def detect_character_violations(text: str) -> list[Violation]:
    """Detect problematic characters that need replacement."""
    if not text:
        return []

    violations = []
    for match in _CHAR_VIOLATION_RE.finditer(text):
        char = match.group()
        violations.append(Violation(
            type="character",
            severity=ViolationSeverity.ERROR,
            message=f"Problematic character: '{char}' should be '{CHARACTER_REPLACEMENTS[char]}'",
            position=match.start(),
            suggestion=CHARACTER_REPLACEMENTS[char],
            auto_fixable=True,
        ))

    return violations


def detect_ats_violations(text: str) -> list[Violation]:
    """Detect ATS formatting issues."""
    if not text:
        return []

    violations = []

    # Check for table-like structures (multiple consecutive tabs or pipes)
    if re.search(r'\t{2,}|^\s*\|[^|\n]+\|[^|\n]+\|', text, re.MULTILINE):
        violations.append(Violation(
            type="ats_formatting",
            severity=ViolationSeverity.WARNING,
            message="Possible table structure detected - may not parse well in ATS",
            auto_fixable=False,
        ))

    # Check for very long lines
    max_len = ATS_RULES["max_line_length"]
    for i, line in enumerate(text.split('\n')):
        if len(line) > max_len:
            violations.append(Violation(
                type="ats_formatting",
                severity=ViolationSeverity.INFO,
                message=f"Line {i+1} exceeds recommended length ({len(line)} chars)",
                auto_fixable=False,
            ))

    return violations


def get_cliche_alternative(cliche: str) -> str | None:
    """Get suggested alternative for common clichés."""
    alternatives = {
        "leverage": "use",
        "leveraged": "used",
        "leveraging": "using",
        "utilize": "use",
        "utilized": "used",
        "utilizing": "using",
        "facilitate": "help",
        "facilitated": "helped",
        "facilitating": "helping",
        "spearhead": "lead",
        "spearheaded": "led",
        "spearheading": "leading",
        "synergy": "collaboration",
        "passionate about": "experienced in",
        "results-driven": "effective",
        "team player": "collaborative",
        "in order to": "to",
    }
    return alternatives.get(cliche.lower())
