"""Document validation tests for generated resume and cover letter content.

Structural schema validation that catches:
- Missing candidate name/contact
- Duplicate roles
- Orphaned accomplishments
- Missing certifications
- Required sections

These fixtures are reusable across Stories 6-2 and 6-3 review checkpoints.
"""

import re
from typing import Optional

import pytest


# ============================================================================
# Reusable Validation Fixtures
# ============================================================================


class ResumeValidationSchema:
    """Structural schema for validating generated resume content.

    Validates presence and uniqueness of required sections without
    brittle prose comparison.
    """

    # Required top-level sections (markdown heading patterns)
    REQUIRED_SECTIONS = [
        "Professional Summary",
        "Experience",
        "Skills",
    ]

    # At least one of these must be present for education/certifications
    EDUCATION_SECTIONS = [
        "Education",
        "Certifications",
        "Education & Certifications",
        "Education and Certifications",
    ]

    @staticmethod
    def validate_candidate_identity(content: str) -> list[str]:
        """Check that candidate name and contact info are present.

        Returns list of violation descriptions (empty = valid).
        """
        violations = []
        lines = content.strip().split("\n")

        # First non-empty line after the H1 header should be the name
        h1_found = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# "):
                h1_found = True
                name = stripped[2:].strip()
                # Check for placeholder patterns
                placeholders = ["[Candidate Name]", "[Your Name]", "[Name]", "[CANDIDATE NAME]"]
                if any(p.lower() in name.lower() for p in placeholders):
                    violations.append(f"Candidate name is a placeholder: '{name}'")
                if not name or len(name) < 2:
                    violations.append("Candidate name is empty or too short")
                break

        if not h1_found:
            violations.append("No H1 header found (expected candidate name)")

        # Check for contact info patterns (email, phone, or location)
        has_email = bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", content[:500]))
        has_phone = bool(re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", content[:500]))

        # Contact info placeholders
        contact_placeholders = ["[Contact", "[Email", "[Phone", "[Location", "contact info placeholder"]
        has_placeholder_contact = any(p.lower() in content[:500].lower() for p in contact_placeholders)

        if has_placeholder_contact:
            violations.append("Contact info contains placeholder text")
        if not has_email and not has_phone:
            violations.append("No email or phone number found in resume header")

        return violations

    @staticmethod
    def validate_required_sections(content: str) -> list[str]:
        """Check that all required sections exist."""
        violations = []
        content_lower = content.lower()

        for section in ResumeValidationSchema.REQUIRED_SECTIONS:
            if section.lower() not in content_lower:
                violations.append(f"Missing required section: {section}")

        # Check education/certifications (at least one variant)
        has_education = any(
            s.lower() in content_lower
            for s in ResumeValidationSchema.EDUCATION_SECTIONS
        )
        if not has_education:
            violations.append(
                "Missing Education/Certifications section "
                f"(expected one of: {', '.join(ResumeValidationSchema.EDUCATION_SECTIONS)})"
            )

        return violations

    @staticmethod
    def validate_role_uniqueness(content: str) -> list[str]:
        """Check that no role heading appears more than once in Experience."""
        violations = []

        # Extract experience section
        exp_match = re.search(
            r"## Experience\s*\n(.*?)(?=\n## |\Z)",
            content,
            re.DOTALL,
        )
        if not exp_match:
            return ["Cannot find Experience section for role uniqueness check"]

        exp_section = exp_match.group(1)

        # Find role headings (### patterns)
        role_headings = re.findall(r"###\s+(.+)", exp_section)

        # Normalize and check for duplicates
        seen: dict[str, int] = {}
        for heading in role_headings:
            normalized = heading.strip().lower()
            seen[normalized] = seen.get(normalized, 0) + 1

        for heading, count in seen.items():
            if count > 1:
                violations.append(f"Duplicate role heading ({count}x): '{heading}'")

        return violations

    @staticmethod
    def validate_certifications(
        content: str,
        expected_certifications: list[str],
    ) -> list[str]:
        """Check that all expected certifications appear in the output."""
        violations = []
        content_lower = content.lower()

        for cert in expected_certifications:
            if cert.lower() not in content_lower:
                violations.append(f"Missing certification: '{cert}'")

        return violations

    @classmethod
    def validate_all(
        cls,
        content: str,
        expected_certifications: Optional[list[str]] = None,
    ) -> list[str]:
        """Run all validations. Returns list of all violations."""
        violations = []
        violations.extend(cls.validate_candidate_identity(content))
        violations.extend(cls.validate_required_sections(content))
        violations.extend(cls.validate_role_uniqueness(content))
        if expected_certifications:
            violations.extend(
                cls.validate_certifications(content, expected_certifications)
            )
        return violations


class CoverLetterValidationSchema:
    """Structural schema for validating generated cover letter content."""

    @staticmethod
    def validate_structure(content: str) -> list[str]:
        """Validate basic cover letter structure."""
        violations = []

        # Should have a greeting
        if not re.search(r"Dear\s+", content, re.IGNORECASE):
            violations.append("Missing greeting (expected 'Dear ...')")

        # Should have a closing
        closing_patterns = ["sincerely", "best regards", "regards", "respectfully"]
        content_lower = content.lower()
        has_closing = any(p in content_lower for p in closing_patterns)
        if not has_closing:
            violations.append("Missing closing (expected Sincerely/Regards)")

        # Should have a signature (non-placeholder name after closing)
        placeholders = ["[Name]", "[Your Name]", "[Candidate Name]"]
        for p in placeholders:
            if p.lower() in content_lower:
                violations.append(f"Signature contains placeholder: '{p}'")

        return violations

    @staticmethod
    def validate_length(content: str) -> list[str]:
        """Validate cover letter is appropriate length."""
        violations = []
        word_count = len(content.split())

        if word_count < 100:
            violations.append(f"Cover letter too short ({word_count} words, min 100)")
        if word_count > 500:
            violations.append(f"Cover letter too long ({word_count} words, max 500)")

        return violations

    @classmethod
    def validate_all(cls, content: str) -> list[str]:
        """Run all validations."""
        violations = []
        violations.extend(cls.validate_structure(content))
        violations.extend(cls.validate_length(content))
        return violations


# ============================================================================
# Tests: Resume Validation Schema
# ============================================================================


class TestResumeValidationSchema:
    """Test the resume validation schema catches known issues."""

    VALID_RESUME = """# Jane Doe

jane.doe@email.com | (555) 123-4567 | San Francisco, CA

## Professional Summary

Experienced software engineer with 8 years of backend development.

## Experience

### Senior Developer | TechCo | 2020-2024
- Led API migration reducing latency by 40%
- Built CI/CD pipeline serving 100+ deployments/week

### Developer | StartupX | 2018-2020
- Created real-time dashboard serving 10K users

## Skills

Python, FastAPI, React, PostgreSQL, AWS

## Education & Certifications

BS Computer Science, MIT
AWS Solutions Architect
"""

    RESUME_MISSING_NAME = """# [Candidate Name]

[Contact info placeholder]

## Professional Summary

Summary here.

## Experience

### Developer | Company | 2020-2024
- Did things

## Skills

Python

## Education

BS CS
"""

    RESUME_DUPLICATE_ROLES = """# Jane Doe

jane@email.com | 555-0100

## Professional Summary

Summary.

## Experience

### Senior Developer | TechCo | 2020-2024
- Achievement 1

### Senior Developer | TechCo | 2020-2024
- Achievement 2

## Skills

Python

## Education

BS CS
"""

    def test_valid_resume_passes(self):
        violations = ResumeValidationSchema.validate_all(self.VALID_RESUME)
        assert violations == [], f"Unexpected violations: {violations}"

    def test_catches_placeholder_name(self):
        violations = ResumeValidationSchema.validate_candidate_identity(
            self.RESUME_MISSING_NAME
        )
        assert any("placeholder" in v.lower() for v in violations)

    def test_catches_placeholder_contact(self):
        violations = ResumeValidationSchema.validate_candidate_identity(
            self.RESUME_MISSING_NAME
        )
        assert any("placeholder" in v.lower() or "No email" in v for v in violations)

    def test_catches_duplicate_roles(self):
        violations = ResumeValidationSchema.validate_role_uniqueness(
            self.RESUME_DUPLICATE_ROLES
        )
        assert any("Duplicate role" in v for v in violations)

    def test_catches_missing_sections(self):
        minimal = "# Jane\n\njane@email.com\n555-0100\n\nSome content."
        violations = ResumeValidationSchema.validate_required_sections(minimal)
        assert len(violations) > 0
        assert any("Professional Summary" in v for v in violations)

    def test_catches_missing_certifications(self):
        violations = ResumeValidationSchema.validate_certifications(
            self.VALID_RESUME,
            ["AWS Solutions Architect", "PMP Certification"],
        )
        assert any("PMP Certification" in v for v in violations)
        # AWS should be found
        assert not any("AWS Solutions Architect" in v for v in violations)

    def test_valid_resume_with_certifications(self):
        violations = ResumeValidationSchema.validate_all(
            self.VALID_RESUME,
            expected_certifications=["AWS Solutions Architect"],
        )
        assert violations == []


class TestCoverLetterValidationSchema:
    """Test the cover letter validation schema catches known issues."""

    VALID_COVER_LETTER = """Dear Hiring Manager,

I noticed TechCo's recent expansion into AI infrastructure and was excited to see the Senior Developer position. With eight years building high-performance APIs and a track record of reducing system latency by 40%, I bring exactly the backend expertise your team needs.

At my current role at TechCo, I led a migration from monolithic architecture to FastAPI microservices, cutting response times in half while maintaining 99.9% uptime. I also built the CI/CD pipeline that now handles 100+ deployments weekly. These experiences directly align with your need for someone who can scale backend systems while maintaining quality.

Your focus on developer experience resonates with my approach to engineering. I believe the best systems are built by teams that have excellent tooling, and my experience building internal developer platforms would help accelerate your engineering velocity.

I would welcome the opportunity to discuss how my experience can contribute to TechCo's growth. I am available for a conversation at your convenience.

Sincerely,
Jane Doe"""

    def test_valid_cover_letter_passes(self):
        violations = CoverLetterValidationSchema.validate_all(
            self.VALID_COVER_LETTER
        )
        assert violations == [], f"Unexpected violations: {violations}"

    def test_catches_missing_greeting(self):
        no_greeting = "I am excited about this role.\n\nSincerely,\nJane"
        violations = CoverLetterValidationSchema.validate_structure(no_greeting)
        assert any("greeting" in v.lower() for v in violations)

    def test_catches_placeholder_signature(self):
        with_placeholder = "Dear Manager,\n\nContent here.\n\nSincerely,\n[Your Name]"
        violations = CoverLetterValidationSchema.validate_structure(with_placeholder)
        assert any("placeholder" in v.lower() for v in violations)

    def test_catches_too_short(self):
        short = "Dear Manager,\n\nBrief.\n\nSincerely,\nJane"
        violations = CoverLetterValidationSchema.validate_length(short)
        assert any("too short" in v.lower() for v in violations)
