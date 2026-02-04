"""Extraction service for skills and accomplishments from resumes."""

import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

from app.services import resume_service, experience_service
from app.utils.document_parser import extract_text
from app.llm.prompts.extraction import (
    SKILL_EXTRACTION_PROMPT,
    ACCOMPLISHMENT_EXTRACTION_PROMPT,
)
from app.llm import get_llm_provider, Message, Role
from app.models.experience import SkillCreate, AccomplishmentCreate


def _extract_json_from_response(content: str) -> str:
    """
    Extract JSON from LLM response, handling markdown code blocks.

    Args:
        content: Raw LLM response content

    Returns:
        Cleaned JSON string
    """
    if not content:
        return ""

    # Try to extract JSON from markdown code blocks
    # Match ```json ... ``` or ``` ... ```
    code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    match = re.search(code_block_pattern, content)
    if match:
        return match.group(1).strip()

    # If no code block, return content stripped
    return content.strip()


async def extract_skills_with_llm(resume_text: str) -> list[dict]:
    """
    Use LLM Provider to extract skills from resume text.

    Args:
        resume_text: The text content of the resume

    Returns:
        List of {"name": str, "category": str} dicts.
    """
    prompt = SKILL_EXTRACTION_PROMPT.format(resume_text=resume_text)
    provider = get_llm_provider()

    messages = [Message(role=Role.USER, content=prompt)]
    response = await provider.generate(messages)

    # Log raw response for debugging
    logger.info(f"Skills extraction raw response length: {len(response.content) if response.content else 0}")

    # Parse JSON from response (handle markdown code blocks)
    try:
        json_str = _extract_json_from_response(response.content)
        if not json_str:
            logger.warning(f"Empty response from LLM for skills extraction. Raw: {response.content[:200] if response.content else 'None'}")
            return []
        parsed = json.loads(json_str)
        skills = parsed.get("skills", [])
        logger.info(f"Extracted {len(skills)} skills from resume")
        return skills
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Failed to parse skills from LLM response: {e}")
        logger.warning(f"Raw response content: {response.content[:500] if response.content else 'None'}")
        return []


async def extract_accomplishments_with_llm(resume_text: str) -> list[dict]:
    """
    Use LLM Provider to extract accomplishments from resume text.

    Args:
        resume_text: The text content of the resume

    Returns:
        List of {"description": str, "context": str} dicts.
    """
    prompt = ACCOMPLISHMENT_EXTRACTION_PROMPT.format(resume_text=resume_text)
    provider = get_llm_provider()

    messages = [Message(role=Role.USER, content=prompt)]
    response = await provider.generate(messages)

    # Log raw response for debugging
    logger.info(f"Accomplishments extraction raw response length: {len(response.content) if response.content else 0}")

    # Parse JSON from response (handle markdown code blocks)
    try:
        json_str = _extract_json_from_response(response.content)
        if not json_str:
            logger.warning(f"Empty response from LLM for accomplishments extraction. Raw: {response.content[:200] if response.content else 'None'}")
            return []
        parsed = json.loads(json_str)
        accomplishments = parsed.get("accomplishments", [])
        logger.info(f"Extracted {len(accomplishments)} accomplishments from resume")
        return accomplishments
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Failed to parse accomplishments from LLM response: {e}")
        logger.warning(f"Raw response content: {response.content[:500] if response.content else 'None'}")
        return []


async def add_skill_if_not_exists(
    role_id: int,
    name: str,
    category: Optional[str] = None,
    source: Optional[str] = None
) -> bool:
    """
    Add a skill if it doesn't already exist for this role.

    Deduplication is performed by normalizing skill names to lowercase
    and trimming whitespace.

    Args:
        role_id: The role ID to add the skill to
        name: The skill name
        category: Optional skill category
        source: Optional source (e.g., "resume")

    Returns:
        True if skill was added, False if duplicate.
    """
    # Normalize skill name for comparison
    normalized_name = name.strip().lower()

    # Check for existing skill (service manages its own session)
    existing_skills = await experience_service.get_skills(role_id)
    for skill in existing_skills:
        if skill.name.strip().lower() == normalized_name:
            return False  # Skill already exists

    # Add new skill
    skill_data = SkillCreate(name=name.strip(), category=category, source=source)
    await experience_service.create_skill(role_id, skill_data)
    return True


async def add_accomplishment_if_not_exists(
    role_id: int,
    description: str,
    context: Optional[str] = None,
    source: Optional[str] = None
) -> bool:
    """
    Add an accomplishment if it doesn't already exist for this role.

    Deduplication is performed by normalizing description text to lowercase
    and trimming whitespace (exact match).

    Args:
        role_id: The role ID to add the accomplishment to
        description: The accomplishment description
        context: Optional context (e.g., job title, company)
        source: Optional source (e.g., "resume")

    Returns:
        True if accomplishment was added, False if duplicate.
    """
    # Normalize description for comparison
    normalized_desc = description.strip().lower()

    # Check for existing accomplishment (service manages its own session)
    existing = await experience_service.get_accomplishments(role_id)
    for acc in existing:
        if acc.description.strip().lower() == normalized_desc:
            return False  # Accomplishment already exists

    # Add new accomplishment
    acc_data = AccomplishmentCreate(
        description=description.strip(),
        context=context,
        source=source
    )
    await experience_service.create_accomplishment(role_id, acc_data)
    return True


async def extract_from_resume(resume_id: int, role_id: int) -> dict:
    """
    Extract skills and accomplishments from a single resume.

    Args:
        resume_id: The resume ID to extract from
        role_id: The role ID for ownership verification

    Returns:
        {"skills_count": int, "accomplishments_count": int}

    Raises:
        ValueError: If resume not found
    """
    # Get resume (service manages its own session)
    resume = await resume_service.get_resume(resume_id, role_id)
    if not resume:
        raise ValueError("Resume not found")

    # Extract text from file
    resume_text = extract_text(resume.file_path, resume.file_type)

    # Extract skills via LLM Provider
    extracted_skills = await extract_skills_with_llm(resume_text)

    # Extract accomplishments via LLM Provider
    extracted_accomplishments = await extract_accomplishments_with_llm(resume_text)

    # Store skills (with deduplication)
    skills_added = 0
    for skill_data in extracted_skills:
        added = await add_skill_if_not_exists(
            role_id,
            name=skill_data["name"],
            category=skill_data.get("category"),
            source="resume"
        )
        if added:
            skills_added += 1

    # Store accomplishments (with deduplication)
    accomplishments_added = 0
    for acc_data in extracted_accomplishments:
        added = await add_accomplishment_if_not_exists(
            role_id,
            description=acc_data["description"],
            context=acc_data.get("context"),
            source="resume"
        )
        if added:
            accomplishments_added += 1

    # Mark resume as processed
    await resume_service.mark_resume_processed(resume_id, role_id)

    return {
        "skills_count": skills_added,
        "accomplishments_count": accomplishments_added
    }


async def extract_all_unprocessed(role_id: int) -> dict:
    """
    Extract from all unprocessed resumes for a role.

    Args:
        role_id: The role ID to process resumes for

    Returns:
        {"resumes_processed": int, "total_skills": int, "total_accomplishments": int}
    """
    resumes = await resume_service.get_resumes(role_id)
    unprocessed = [r for r in resumes if not r.processed]

    total_skills = 0
    total_accomplishments = 0

    for resume in unprocessed:
        result = await extract_from_resume(resume.id, role_id)
        total_skills += result["skills_count"]
        total_accomplishments += result["accomplishments_count"]

    return {
        "resumes_processed": len(unprocessed),
        "total_skills": total_skills,
        "total_accomplishments": total_accomplishments
    }
