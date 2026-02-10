"""Tests for document validation fixtures (Epic 4 Retro Item 7).

Validates that the structural validation helpers correctly identify valid
and invalid generated documents without brittle prose comparison.
"""

import pytest

from tests.helpers.document_validators import (
    validate_resume_structure,
    validate_resume_constraints,
    validate_resume_keywords,
    validate_resume,
    validate_cover_letter_structure,
    validate_cover_letter_constraints,
    validate_cover_letter_tone,
    validate_cover_letter_keywords,
    validate_cover_letter,
)


# ============================================================================
# Test fixtures: sample documents
# ============================================================================

VALID_RESUME = """# Jane Doe

jane.doe@email.com | (555) 123-4567 | github.com/janedoe

## Professional Summary

Experienced Python developer with 6 years building scalable backend systems
using FastAPI and React frontends. Skilled in cloud infrastructure and CI/CD
pipeline optimization for TechCorp-scale applications.

## Experience

### Senior Backend Developer | DataFlow Inc | 2021-Present
- Architected microservices handling 50K requests/second using Python and FastAPI
- Reduced API response times by 40% through query optimization and caching
- Led migration from monolith to event-driven architecture serving 2M users
- Implemented comprehensive test suites achieving 95% code coverage

### Software Engineer | StartupCo | 2018-2021
- Built RESTful APIs with Python and Flask, later migrated to FastAPI
- Designed React dashboard consuming real-time WebSocket data feeds
- Deployed applications on AWS using Terraform and GitHub Actions CI/CD

## Skills

Python, FastAPI, React, TypeScript, PostgreSQL, Redis, Docker, AWS, Terraform,
CI/CD, REST APIs, microservices, event-driven architecture

## Education

B.S. Computer Science, State University, 2018
AWS Solutions Architect Associate, 2022
"""

VALID_COVER_LETTER = """\
Dear Hiring Manager,

When I discovered the Senior Python Developer opening at TechCorp, I was \
immediately drawn to your commitment to AI-driven innovation and your \
recent expansion into enterprise solutions. With six years of experience \
building scalable backend systems, I'm excited about the opportunity to \
contribute to your engineering team.

Throughout my career, I've focused on Python and FastAPI development at \
scale. At DataFlow Inc, I architected microservices handling 50,000 \
requests per second and reduced API response times by 40% through \
strategic optimization. These experiences align directly with TechCorp's \
need for a developer who can build robust, high-performance systems.

My background in React frontend development and CI/CD pipeline automation \
gives me a full-stack perspective that complements your team's goals. I've \
led migrations from monolithic to event-driven architectures, and I \
understand the challenges of maintaining quality at scale - exactly the \
kind of work your job posting describes.

I would welcome the chance to discuss how my experience building scalable \
Python systems can support TechCorp's growth. I'm available for a \
conversation at your convenience.

Sincerely,
Jane Doe
"""


# ============================================================================
# Resume Structure Tests
# ============================================================================


class TestResumeStructure:
    """Test resume structural validation."""

    def test_valid_resume_has_no_structure_violations(self):
        violations = validate_resume_structure(VALID_RESUME)
        assert violations == []

    def test_missing_h1_header(self):
        content = VALID_RESUME.replace("# Jane Doe", "Jane Doe")
        violations = validate_resume_structure(content)
        assert any("Missing H1 header" in v for v in violations)

    def test_missing_professional_summary(self):
        content = VALID_RESUME.replace("## Professional Summary", "## About Me")
        violations = validate_resume_structure(content)
        assert any("Professional Summary" in v for v in violations)

    def test_missing_experience_section(self):
        content = VALID_RESUME.replace("## Experience", "## Work History")
        violations = validate_resume_structure(content)
        assert any("Experience" in v for v in violations)

    def test_missing_skills_section(self):
        content = VALID_RESUME.replace("## Skills", "## Technologies")
        violations = validate_resume_structure(content)
        assert any("Skills" in v for v in violations)

    def test_missing_education_section(self):
        content = VALID_RESUME.replace("## Education", "## Certifications")
        violations = validate_resume_structure(content)
        assert any("Education" in v for v in violations)

    def test_sections_out_of_order(self):
        # Put Skills before Experience
        content = """# Jane Doe

## Professional Summary

Summary text here for the position.

## Skills

Python, FastAPI

## Experience

### Developer | Company | 2020-Present
- Did things with code

## Education

B.S. Computer Science
"""
        violations = validate_resume_structure(content)
        assert any("out of order" in v for v in violations)

    def test_experience_missing_bullet_points(self):
        # Replace all bullet-pointed lines with plain text
        content = VALID_RESUME
        import re
        content = re.sub(r"^- .+$", "", content, flags=re.MULTILINE)
        violations = validate_resume_structure(content)
        assert any("bullet points" in v for v in violations)


# ============================================================================
# Resume Constraints Tests
# ============================================================================


class TestResumeConstraints:
    """Test resume formatting constraint validation."""

    def test_valid_resume_has_no_constraint_violations(self):
        violations = validate_resume_constraints(VALID_RESUME)
        assert violations == []

    def test_detects_em_dash(self):
        content = VALID_RESUME.replace("2021-Present", "2021\u2014Present")
        violations = validate_resume_constraints(content)
        assert any("em-dash" in v for v in violations)

    def test_detects_en_dash(self):
        content = VALID_RESUME.replace("2021-Present", "2021\u2013Present")
        violations = validate_resume_constraints(content)
        assert any("en-dash" in v for v in violations)

    def test_detects_smart_quotes(self):
        content = VALID_RESUME + "\n\u201cGreat work\u201d"
        violations = validate_resume_constraints(content)
        assert any("smart" in v.lower() for v in violations)

    def test_detects_ai_cliche_leverage(self):
        content = VALID_RESUME.replace(
            "Architected microservices",
            "Leveraged microservices"
        )
        violations = validate_resume_constraints(content)
        assert any("leverage" in v for v in violations)

    def test_detects_ai_cliche_synergy(self):
        content = VALID_RESUME + "\nCreated synergy between teams."
        violations = validate_resume_constraints(content)
        assert any("synergy" in v for v in violations)

    def test_detects_overused_passionate_about(self):
        content = VALID_RESUME.replace(
            "Experienced Python developer",
            "Passionate about Python development"
        )
        violations = validate_resume_constraints(content)
        assert any("passionate about" in v for v in violations)

    def test_detects_word_count_too_high(self):
        # Add enough words to exceed 800 (resume is ~200 words)
        extra = " word" * 700
        content = VALID_RESUME + extra
        violations = validate_resume_constraints(content)
        assert any("exceeds maximum 800" in v for v in violations)

    def test_detects_word_count_too_low(self):
        content = "# Name\n## Professional Summary\nShort."
        violations = validate_resume_constraints(content)
        assert any("below minimum 100" in v for v in violations)


# ============================================================================
# Resume Keywords Tests
# ============================================================================


class TestResumeKeywords:
    """Test resume keyword density validation."""

    def test_all_keywords_present(self):
        keywords = ["Python", "FastAPI", "React", "AWS", "Docker"]
        violations = validate_resume_keywords(VALID_RESUME, keywords)
        assert violations == []

    def test_partial_keywords_above_threshold(self):
        # 3 of 5 = 60% >= 40%
        keywords = ["Python", "FastAPI", "Kubernetes", "Scala", "Hadoop"]
        violations = validate_resume_keywords(VALID_RESUME, keywords)
        assert violations == []

    def test_insufficient_keywords(self):
        # 1 of 5 = 20% < 40% ("scala" is substring of "scalable" so avoid it)
        keywords = ["Python", "Kubernetes", "Haskell", "Erlang", "Clojure"]
        violations = validate_resume_keywords(VALID_RESUME, keywords)
        assert any("Keyword density" in v for v in violations)
        assert any("Missing" in v for v in violations)

    def test_empty_keywords_no_violation(self):
        violations = validate_resume_keywords(VALID_RESUME, [])
        assert violations == []

    def test_case_insensitive_matching(self):
        keywords = ["python", "fastapi", "react", "aws", "docker"]
        violations = validate_resume_keywords(VALID_RESUME, keywords)
        assert violations == []

    def test_only_checks_top_5(self):
        # First 5 are present, 6th is not - should pass
        keywords = [
            "Python", "FastAPI", "React", "AWS", "Docker",
            "NonexistentTech",
        ]
        violations = validate_resume_keywords(VALID_RESUME, keywords)
        assert violations == []


# ============================================================================
# Full Resume Validation
# ============================================================================


class TestFullResumeValidation:
    """Test combined resume validation."""

    def test_valid_resume_passes_full_validation(self):
        keywords = ["Python", "FastAPI", "React", "AWS", "CI/CD"]
        violations = validate_resume(VALID_RESUME, keywords, "TechCorp")
        assert violations == []

    def test_missing_company_name(self):
        keywords = ["Python", "FastAPI"]
        violations = validate_resume(VALID_RESUME, keywords, "UnknownCorp")
        assert any("UnknownCorp" in v for v in violations)

    def test_multiple_violations_reported(self):
        bad_resume = "# Name\n## Skills\nSynergy leverage."
        keywords = ["Python", "FastAPI", "React", "AWS", "Docker"]
        violations = validate_resume(bad_resume, keywords, "TechCorp")
        # Should have multiple violations (missing sections, constraints, keywords, company)
        assert len(violations) > 3


# ============================================================================
# Cover Letter Structure Tests
# ============================================================================


class TestCoverLetterStructure:
    """Test cover letter structural validation."""

    def test_valid_cover_letter_has_no_structure_violations(self):
        violations = validate_cover_letter_structure(VALID_COVER_LETTER)
        assert violations == []

    def test_missing_greeting(self):
        content = "Hi there,\n\n" + VALID_COVER_LETTER.split("\n\n", 1)[1]
        violations = validate_cover_letter_structure(content)
        assert any("greeting" in v.lower() for v in violations)

    def test_missing_closing(self):
        content = VALID_COVER_LETTER.replace("Sincerely,\nJane Doe", "Thanks!")
        violations = validate_cover_letter_structure(content)
        assert any("closing" in v.lower() for v in violations)

    def test_too_few_paragraphs(self):
        content = """\
Dear Hiring Manager,

I want this job at TechCorp because I have Python and FastAPI skills.

Sincerely,
Jane Doe
"""
        violations = validate_cover_letter_structure(content)
        assert any("Too few" in v for v in violations)

    def test_too_many_paragraphs(self):
        content = """\
Dear Hiring Manager,

First paragraph about TechCorp and Python and FastAPI experience.

Second paragraph about accomplishments and projects completed.

Third paragraph about team collaboration and problem solving skills.

Fourth paragraph about cloud infrastructure and deployment experience.

Fifth paragraph about additional qualifications and certifications earned.

Sincerely,
Jane Doe
"""
        violations = validate_cover_letter_structure(content)
        assert any("Too many" in v for v in violations)


# ============================================================================
# Cover Letter Constraints Tests
# ============================================================================


class TestCoverLetterConstraints:
    """Test cover letter formatting constraint validation."""

    def test_valid_cover_letter_has_no_constraint_violations(self):
        violations = validate_cover_letter_constraints(VALID_COVER_LETTER)
        assert violations == []

    def test_detects_em_dash(self):
        content = VALID_COVER_LETTER.replace(" - ", " \u2014 ")
        violations = validate_cover_letter_constraints(content)
        assert any("em-dash" in v for v in violations)

    def test_detects_ai_cliche(self):
        content = VALID_COVER_LETTER + "\nI leverage my skills daily."
        violations = validate_cover_letter_constraints(content)
        assert any("leverage" in v for v in violations)

    def test_detects_generic_opening(self):
        content = VALID_COVER_LETTER.replace(
            "When I discovered the Senior Python Developer opening at TechCorp",
            "I am writing to apply for the Senior Python Developer position"
        )
        violations = validate_cover_letter_constraints(content)
        assert any("Generic opening" in v for v in violations)

    def test_detects_generic_claim(self):
        content = VALID_COVER_LETTER + "\nI believe I would be a great fit for this role."
        violations = validate_cover_letter_constraints(content)
        assert any("Generic claim" in v for v in violations)

    def test_detects_markdown_headers(self):
        content = VALID_COVER_LETTER + "\n## My Skills\n\nSome skills here."
        violations = validate_cover_letter_constraints(content)
        assert any("Markdown headers" in v for v in violations)

    def test_detects_markdown_bold(self):
        content = VALID_COVER_LETTER.replace("TechCorp", "**TechCorp**")
        violations = validate_cover_letter_constraints(content)
        assert any("Markdown bold" in v for v in violations)

    def test_detects_word_count_too_low(self):
        content = "Dear Manager,\n\nShort letter.\n\nSincerely,\nJane"
        violations = validate_cover_letter_constraints(content)
        assert any("below minimum 150" in v for v in violations)

    def test_detects_word_count_too_high(self):
        extra = " word" * 300
        content = VALID_COVER_LETTER + extra
        violations = validate_cover_letter_constraints(content)
        assert any("exceeds maximum 400" in v for v in violations)


# ============================================================================
# Cover Letter Tone Tests
# ============================================================================


class TestCoverLetterTone:
    """Test cover letter tone validation."""

    def test_formal_tone_no_contractions(self):
        # VALID_COVER_LETTER uses "I'm" and "I've" which are contractions
        formal_content = VALID_COVER_LETTER.replace("I'm", "I am").replace("I've", "I have")
        violations = validate_cover_letter_tone(formal_content, "formal")
        assert not any("contractions" in v for v in violations)

    def test_formal_tone_rejects_contractions(self):
        content = "I'm excited to join your team. It's a great opportunity. I've worked on many projects. We're going to succeed together. This isn't just another role for me."
        violations = validate_cover_letter_tone(content, "formal")
        assert any("contractions" in v for v in violations)

    def test_conversational_tone_accepts_contractions(self):
        violations = validate_cover_letter_tone(VALID_COVER_LETTER, "conversational")
        assert not any("contractions" in v for v in violations)

    def test_match_culture_tone_always_passes(self):
        # match_culture doesn't have specific heuristic constraints
        violations = validate_cover_letter_tone(VALID_COVER_LETTER, "match_culture")
        assert violations == []


# ============================================================================
# Cover Letter Keywords Tests
# ============================================================================


class TestCoverLetterKeywords:
    """Test cover letter keyword density validation."""

    def test_keywords_present(self):
        keywords = ["Python", "FastAPI", "React", "CI/CD", "TechCorp"]
        violations = validate_cover_letter_keywords(VALID_COVER_LETTER, keywords)
        assert violations == []

    def test_insufficient_keywords(self):
        keywords = ["Rust", "Kubernetes", "Scala", "Hadoop", "Spark"]
        violations = validate_cover_letter_keywords(VALID_COVER_LETTER, keywords)
        assert any("Keyword density" in v for v in violations)


# ============================================================================
# Full Cover Letter Validation
# ============================================================================


class TestFullCoverLetterValidation:
    """Test combined cover letter validation."""

    def test_valid_cover_letter_passes_full_validation(self):
        keywords = ["Python", "FastAPI", "React"]
        violations = validate_cover_letter(
            VALID_COVER_LETTER,
            keywords,
            company_name="TechCorp",
            tone="conversational",
        )
        assert violations == [], f"Violations: {violations}"

    def test_missing_company_name(self):
        keywords = ["Python"]
        violations = validate_cover_letter(
            VALID_COVER_LETTER,
            keywords,
            company_name="UnknownCorp",
            tone="formal",
        )
        assert any("UnknownCorp" in v for v in violations)

    def test_multiple_violations_reported(self):
        bad_letter = "Hi there,\n\nSynergy leverage.\n\nBye!"
        keywords = ["Python", "FastAPI", "React", "AWS", "Docker"]
        violations = validate_cover_letter(
            bad_letter, keywords, company_name="TechCorp", tone="formal"
        )
        assert len(violations) > 3
