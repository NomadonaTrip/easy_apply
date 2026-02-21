"""Generation service for resume and cover letter creation."""

import json
import logging
from collections import defaultdict
from typing import Optional

from app.llm import get_llm_provider, get_llm_provider_for_generation, Message
from app.llm.prompts import PromptRegistry
from app.llm.skills.loader import SkillLoader
from app.llm.types import GenerationConfig, Role
from app.models.application import Application, ApplicationUpdate, GenerationStatus
from app.models.research import ResearchResult
from app.services import application_service, experience_service, resume_service
from app.services.extraction_service import enrich_skills_from_keywords
from app.utils.document_parser import extract_text
from app.utils.llm_helpers import build_research_context, generate_with_retry
from app.utils.text_processing import check_keyword_coverage, enforce_output_constraints, keyword_found

logger = logging.getLogger(__name__)

# Skill categories that represent certifications/qualifications
_CERTIFICATION_CATEGORIES = {"certification", "certifications", "qualification", "qualifications"}

# Priority tier boundaries
_MUST_HAVE_MIN = 8
_IMPORTANT_MIN = 5


def _parse_keywords_raw(application: Application) -> list[dict]:
    """Parse keywords_raw from application JSON field.

    Shared by enrichment (pre-context) and build_generation_context.
    """
    keywords_list = json.loads(application.keywords) if application.keywords else []
    keywords_raw: list[dict] = []
    if isinstance(keywords_list, list) and keywords_list:
        for kw in keywords_list:
            if isinstance(kw, dict):
                keywords_raw.append(kw)
            else:
                keywords_raw.append({"text": str(kw), "priority": 5, "category": "general", "pattern_boosted": False})
    return keywords_raw


def _format_keywords_tiered(keywords_raw: list[dict]) -> str:
    """Format keywords into priority-tiered sections for the prompt.

    Groups keywords into MUST-HAVE (8-10), IMPORTANT (5-7), NICE-TO-HAVE (1-4)
    with category and pattern_boosted metadata visible to the LLM.
    """
    must_have = []
    important = []
    nice_to_have = []

    for kw in keywords_raw:
        priority = kw.get("priority", 5)
        if priority >= _MUST_HAVE_MIN:
            must_have.append(kw)
        elif priority >= _IMPORTANT_MIN:
            important.append(kw)
        else:
            nice_to_have.append(kw)

    # Sort each tier by descending priority
    must_have.sort(key=lambda k: k.get("priority", 0), reverse=True)
    important.sort(key=lambda k: k.get("priority", 0), reverse=True)
    nice_to_have.sort(key=lambda k: k.get("priority", 0), reverse=True)

    lines: list[str] = []
    counter = 1

    if must_have:
        lines.append("## MUST-HAVE Keywords (Priority 8-10) - These MUST appear in the output:")
        for kw in must_have:
            boosted = " *" if kw.get("pattern_boosted") else ""
            lines.append(f"  {counter}. {kw['text']} [{kw.get('category', 'general')}, priority: {kw.get('priority', 5)}]{boosted}")
            counter += 1
        lines.append("")

    if important:
        lines.append("## IMPORTANT Keywords (Priority 5-7) - Include where naturally fitting:")
        for kw in important:
            boosted = " *" if kw.get("pattern_boosted") else ""
            lines.append(f"  {counter}. {kw['text']} [{kw.get('category', 'general')}, priority: {kw.get('priority', 5)}]{boosted}")
            counter += 1
        lines.append("")

    if nice_to_have:
        lines.append("## NICE-TO-HAVE Keywords (Priority 1-4) - Include if space allows:")
        for kw in nice_to_have:
            boosted = " *" if kw.get("pattern_boosted") else ""
            lines.append(f"  {counter}. {kw['text']} [{kw.get('category', 'general')}, priority: {kw.get('priority', 5)}]{boosted}")
            counter += 1
        lines.append("")

    if any(kw.get("pattern_boosted") for kw in keywords_raw):
        lines.append("* = pattern-boosted (historically successful for this role type)")

    return "\n".join(lines) if lines else "No keywords specified"


def _annotate_accomplishments(accomplishments_text: str, keywords_raw: list[dict]) -> str:
    """Annotate accomplishment group headings with relevant high-priority keywords.

    Scans the bullet points under each ### heading for mentions of priority 7+
    keywords and appends a [Relevant to: ...] tag to the heading.
    """
    high_priority_kws = [
        kw["text"] for kw in keywords_raw
        if kw.get("priority", 0) >= 7
    ]
    if not high_priority_kws:
        return accomplishments_text

    lines = accomplishments_text.split("\n")
    result: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        if line.startswith("### "):
            # Collect all bullet lines under this heading
            heading = line
            bullets: list[str] = []
            j = i + 1
            while j < len(lines) and not lines[j].startswith("### "):
                bullets.append(lines[j])
                j += 1

            # Check which high-priority keywords appear in the bullets
            bullets_lower = " ".join(bullets).lower()
            matched = [kw for kw in high_priority_kws if keyword_found(kw, bullets_lower)]

            if matched:
                heading = f"{heading} [Relevant to: {', '.join(matched)}]"

            result.append(heading)
            result.extend(bullets)
            i = j
        else:
            result.append(line)
            i += 1

    return "\n".join(result)


async def _get_candidate_header(role_id: int) -> str:
    """Extract candidate identity header from the most recent processed resume.

    Returns the first ~500 characters of resume text which typically
    contains the candidate's name, contact info, and summary.
    """
    try:
        resumes = await resume_service.get_resumes(role_id)
        processed = [r for r in resumes if r.processed]
        if not processed:
            return ""
        # Use the most recently uploaded processed resume
        latest = max(processed, key=lambda r: r.uploaded_at)
        text = extract_text(latest.file_path, latest.file_type)
        # Return header section (name + contact typically in first ~500 chars)
        return text[:500].strip() if text else ""
    except (FileNotFoundError, ValueError, OSError, IndexError) as e:
        logger.warning("Failed to extract candidate header: %s", e)
        return ""


async def build_generation_context(
    application: Application,
    role_id: int,
) -> dict:
    """Build context dict for generation prompts from experience DB and application data.

    Returns dict with keys matching prompt template placeholders:
    skills, certifications, accomplishments, candidate_header,
    company_name, job_posting, research_context,
    gap_note, manual_context, keywords.
    """
    # Get experience data
    skills = await experience_service.get_skills(role_id)
    accomplishments = await experience_service.get_accomplishments(role_id)

    if not skills:
        logger.warning("No skills found for role %d — skills section will be empty", role_id)
    if not accomplishments:
        logger.warning("No accomplishments found for role %d — experience section will be empty", role_id)

    # Separate certifications from skills
    cert_skills = []
    regular_skills = []
    for s in skills:
        if s.category and s.category.lower() in _CERTIFICATION_CATEGORIES:
            cert_skills.append(s)
        else:
            regular_skills.append(s)

    # Format skills (excluding certifications)
    skills_text = "\n".join(
        f"- {s.name}" + (f" ({s.category})" if s.category else "")
        for s in regular_skills
    ) or "No skills data available"

    # Format certifications
    certifications_text = "\n".join(
        f"- {s.name}" for s in cert_skills
    ) or "None listed"

    # Format accomplishments grouped by company+dates (or fall back to context)
    company_groups: dict[str, dict] = {}
    for a in accomplishments:
        if a.company_name:
            key = f"{a.company_name}|{a.dates or ''}"
        else:
            key = a.context or "Other"

        if key not in company_groups:
            company_groups[key] = {
                "titles": set(),
                "descs": [],
                "company": a.company_name,
                "dates": a.dates,
            }

        if a.role_title:
            company_groups[key]["titles"].add(a.role_title)
        company_groups[key]["descs"].append(a.description)

    if company_groups:
        parts = []
        for key, group in company_groups.items():
            if group["company"] and group["titles"]:
                titles_str = " / ".join(sorted(group["titles"]))
                dates_str = f" | {group['dates']}" if group["dates"] else ""
                heading = f"{titles_str} | {group['company']}{dates_str}"
            else:
                heading = key  # legacy fallback: use context string
            parts.append(f"### {heading}")
            for desc in group["descs"]:
                parts.append(f"- {desc}")
            parts.append("")  # blank line between groups
        accomplishments_text = "\n".join(parts)
    else:
        accomplishments_text = "No accomplishments data available"

    # Get candidate identity from resume header
    candidate_header = await _get_candidate_header(role_id)

    # Parse keywords from JSON — preserve full metadata for coverage check
    keywords_raw = _parse_keywords_raw(application)
    keywords_text = _format_keywords_tiered(keywords_raw) if keywords_raw else "No keywords specified"

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
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Failed to parse research data: %s", e)

    # Annotate accomplishment headings with keyword relevance
    if keywords_raw:
        accomplishments_text = _annotate_accomplishments(accomplishments_text, keywords_raw)

    # Manual context
    manual_context = application.manual_context or "No additional context provided."

    logger.info(
        "Generation context built for role %d: %d skills, %d certs, %d accomplishments, "
        "%d keywords, candidate_header=%d chars",
        role_id, len(regular_skills), len(cert_skills), len(accomplishments),
        len(keywords_raw), len(candidate_header),
    )

    return {
        "skills": skills_text,
        "certifications": certifications_text,
        "accomplishments": accomplishments_text,
        "candidate_header": candidate_header,
        "company_name": application.company_name,
        "job_posting": application.job_posting,
        "research_context": research_context,
        "gap_note": gap_note,
        "gap_categories": gap_categories,
        "manual_context": manual_context,
        "keywords": keywords_text,
        "keywords_raw": keywords_raw,
    }


async def generate_resume(
    application_id: int,
    role_id: int,
) -> str:
    """Generate a tailored resume for an application.

    Updates generation_status throughout the process.
    Uses PromptRegistry for prompts and generate_with_retry for resilience.
    """
    application = await application_service.get_application(application_id, role_id)
    if not application:
        raise ValueError(f"Application {application_id} not found for role {role_id}")

    # Update generation_status to generating_resume
    await _update_generation_status(application_id, role_id, GenerationStatus.GENERATING_RESUME)

    context = None
    try:
        # Enrich skills library BEFORE building context so enriched skills
        # appear in the current generation's prompt
        try:
            keywords_raw = _parse_keywords_raw(application)
            if keywords_raw:
                skills = await experience_service.get_skills(role_id)
                accomplishments = await experience_service.get_accomplishments(role_id)
                added = await enrich_skills_from_keywords(
                    role_id, keywords_raw, accomplishments, skills
                )
                if added:
                    logger.info("Enriched skills library with %d keyword(s) for role %d", added, role_id)
        except Exception:
            pass  # enrichment is best-effort, never blocks generation

        # Build context (now includes any enriched skills)
        context = await build_generation_context(application, role_id)

        # Get prompts from registry
        prompt = PromptRegistry.get("generation_resume", **context)
        system_prompt = PromptRegistry.get("generation_resume_system")

        # Get LLM provider (uses LLM_MODEL_GEN override if set)
        provider = get_llm_provider_for_generation()

        # Load resume-tailoring skill if available
        if SkillLoader.skill_exists("resume_tailoring"):
            skill_content = SkillLoader.load("resume_tailoring")
            provider.set_system_instruction(skill_content)

        # Generate with retry
        config = GenerationConfig(prompt_name="generation_resume")
        messages = [
            Message(role=Role.SYSTEM, content=system_prompt),
            Message(role=Role.USER, content=prompt),
        ]
        response = await generate_with_retry(provider, messages, config)
        resume_content = enforce_output_constraints(response.content)

        # Keyword coverage observability (fire-and-forget, never blocks)
        try:
            check_keyword_coverage(resume_content, context.get("keywords_raw", []))
        except Exception:
            pass  # observability must never break generation

        # Save content and update status
        await _save_generation_result(
            application_id, role_id,
            resume_content=resume_content,
            generation_status=GenerationStatus.COMPLETE,
        )

        # Log gap impact after successful generation (AC #10)
        if context["gap_note"]:
            _log_gap_impact("generation_resume", context["gap_categories"], context["gap_note"], outcome="success")

        logger.info(
            "Resume generated for application %d (role %d), %d chars",
            application_id, role_id, len(resume_content),
        )

        return resume_content

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
) -> str:
    """Generate a tailored cover letter for an application.

    Args:
        application_id: Application to generate for
        role_id: Role for data isolation
        tone: One of 'formal', 'conversational', 'match_culture'
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
        # Enrich skills library BEFORE building context so enriched skills
        # appear in the current generation's prompt
        try:
            keywords_raw = _parse_keywords_raw(application)
            if keywords_raw:
                skills = await experience_service.get_skills(role_id)
                accomplishments = await experience_service.get_accomplishments(role_id)
                added = await enrich_skills_from_keywords(
                    role_id, keywords_raw, accomplishments, skills
                )
                if added:
                    logger.info("Enriched skills library with %d keyword(s) for role %d", added, role_id)
        except Exception:
            pass  # enrichment is best-effort, never blocks generation

        # Build context (now includes any enriched skills)
        context = await build_generation_context(application, role_id)
        context["tone"] = tone

        # Get prompts
        prompt = PromptRegistry.get("generation_cover_letter", **context)
        system_prompt = PromptRegistry.get("generation_cover_letter_system")

        # Generate (uses LLM_MODEL_GEN override if set)
        provider = get_llm_provider_for_generation()

        # Load cover-letter-writing skill if available
        if SkillLoader.skill_exists("cover_letter_writing"):
            skill_content = SkillLoader.load("cover_letter_writing")
            provider.set_system_instruction(skill_content)

        config = GenerationConfig(prompt_name="generation_cover_letter")
        messages = [
            Message(role=Role.SYSTEM, content=system_prompt),
            Message(role=Role.USER, content=prompt),
        ]
        response = await generate_with_retry(provider, messages, config)
        cover_letter_content = enforce_output_constraints(response.content)

        # Keyword coverage observability (fire-and-forget, never blocks)
        try:
            check_keyword_coverage(cover_letter_content, context.get("keywords_raw", []))
        except Exception:
            pass  # observability must never break generation

        # Save
        await _save_generation_result(
            application_id, role_id,
            cover_letter_content=cover_letter_content,
            cover_letter_tone=tone,
            generation_status=GenerationStatus.COMPLETE,
        )

        # Log gap impact after successful generation (AC #10)
        if context["gap_note"]:
            _log_gap_impact("generation_cover_letter", context["gap_categories"], context["gap_note"], outcome="success")

        logger.info(
            "Cover letter generated for application %d (role %d), tone=%s, %d chars",
            application_id, role_id, tone, len(cover_letter_content),
        )

        return cover_letter_content

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
) -> None:
    """Save generation result to application record."""
    update = ApplicationUpdate(generation_status=generation_status)
    if resume_content is not None:
        update.resume_content = resume_content
    if cover_letter_content is not None:
        update.cover_letter_content = cover_letter_content
    if cover_letter_tone is not None:
        update.cover_letter_tone = cover_letter_tone

    await application_service.update_application(application_id, role_id, update)
