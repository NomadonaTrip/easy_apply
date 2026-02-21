"""Output constraint enforcement for LLM-generated text."""

import logging
import re

logger = logging.getLogger(__name__)

# Stop words to skip during fuzzy keyword decomposition
_STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "of", "in", "on", "at", "to", "for",
    "with", "by", "from", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "can", "could", "not", "no", "but", "if",
    "than", "that", "this", "these", "those", "its", "it",
})

# Minimum prefix length for fuzzy word matching
_PREFIX_LEN = 5


def _fuzzy_keyword_match(keyword_text: str, text_words: set[str]) -> bool:
    """Check if all content words of a keyword appear in text via prefix matching.

    Decomposes the keyword into content words (skipping stop words),
    takes a 5-char prefix of each, and checks that all prefixes appear
    among the text word prefixes. This handles morphological variants:
    "collaboration" and "collaborated" both share prefix "colla".

    Args:
        keyword_text: The keyword phrase (already lowercased).
        text_words: Set of word prefixes from the target text.

    Returns:
        True if all content-word prefixes are found in text_words.
    """
    # Split keyword into words, strip non-alpha edges
    kw_words = re.findall(r"[a-z]+", keyword_text.lower())
    content_words = [w for w in kw_words if w not in _STOP_WORDS and len(w) >= 3]

    if not content_words:
        return False

    for word in content_words:
        prefix = word[:_PREFIX_LEN]
        if prefix not in text_words:
            return False

    return True


def _build_text_word_prefixes(text: str) -> set[str]:
    """Build a set of 5-char prefixes from all words in text."""
    words = re.findall(r"[a-z]+", text.lower())
    return {w[:_PREFIX_LEN] for w in words if len(w) >= 3}


def keyword_found(keyword_text: str, text: str, text_word_prefixes: set[str] | None = None) -> bool:
    """Check if a keyword appears in text using flexible matching.

    Handles:
    1. Exact substring match (baseline)
    2. Hyphen/space variant: "Problem-solving" matches "problem solving"
    3. Slash-separated alternatives: "A/B" matches if "A" or "B" found
    4. Parenthetical expansion: "KPIs (Key Performance Indicators)" matches either form
    5. Word-prefix fuzzy: all content-word 5-char prefixes found in text words

    Args:
        keyword_text: The keyword to search for.
        text: The text to search in (should be lowercased).
        text_word_prefixes: Optional pre-computed set of word prefixes for fuzzy matching.
            If None, will be computed from text on demand.
    """
    kw_lower = keyword_text.lower().strip()

    # 1. Exact substring match
    if kw_lower in text:
        return True

    # 2. Hyphen/space variant
    if "-" in kw_lower and kw_lower.replace("-", " ") in text:
        return True
    if " " in kw_lower and kw_lower.replace(" ", "-") in text:
        return True

    # 3. Slash-separated alternatives — match if ANY part is found
    if "/" in kw_lower:
        parts = [p.strip() for p in kw_lower.split("/") if p.strip()]
        if any(part in text for part in parts):
            return True

    # 4. Parenthetical — match leading term OR parenthetical content
    paren_match = re.match(r"^(.+?)\s*\((.+?)\)\s*$", kw_lower)
    if paren_match:
        leading = paren_match.group(1).strip()
        inside = paren_match.group(2).strip()
        if leading in text or inside in text:
            return True

    # 5. Word-prefix fuzzy match (fallback for morphological variants)
    if text_word_prefixes is None:
        text_word_prefixes = _build_text_word_prefixes(text)
    if _fuzzy_keyword_match(kw_lower, text_word_prefixes):
        return True

    return False

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


def check_keyword_coverage(
    text: str,
    keywords_raw: list[dict],
    threshold: float = 0.6,
) -> dict:
    """Check what percentage of keywords appear in generated text by priority tier.

    Args:
        text: Generated text to check.
        keywords_raw: List of keyword dicts with text, priority, category keys.
        threshold: Minimum acceptable must-have coverage (0-1). Default 0.6.

    Returns dict with:
        must_have_coverage (float 0-1), must_have_missing (list[str]),
        important_coverage (float 0-1), overall_coverage (float 0-1),
        below_threshold (bool).
    """
    if not text or not keywords_raw:
        return {
            "must_have_coverage": 0.0,
            "must_have_missing": [],
            "important_coverage": 0.0,
            "overall_coverage": 0.0,
            "below_threshold": False,
        }

    text_lower = text.lower()
    text_prefixes = _build_text_word_prefixes(text_lower)

    must_have = [kw for kw in keywords_raw if kw.get("priority", 0) >= 8]
    important = [kw for kw in keywords_raw if 5 <= kw.get("priority", 0) <= 7]

    def _coverage(kws: list[dict]) -> tuple[float, list[str]]:
        if not kws:
            return 1.0, []
        missing = [kw["text"] for kw in kws if not keyword_found(kw["text"], text_lower, text_prefixes)]
        found = len(kws) - len(missing)
        return found / len(kws), missing

    mh_cov, mh_missing = _coverage(must_have)
    imp_cov, _ = _coverage(important)
    overall_cov, _ = _coverage(keywords_raw)
    below = bool(must_have and mh_cov < threshold)

    if below:
        logger.warning(
            "Keyword coverage below threshold: must-have %.0f%% (missing: %s)",
            mh_cov * 100, ", ".join(mh_missing),
        )
    else:
        logger.info(
            "Keyword coverage: must-have %.0f%%, important %.0f%%, overall %.0f%%",
            mh_cov * 100, imp_cov * 100, overall_cov * 100,
        )

    return {
        "must_have_coverage": mh_cov,
        "must_have_missing": mh_missing,
        "important_coverage": imp_cov,
        "overall_coverage": overall_cov,
        "below_threshold": below,
    }


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
