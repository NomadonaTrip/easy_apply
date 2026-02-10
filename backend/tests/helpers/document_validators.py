"""Reusable structural validation fixtures for LLM-generated documents.

Epic 4 Retro Item 7: Test helpers for validating generated document structure -
section presence, keyword inclusion, constraint compliance.

Usage in tests:
    from tests.helpers.document_validators import validate_resume, validate_cover_letter

    violations = validate_resume(content, keywords=["Python", "FastAPI"], company_name="TechCorp")
    assert violations == [], f"Resume validation failed: {violations}"
"""

import re


# ============================================================================
# Forbidden characters and phrases
# ============================================================================

_FORBIDDEN_CHARS = {
    "\u2014": "em-dash",
    "\u2013": "en-dash",
    "\u201c": "left smart double quote",
    "\u201d": "right smart double quote",
    "\u2018": "left smart single quote",
    "\u2019": "right smart single quote",
}

_AI_CLICHES = [
    "leverage",
    "synergy",
    "spearhead",
    "utilize",
    "facilitate",
]

_RESUME_OVERUSED_PHRASES = [
    "passionate about",
    "results-driven",
    "team player",
]

_COVER_LETTER_GENERIC_OPENINGS = [
    "i am writing to apply for",
]

_COVER_LETTER_GENERIC_CLAIMS = [
    "i believe i would be a great fit",
]

# Common contractions for tone detection
_CONTRACTIONS = [
    "i'm", "i've", "i'd", "i'll",
    "you're", "you've", "you'd", "you'll",
    "we're", "we've", "we'd", "we'll",
    "they're", "they've", "they'd", "they'll",
    "it's", "that's", "there's", "here's",
    "don't", "doesn't", "didn't", "isn't", "aren't",
    "wasn't", "weren't", "won't", "wouldn't", "couldn't",
    "shouldn't", "can't", "haven't", "hasn't", "hadn't",
    "let's", "who's", "what's",
]


# ============================================================================
# Resume Validation
# ============================================================================

_RESUME_REQUIRED_SECTIONS = [
    ("Professional Summary", r"##\s+Professional\s+Summary"),
    ("Experience", r"##\s+Experience"),
    ("Skills", r"##\s+Skills"),
    ("Education", r"##\s+Education"),
]

_RESUME_SECTION_ORDER = [
    "Professional Summary",
    "Experience",
    "Skills",
    "Education",
]


def validate_resume_structure(content: str) -> list[str]:
    """Validate resume has required sections in correct order.

    Checks:
    - H1 header (candidate name) present
    - All required sections present (Professional Summary, Experience, Skills, Education)
    - Sections appear in the correct order
    - At least one experience entry with bullet points

    Returns list of violation strings. Empty list = valid.
    """
    violations = []

    # H1 header (candidate name)
    if not re.search(r"^#\s+\S", content, re.MULTILINE):
        violations.append("Missing H1 header (candidate name)")

    # Required sections
    section_positions = {}
    for section_name, pattern in _RESUME_REQUIRED_SECTIONS:
        match = re.search(pattern, content, re.IGNORECASE)
        if not match:
            violations.append(f"Missing required section: {section_name}")
        else:
            section_positions[section_name] = match.start()

    # Section order (only check if all sections found)
    if len(section_positions) == len(_RESUME_SECTION_ORDER):
        ordered = [
            section_positions[name]
            for name in _RESUME_SECTION_ORDER
            if name in section_positions
        ]
        if ordered != sorted(ordered):
            violations.append(
                f"Sections out of order. Expected: {', '.join(_RESUME_SECTION_ORDER)}"
            )

    # Experience entries with bullet points
    exp_match = re.search(r"##\s+Experience", content, re.IGNORECASE)
    if exp_match:
        # Look for content after Experience header until next ## section
        exp_section = content[exp_match.end():]
        next_section = re.search(r"\n##\s+", exp_section)
        if next_section:
            exp_section = exp_section[:next_section.start()]

        # Should have at least one sub-heading (### Title | Company | Dates)
        if not re.search(r"###\s+.+", exp_section):
            violations.append(
                "Experience section missing entries (expected ### sub-headings)"
            )

        # Should have bullet points
        if not re.search(r"^-\s+", exp_section, re.MULTILINE):
            violations.append(
                "Experience section missing bullet points"
            )

    return violations


def validate_resume_constraints(content: str) -> list[str]:
    """Validate resume formatting constraints.

    Checks:
    - No em-dashes, en-dashes, smart quotes
    - No AI cliches or overused phrases
    - Word count between 100-800
    - Uses markdown format

    Returns list of violation strings. Empty list = valid.
    """
    violations = []
    content_lower = content.lower()

    # Forbidden characters
    for char, name in _FORBIDDEN_CHARS.items():
        if char in content:
            violations.append(f"Forbidden character: {name} ({repr(char)})")

    # AI cliches
    for cliche in _AI_CLICHES:
        if cliche in content_lower:
            violations.append(f"AI cliche detected: '{cliche}'")

    # Overused phrases
    for phrase in _RESUME_OVERUSED_PHRASES:
        if phrase in content_lower:
            violations.append(f"Overused phrase detected: '{phrase}'")

    # Word count
    words = content.split()
    word_count = len(words)
    if word_count < 100:
        violations.append(f"Word count {word_count} below minimum 100")
    if word_count > 800:
        violations.append(f"Word count {word_count} exceeds maximum 800")

    return violations


def validate_resume_keywords(
    content: str, keywords: list[str], min_density: float = 0.4
) -> list[str]:
    """Validate keyword presence in resume.

    Checks that at least min_density (default 40%) of top-5 keywords appear.

    Args:
        content: Resume text content.
        keywords: List of keywords in priority order.
        min_density: Minimum fraction of keywords that must appear (0.0-1.0).

    Returns list of violation strings. Empty list = valid.
    """
    violations = []
    content_lower = content.lower()

    top_keywords = keywords[:5]
    if not top_keywords:
        return violations

    matched = [kw for kw in top_keywords if kw.lower() in content_lower]
    density = len(matched) / len(top_keywords)

    if density < min_density:
        missing = [kw for kw in top_keywords if kw.lower() not in content_lower]
        violations.append(
            f"Keyword density {density:.0%} below minimum {min_density:.0%}. "
            f"Missing: {', '.join(missing)}"
        )

    return violations


def validate_resume(
    content: str,
    keywords: list[str],
    company_name: str,
) -> list[str]:
    """Full resume validation combining structure, constraints, and keywords.

    Args:
        content: Generated resume text.
        keywords: List of keywords in priority order.
        company_name: Target company name (must be referenced).

    Returns list of violation strings. Empty list = valid.
    """
    violations = []
    violations.extend(validate_resume_structure(content))
    violations.extend(validate_resume_constraints(content))
    violations.extend(validate_resume_keywords(content, keywords))

    # Company name reference
    if company_name.lower() not in content.lower():
        violations.append(
            f"Company name '{company_name}' not referenced in resume"
        )

    return violations


# ============================================================================
# Cover Letter Validation
# ============================================================================


def validate_cover_letter_structure(content: str) -> list[str]:
    """Validate cover letter has required structural elements.

    Checks:
    - Starts with greeting ("Dear")
    - Contains closing ("Sincerely")
    - Has 3-4 paragraphs

    Returns list of violation strings. Empty list = valid.
    """
    violations = []

    # Greeting
    stripped = content.strip()
    if not stripped.lower().startswith("dear"):
        violations.append("Missing greeting (should start with 'Dear')")

    # Closing
    if "sincerely" not in content.lower():
        violations.append("Missing closing (should contain 'Sincerely')")

    # Paragraph count: split by blank lines, filter empty
    paragraphs = [
        p.strip()
        for p in re.split(r"\n\s*\n", stripped)
        if p.strip()
    ]
    # Exclude greeting line and closing line from paragraph count
    body_paragraphs = []
    for p in paragraphs:
        p_lower = p.strip().lower()
        # Skip greeting-only paragraph
        if p_lower.startswith("dear") and len(p.split("\n")) <= 1:
            continue
        # Skip closing-only paragraph (Sincerely + name)
        if p_lower.startswith("sincerely"):
            continue
        body_paragraphs.append(p)

    if len(body_paragraphs) < 3:
        violations.append(
            f"Too few body paragraphs: {len(body_paragraphs)} (expected 3-4)"
        )
    elif len(body_paragraphs) > 4:
        violations.append(
            f"Too many body paragraphs: {len(body_paragraphs)} (expected 3-4)"
        )

    return violations


def validate_cover_letter_constraints(content: str) -> list[str]:
    """Validate cover letter formatting constraints.

    Checks:
    - No em-dashes, en-dashes, smart quotes
    - No AI cliches
    - No generic openings or claims
    - Word count 150-400
    - No markdown formatting

    Returns list of violation strings. Empty list = valid.
    """
    violations = []
    content_lower = content.lower()

    # Forbidden characters
    for char, name in _FORBIDDEN_CHARS.items():
        if char in content:
            violations.append(f"Forbidden character: {name} ({repr(char)})")

    # AI cliches
    for cliche in _AI_CLICHES:
        if cliche in content_lower:
            violations.append(f"AI cliche detected: '{cliche}'")

    # Generic openings
    for opening in _COVER_LETTER_GENERIC_OPENINGS:
        if opening in content_lower:
            violations.append(f"Generic opening detected: '{opening}'")

    # Generic claims
    for claim in _COVER_LETTER_GENERIC_CLAIMS:
        if claim in content_lower:
            violations.append(f"Generic claim detected: '{claim}'")

    # Word count
    words = content.split()
    word_count = len(words)
    if word_count < 150:
        violations.append(f"Word count {word_count} below minimum 150")
    if word_count > 400:
        violations.append(f"Word count {word_count} exceeds maximum 400")

    # No markdown formatting
    if re.search(r"^#{1,6}\s+", content, re.MULTILINE):
        violations.append("Markdown headers found (cover letter should be plain text)")
    if re.search(r"\*\*[^*]+\*\*", content):
        violations.append("Markdown bold found (cover letter should be plain text)")

    return violations


def validate_cover_letter_tone(content: str, expected_tone: str) -> list[str]:
    """Validate cover letter matches the requested tone.

    Tone heuristics:
    - formal: Avg sentence length >= 15 words, no contractions
    - conversational: At least 1 contraction OR avg sentence length < 20
    - match_culture: Company name referenced (validated separately)

    Returns list of violation strings. Empty list = valid.
    """
    violations = []
    content_lower = content.lower()

    # Split into sentences (rough heuristic)
    sentences = re.split(r"[.!?]+", content)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]

    if not sentences:
        violations.append("No sentences detected for tone analysis")
        return violations

    avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)

    has_contractions = any(c in content_lower for c in _CONTRACTIONS)

    if expected_tone == "formal":
        if has_contractions:
            violations.append(
                "Formal tone requested but contractions found"
            )
        if avg_sentence_length < 15:
            violations.append(
                f"Formal tone requested but avg sentence length "
                f"({avg_sentence_length:.1f} words) suggests informal style"
            )

    elif expected_tone == "conversational":
        # Conversational should have EITHER contractions OR shorter sentences
        if not has_contractions and avg_sentence_length >= 20:
            violations.append(
                "Conversational tone requested but no contractions found "
                "and avg sentence length is formal"
            )

    # match_culture: we only check company name reference, which is done
    # in validate_cover_letter() via the company_name check

    return violations


def validate_cover_letter_keywords(
    content: str, keywords: list[str], min_density: float = 0.4
) -> list[str]:
    """Validate keyword presence in cover letter.

    Same logic as resume keyword validation.
    """
    return validate_resume_keywords(content, keywords, min_density)


def validate_cover_letter(
    content: str,
    keywords: list[str],
    company_name: str,
    tone: str = "formal",
) -> list[str]:
    """Full cover letter validation combining structure, constraints, tone, and keywords.

    Args:
        content: Generated cover letter text.
        keywords: List of keywords in priority order.
        company_name: Target company name (must be referenced).
        tone: Expected tone ("formal", "conversational", "match_culture").

    Returns list of violation strings. Empty list = valid.
    """
    violations = []
    violations.extend(validate_cover_letter_structure(content))
    violations.extend(validate_cover_letter_constraints(content))
    violations.extend(validate_cover_letter_tone(content, tone))
    violations.extend(validate_cover_letter_keywords(content, keywords))

    # Company name reference
    if company_name.lower() not in content.lower():
        violations.append(
            f"Company name '{company_name}' not referenced in cover letter"
        )

    return violations
