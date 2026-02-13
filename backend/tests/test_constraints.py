"""Tests for output constraint enforcement (Story 5-4)."""

import pytest

from app.utils.constraints import (
    AI_CLICHES,
    ALL_CLICHES,
    CHARACTER_REPLACEMENTS,
    ATS_RULES,
    Violation,
    ViolationSeverity,
    detect_cliches,
    detect_character_violations,
    detect_ats_violations,
    get_cliche_alternative,
)
from app.utils.text_processing import (
    enforce_output_constraints,
    enforce_output_constraints_detailed,
    ConstraintResult,
)


# ── Task 1: Constraint Rules Definitions ──


class TestConstraintRulesDefinitions:
    """Verify comprehensive constraint rules are defined correctly."""

    def test_ai_cliches_has_expected_categories(self):
        expected = {
            "corporate_buzzwords",
            "action_verbs_overused",
            "self_description_cliches",
            "filler_phrases",
        }
        assert set(AI_CLICHES.keys()) == expected

    def test_all_cliches_is_flat_list(self):
        assert isinstance(ALL_CLICHES, list)
        assert len(ALL_CLICHES) > 0
        # Every cliché should be a string
        assert all(isinstance(c, str) for c in ALL_CLICHES)

    def test_all_cliches_matches_dict_total(self):
        total = sum(len(terms) for terms in AI_CLICHES.values())
        assert len(ALL_CLICHES) == total

    def test_key_cliches_present(self):
        assert "leverage" in ALL_CLICHES
        assert "synergy" in ALL_CLICHES
        assert "spearheaded" in ALL_CLICHES
        assert "passionate about" in ALL_CLICHES
        assert "cutting-edge" in ALL_CLICHES

    def test_character_replacements_includes_em_dash(self):
        assert "\u2014" in CHARACTER_REPLACEMENTS  # em-dash
        assert CHARACTER_REPLACEMENTS["\u2014"] == "-"

    def test_character_replacements_includes_en_dash(self):
        assert "\u2013" in CHARACTER_REPLACEMENTS  # en-dash
        assert CHARACTER_REPLACEMENTS["\u2013"] == "-"

    def test_character_replacements_includes_smart_quotes(self):
        assert "\u201c" in CHARACTER_REPLACEMENTS  # left double
        assert "\u201d" in CHARACTER_REPLACEMENTS  # right double
        assert "\u2018" in CHARACTER_REPLACEMENTS  # left single
        assert "\u2019" in CHARACTER_REPLACEMENTS  # right single

    def test_character_replacements_includes_ellipsis(self):
        assert "\u2026" in CHARACTER_REPLACEMENTS
        assert CHARACTER_REPLACEMENTS["\u2026"] == "..."

    def test_ats_rules_defined(self):
        assert "avoid_tables" in ATS_RULES
        assert ATS_RULES["avoid_tables"] is True
        assert "avoid_columns" in ATS_RULES
        assert "avoid_graphics" in ATS_RULES


# ── Task 2: Constraint Detection ──


class TestClicheDetection:
    """Test AI cliché detection with positions and severity."""

    def test_detects_single_cliche(self):
        violations = detect_cliches("I leveraged my skills effectively")
        assert len(violations) >= 1
        assert any("leveraged" in v.message.lower() for v in violations)

    def test_detects_multiple_cliches(self):
        text = "I leveraged my skills to spearhead innovative solutions"
        violations = detect_cliches(text)
        assert len(violations) >= 3

    def test_clean_text_has_no_violations(self):
        text = "I used my skills to lead effective solutions"
        violations = detect_cliches(text)
        assert len(violations) == 0

    def test_case_insensitive_detection(self):
        violations = detect_cliches("LEVERAGE your SYNERGY")
        assert len(violations) >= 2

    def test_violation_has_position(self):
        violations = detect_cliches("I leverage technology")
        assert len(violations) >= 1
        assert violations[0].position is not None
        assert violations[0].position >= 0

    def test_violation_has_correct_type(self):
        violations = detect_cliches("I leverage technology")
        assert violations[0].type == "ai_cliche"

    def test_violation_severity_is_warning(self):
        violations = detect_cliches("proven track record of success")
        assert all(v.severity == ViolationSeverity.WARNING for v in violations)

    def test_word_boundary_matching(self):
        # "agile" should match as standalone, not inside "fragile"
        violations_standalone = detect_cliches("We use agile methodology")
        violations_embedded = detect_cliches("This is a fragile system")
        assert len(violations_standalone) >= 1
        assert len(violations_embedded) == 0

    def test_multiword_cliche_detection(self):
        violations = detect_cliches("Our proven track record speaks for itself")
        assert any("proven track record" in v.message.lower() for v in violations)


class TestCharacterViolationDetection:
    """Test problematic character detection."""

    def test_detects_em_dash(self):
        violations = detect_character_violations("word\u2014word")
        assert len(violations) >= 1
        assert violations[0].type == "character"
        assert violations[0].auto_fixable is True

    def test_detects_smart_quotes(self):
        violations = detect_character_violations("\u201cHello\u201d")
        assert len(violations) >= 2

    def test_clean_text_no_violations(self):
        violations = detect_character_violations("Normal text with - hyphens and 'quotes'")
        assert len(violations) == 0

    def test_character_violation_severity_is_error(self):
        violations = detect_character_violations("word\u2014word")
        assert all(v.severity == ViolationSeverity.ERROR for v in violations)

    def test_character_violation_has_suggestion(self):
        violations = detect_character_violations("word\u2014word")
        assert violations[0].suggestion == "-"

    def test_detects_ellipsis_character(self):
        violations = detect_character_violations("Wait\u2026")
        assert len(violations) >= 1


class TestATSViolationDetection:
    """Test ATS formatting violation detection."""

    def test_detects_table_like_structures(self):
        violations = detect_ats_violations("| col1 | col2 | col3 |")
        assert len(violations) >= 1
        assert violations[0].type == "ats_formatting"

    def test_no_false_positive_on_inline_pipes(self):
        text = "We use option A | option B | option C in our pipeline"
        violations = detect_ats_violations(text)
        table_violations = [v for v in violations if "table" in v.message.lower()]
        assert len(table_violations) == 0

    def test_clean_text_no_ats_violations(self):
        text = "Normal resume text\nWith standard formatting"
        violations = detect_ats_violations(text)
        assert len(violations) == 0

    def test_long_line_detection(self):
        long_line = "A" * 150
        violations = detect_ats_violations(long_line)
        assert any("exceeds" in v.message for v in violations)


# ── Task 3: Auto-Correction ──


class TestClicheAlternatives:
    """Test cliché alternative suggestions."""

    def test_leverage_alternative(self):
        assert get_cliche_alternative("leverage") == "use"
        assert get_cliche_alternative("leveraged") == "used"
        assert get_cliche_alternative("leveraging") == "using"

    def test_spearhead_alternative(self):
        assert get_cliche_alternative("spearhead") == "lead"
        assert get_cliche_alternative("spearheaded") == "led"

    def test_utilize_alternative(self):
        assert get_cliche_alternative("utilize") == "use"

    def test_unknown_cliche_returns_none(self):
        assert get_cliche_alternative("unknown_term") is None

    def test_case_insensitive_lookup(self):
        assert get_cliche_alternative("Leverage") == "use"
        assert get_cliche_alternative("LEVERAGE") == "use"


# ── Task 4: Constraint Validation Pipeline ──


class TestEnforceOutputConstraints:
    """Test the simple constraint enforcement (returns cleaned text)."""

    def test_em_dash_replacement(self):
        result = enforce_output_constraints("I led teams \u2014 managing projects")
        assert "\u2014" not in result
        assert "-" in result

    def test_en_dash_replacement(self):
        result = enforce_output_constraints("2020\u20132023")
        assert "\u2013" not in result
        assert "-" in result

    def test_smart_quote_replacement(self):
        result = enforce_output_constraints("\u201cHello\u201d and \u2018world\u2019")
        assert "\u201c" not in result
        assert "\u201d" not in result
        assert "\u2018" not in result
        assert "\u2019" not in result

    def test_whitespace_cleanup(self):
        result = enforce_output_constraints("Line one\n\n\n\nLine two   with   spaces")
        assert "\n\n\n" not in result
        assert "   " not in result

    def test_empty_text(self):
        assert enforce_output_constraints("") == ""
        assert enforce_output_constraints(None) == ""

    def test_clean_text_unchanged(self):
        text = "Clean text with normal formatting"
        result = enforce_output_constraints(text)
        assert result == text

    def test_strips_leading_trailing_whitespace(self):
        result = enforce_output_constraints("  hello  ")
        assert result == "hello"


class TestEnforceOutputConstraintsDetailed:
    """Test the detailed constraint enforcement (returns ConstraintResult)."""

    def test_returns_constraint_result(self):
        result = enforce_output_constraints_detailed("some text")
        assert isinstance(result, ConstraintResult)

    def test_counts_fixed_violations(self):
        text = "word\u2014word and \u201cquotes\u201d"
        result = enforce_output_constraints_detailed(text)
        assert result.violations_fixed > 0

    def test_counts_remaining_violations(self):
        text = "I leveraged my skills to spearhead projects"
        result = enforce_output_constraints_detailed(text)
        assert result.violations_remaining > 0

    def test_violations_list_populated(self):
        text = "I leveraged my synergy"
        result = enforce_output_constraints_detailed(text)
        assert len(result.violations) > 0

    def test_cleaned_text_has_no_character_violations(self):
        text = "word\u2014word and \u201cquotes\u201d"
        result = enforce_output_constraints_detailed(text)
        assert "\u2014" not in result.cleaned_text
        assert "\u201c" not in result.cleaned_text
        assert "\u201d" not in result.cleaned_text

    def test_empty_text_returns_empty_result(self):
        result = enforce_output_constraints_detailed("")
        assert result.cleaned_text == ""
        assert result.violations == []
        assert result.violations_fixed == 0
        assert result.violations_remaining == 0

    def test_clean_text_no_violations(self):
        result = enforce_output_constraints_detailed("Clean professional text")
        assert result.violations_fixed == 0
        assert result.violations_remaining == 0

    def test_ellipsis_replacement(self):
        result = enforce_output_constraints_detailed("Wait\u2026 for it")
        assert "\u2026" not in result.cleaned_text
        assert "..." in result.cleaned_text

    def test_bullet_replacement(self):
        result = enforce_output_constraints_detailed("\u2022 Item one\n\u2022 Item two")
        assert "\u2022" not in result.cleaned_text
        assert "- Item one" in result.cleaned_text
