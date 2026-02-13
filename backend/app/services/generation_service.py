"""Generation service for resume and cover letter creation."""

import json
import logging
from typing import Optional

from app.llm import get_llm_provider, Message
from app.llm.prompts import PromptRegistry
from app.llm.skills.loader import SkillLoader
from app.llm.types import GenerationConfig, Role
from app.models.application import Application, ApplicationUpdate, GenerationStatus
from app.models.research import ResearchResult
from app.services import application_service, experience_service
from app.utils.llm_helpers import build_research_context, generate_with_retry
from app.utils.constraints import ViolationSeverity
from app.utils.text_processing import enforce_output_constraints_detailed

logger = logging.getLogger(__name__)


async def build_generation_context(
    application: Application,
    role_id: int,
) -> dict:
    """Build context dict for generation prompts from experience DB and application data.

    Returns dict with keys matching prompt template placeholders:
    skills, accomplishments, company_name, job_posting, research_context,
    gap_note, manual_context, keywords.
    """
    # Get experience data
    skills = await experience_service.get_skills(role_id)
    accomplishments = await experience_service.get_accomplishments(role_id)

    # Format skills
    skills_text = "\n".join(
        f"- {s.name}" + (f" ({s.category})" if s.category else "")
        for s in skills
    ) or "No skills data available"

    # Format accomplishments
    accomplishments_text = "\n".join(
        f"- {a.description}" + (f" [{a.context}]" if a.context else "")
        for a in accomplishments
    ) or "No accomplishments data available"

    # Parse keywords from JSON
    keywords_list = json.loads(application.keywords) if application.keywords else []
    if isinstance(keywords_list, list) and keywords_list:
        keywords_text = "\n".join(
            f"{i+1}. {kw['text']}" if isinstance(kw, dict) else f"{i+1}. {kw}"
            for i, kw in enumerate(keywords_list)
        )
    else:
        keywords_text = "No keywords specified"

    # Build research context using build_research_context()
    research_context = "No research data available."
    gap_note = ""
    gap_categories: list[str] = []
    if application.research_data:
        try:
            research_dict = json.loads(application.research_data)
            research = ResearchResult(**research_dict)
            research_context, gap_note_result = build_research_context(research)
            gap_note = gap_note_result or ""
            gap_categories = research.gaps
        except Exception as e:
            logger.warning("Failed to parse research data: %s", e)

    # Manual context
    manual_context = application.manual_context or "No additional context provided."

    return {
        "skills": skills_text,
        "accomplishments": accomplishments_text,
        "company_name": application.company_name,
        "job_posting": application.job_posting,
        "research_context": research_context,
        "gap_note": gap_note,
        "gap_categories": gap_categories,
        "manual_context": manual_context,
        "keywords": keywords_text,
    }


async def generate_resume(
    application_id: int,
    role_id: int,
) -> dict:
    """Generate a tailored resume for an application.

    Updates generation_status throughout the process.
    Uses PromptRegistry for prompts and generate_with_retry for resilience.

    Returns dict with content, violations_fixed, violations_remaining, warnings.
    """
    application = await application_service.get_application(application_id, role_id)
    if not application:
        raise ValueError(f"Application {application_id} not found for role {role_id}")

    # Update generation_status to generating_resume
    await _update_generation_status(application_id, role_id, GenerationStatus.GENERATING_RESUME)

    context = None
    try:
        # Build context
        context = await build_generation_context(application, role_id)

        # Get prompts from registry
        prompt = PromptRegistry.get("generation_resume", **context)
        system_prompt = PromptRegistry.get("generation_resume_system")

        # Get LLM provider
        provider = get_llm_provider()

        # Load resume-tailoring skill if available
        if SkillLoader.skill_exists("resume_tailoring"):
            skill_content = SkillLoader.load("resume_tailoring")
            provider.set_system_instruction(skill_content)

        # Generate with retry
        config = GenerationConfig(prompt_name="generation_resume", max_tokens=8192)
        messages = [
            Message(role=Role.SYSTEM, content=system_prompt),
            Message(role=Role.USER, content=prompt),
        ]
        response = await generate_with_retry(provider, messages, config)
        if response.finish_reason == "MAX_TOKENS":
            logger.warning(
                "Resume generation truncated for application %d (hit max_tokens)",
                application_id,
            )

        # Enforce constraints with detailed reporting
        constraint_result = enforce_output_constraints_detailed(response.content)
        resume_content = constraint_result.cleaned_text

        if constraint_result.violations_remaining > 0:
            logger.warning(
                "Resume for application %d has %d constraint violations after processing",
                application_id, constraint_result.violations_remaining,
            )

        # Build warnings list
        warnings = [
            v.message for v in constraint_result.violations
            if v.severity == ViolationSeverity.WARNING
        ]

        # Save content and constraint metadata
        await _save_generation_result(
            application_id, role_id,
            resume_content=resume_content,
            generation_status=GenerationStatus.COMPLETE,
            resume_violations_fixed=constraint_result.violations_fixed,
            resume_constraint_warnings=json.dumps(warnings),
        )

        # Log gap impact after successful generation (AC #10)
        if context["gap_note"]:
            _log_gap_impact("generation_resume", context["gap_categories"], context["gap_note"], outcome="success")

        logger.info(
            "Resume generated for application %d (role %d), %d chars, %d violations fixed, %d remaining",
            application_id, role_id, len(resume_content),
            constraint_result.violations_fixed, constraint_result.violations_remaining,
        )

        return {
            "content": resume_content,
            "violations_fixed": constraint_result.violations_fixed,
            "violations_remaining": constraint_result.violations_remaining,
            "warnings": warnings,
        }

    except Exception as e:
        logger.error(
            "Resume generation failed for application %d: %s",
            application_id, e,
        )
        await _update_generation_status(application_id, role_id, GenerationStatus.FAILED)
        if context and context.get("gap_note"):
            _log_gap_impact("generation_resume", context["gap_categories"], context["gap_note"], outcome="failed")
        raise


async def generate_cover_letter(
    application_id: int,
    role_id: int,
    tone: str = "formal",
) -> dict:
    """Generate a tailored cover letter for an application.

    Args:
        application_id: Application to generate for
        role_id: Role for data isolation
        tone: One of 'formal', 'conversational', 'match_culture'

    Returns dict with content, violations_fixed, violations_remaining, warnings.
    """
    valid_tones = ["formal", "conversational", "match_culture"]
    if tone not in valid_tones:
        tone = "formal"

    application = await application_service.get_application(application_id, role_id)
    if not application:
        raise ValueError(f"Application {application_id} not found for role {role_id}")

    # Update generation_status
    await _update_generation_status(application_id, role_id, GenerationStatus.GENERATING_COVER_LETTER)

    context = None
    try:
        # Build context
        context = await build_generation_context(application, role_id)
        context["tone"] = tone

        # Get prompts
        prompt = PromptRegistry.get("generation_cover_letter", **context)
        system_prompt = PromptRegistry.get("generation_cover_letter_system")

        # Generate
        provider = get_llm_provider()
        config = GenerationConfig(prompt_name="generation_cover_letter", max_tokens=8192)
        messages = [
            Message(role=Role.SYSTEM, content=system_prompt),
            Message(role=Role.USER, content=prompt),
        ]
        response = await generate_with_retry(provider, messages, config)
        if response.finish_reason == "MAX_TOKENS":
            logger.warning(
                "Cover letter generation truncated for application %d (hit max_tokens)",
                application_id,
            )

        # Enforce constraints with detailed reporting
        constraint_result = enforce_output_constraints_detailed(response.content)
        cover_letter_content = constraint_result.cleaned_text

        if constraint_result.violations_remaining > 0:
            logger.warning(
                "Cover letter for application %d has %d constraint violations after processing",
                application_id, constraint_result.violations_remaining,
            )

        # Build warnings list
        warnings = [
            v.message for v in constraint_result.violations
            if v.severity == ViolationSeverity.WARNING
        ]

        # Save content and constraint metadata
        await _save_generation_result(
            application_id, role_id,
            cover_letter_content=cover_letter_content,
            cover_letter_tone=tone,
            generation_status=GenerationStatus.COMPLETE,
            cover_letter_violations_fixed=constraint_result.violations_fixed,
            cover_letter_constraint_warnings=json.dumps(warnings),
        )

        # Log gap impact after successful generation (AC #10)
        if context["gap_note"]:
            _log_gap_impact("generation_cover_letter", context["gap_categories"], context["gap_note"], outcome="success")

        logger.info(
            "Cover letter generated for application %d (role %d), tone=%s, %d chars, %d violations fixed, %d remaining",
            application_id, role_id, tone, len(cover_letter_content),
            constraint_result.violations_fixed, constraint_result.violations_remaining,
        )

        return {
            "content": cover_letter_content,
            "violations_fixed": constraint_result.violations_fixed,
            "violations_remaining": constraint_result.violations_remaining,
            "warnings": warnings,
        }

    except Exception as e:
        logger.error(
            "Cover letter generation failed for application %d: %s",
            application_id, e,
        )
        await _update_generation_status(application_id, role_id, GenerationStatus.FAILED)
        if context and context.get("gap_note"):
            _log_gap_impact("generation_cover_letter", context["gap_categories"], context["gap_note"], outcome="failed")
        raise


def _log_gap_impact(
    prompt_name: str,
    gap_categories: list[str],
    gap_note: str,
    outcome: str = "pending",
) -> None:
    """Log structured gap impact on generation quality (AC #10)."""
    logger.info(
        "Generation with research gaps",
        extra={
            "prompt_name": prompt_name,
            "gap_categories": gap_categories,
            "gap_note": gap_note,
            "outcome": outcome,
        },
    )


async def _update_generation_status(
    application_id: int,
    role_id: int,
    status: GenerationStatus,
) -> None:
    """Update only the generation_status field."""
    await application_service.update_application(
        application_id, role_id,
        ApplicationUpdate(generation_status=status),
    )


async def _save_generation_result(
    application_id: int,
    role_id: int,
    resume_content: Optional[str] = None,
    cover_letter_content: Optional[str] = None,
    cover_letter_tone: Optional[str] = None,
    generation_status: GenerationStatus = GenerationStatus.COMPLETE,
    resume_violations_fixed: Optional[int] = None,
    resume_constraint_warnings: Optional[str] = None,
    cover_letter_violations_fixed: Optional[int] = None,
    cover_letter_constraint_warnings: Optional[str] = None,
) -> None:
    """Save generation result and constraint metadata to application record."""
    update = ApplicationUpdate(generation_status=generation_status)
    if resume_content is not None:
        update.resume_content = resume_content
    if cover_letter_content is not None:
        update.cover_letter_content = cover_letter_content
    if cover_letter_tone is not None:
        update.cover_letter_tone = cover_letter_tone
    if resume_violations_fixed is not None:
        update.resume_violations_fixed = resume_violations_fixed
    if resume_constraint_warnings is not None:
        update.resume_constraint_warnings = resume_constraint_warnings
    if cover_letter_violations_fixed is not None:
        update.cover_letter_violations_fixed = cover_letter_violations_fixed
    if cover_letter_constraint_warnings is not None:
        update.cover_letter_constraint_warnings = cover_letter_constraint_warnings

    await application_service.update_application(application_id, role_id, update)
