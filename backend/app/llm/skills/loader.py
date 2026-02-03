"""Skill loader for loading skill files as system instructions."""

from pathlib import Path
from typing import ClassVar


class SkillLoader:
    """
    Loads skill files (e.g., SKILL.md) as system instructions for LLMs.

    Skills are markdown files containing detailed instructions for
    specific tasks like resume tailoring, document generation, etc.
    """

    # Directory containing skill subdirectories
    SKILLS_DIR: ClassVar[Path] = Path(__file__).parent

    @classmethod
    def load(cls, skill_name: str) -> str:
        """
        Load a skill by name.

        Args:
            skill_name: Name of the skill directory (e.g., "resume_tailoring")

        Returns:
            Skill content as string

        Raises:
            ValueError: If skill not found
        """
        skill_path = cls.SKILLS_DIR / skill_name / "SKILL.md"

        if not skill_path.exists():
            # Also try without underscore (backwards compatibility)
            alt_path = cls.SKILLS_DIR / skill_name.replace("_", "-") / "SKILL.md"
            if alt_path.exists():
                skill_path = alt_path
            else:
                raise ValueError(
                    f"Skill not found: {skill_name}. "
                    f"Expected file at {skill_path}"
                )

        return skill_path.read_text(encoding="utf-8")

    @classmethod
    def load_with_context(cls, skill_name: str, context: dict) -> str:
        """
        Load a skill and inject context variables.

        Args:
            skill_name: Name of the skill
            context: Dict of variables to inject (e.g., {"company": "Acme"})

        Returns:
            Skill content with variables replaced
        """
        content = cls.load(skill_name)

        # Simple variable replacement: {variable_name} -> value
        for key, value in context.items():
            content = content.replace(f"{{{key}}}", str(value))

        return content

    @classmethod
    def available_skills(cls) -> list[str]:
        """
        List available skill names.

        Returns:
            List of skill directory names
        """
        skills = []
        for path in cls.SKILLS_DIR.iterdir():
            if path.is_dir() and (path / "SKILL.md").exists():
                skills.append(path.name)
        return sorted(skills)

    @classmethod
    def skill_exists(cls, skill_name: str) -> bool:
        """
        Check if a skill exists.

        Args:
            skill_name: Name of the skill

        Returns:
            True if skill exists
        """
        skill_path = cls.SKILLS_DIR / skill_name / "SKILL.md"
        alt_path = cls.SKILLS_DIR / skill_name.replace("_", "-") / "SKILL.md"
        return skill_path.exists() or alt_path.exists()

    @classmethod
    def get_skill_path(cls, skill_name: str) -> Path:
        """
        Get the path to a skill file.

        Args:
            skill_name: Name of the skill

        Returns:
            Path to the SKILL.md file

        Raises:
            ValueError: If skill not found
        """
        skill_path = cls.SKILLS_DIR / skill_name / "SKILL.md"
        if skill_path.exists():
            return skill_path

        alt_path = cls.SKILLS_DIR / skill_name.replace("_", "-") / "SKILL.md"
        if alt_path.exists():
            return alt_path

        raise ValueError(f"Skill not found: {skill_name}")
