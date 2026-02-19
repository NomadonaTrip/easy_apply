"""Enrichment service for discovering new skills/accomplishments from approved documents."""

import json
import logging
from datetime import datetime, timezone

from sqlmodel import select, func

from app.database import async_session_maker
from app.llm import get_llm_provider, Message, Role as LLMRole
from app.llm.prompts import PromptRegistry
from app.llm.types import GenerationConfig
from app.models.enrichment import EnrichmentCandidate
from app.models.experience import SkillCreate, AccomplishmentCreate
from app.services import application_service, experience_service
from app.utils.llm_helpers import generate_with_retry, extract_json_from_response

logger = logging.getLogger(__name__)


async def analyze_document_for_enrichment(
    application_id: int,
    role_id: int,
    document_type: str,
) -> dict:
    """Analyze an approved document for new skills/accomplishments.

    Called as BackgroundTask after document approval.
    Graceful degradation: LLM failure logged but does NOT affect approval.

    Args:
        application_id: The application ID
        role_id: The role ID (for data isolation)
        document_type: "resume" or "cover_letter"

    Returns:
        dict with candidates_found count and reason
    """
    if role_id is None:
        raise ValueError("role_id is required - data isolation violation")

    if document_type not in ("resume", "cover_letter"):
        raise ValueError("document_type must be 'resume' or 'cover_letter'")

    # 1. Load application document content
    application = await application_service.get_application(application_id, role_id)
    if not application:
        logger.warning("Application %d not found for role %d", application_id, role_id)
        return {"candidates_found": 0, "reason": "application_not_found"}

    content = (
        application.resume_content
        if document_type == "resume"
        else application.cover_letter_content
    )

    if not content:
        return {"candidates_found": 0, "reason": "no_content"}

    # 2. Idempotency: skip if already analyzed for this app+doc_type
    existing = await get_candidates_by_application(application_id, role_id)
    if any(c.document_type == document_type for c in existing):
        return {"candidates_found": 0, "reason": "already_analyzed"}

    # 3. Load existing experience for dedup context
    existing_skills = await experience_service.get_skills(role_id)
    existing_accomplishments = await experience_service.get_accomplishments(role_id)

    skills_list = ", ".join(s.name for s in existing_skills) or "None"
    accomplishments_list = (
        "; ".join(a.description for a in existing_accomplishments) or "None"
    )

    # 4. Call LLM with enrichment prompt
    try:
        provider = get_llm_provider()
        prompt = PromptRegistry.get(
            "enrichment_analysis",
            document_content=content,
            existing_skills=skills_list,
            existing_accomplishments=accomplishments_list,
        )
        messages = [Message(role=LLMRole.USER, content=prompt)]
        config = GenerationConfig(prompt_name="enrichment_analysis")
        response = await generate_with_retry(provider, messages, config)

        json_str = extract_json_from_response(response.content)
        if not json_str:
            logger.warning("Empty LLM response for enrichment analysis")
            return {"candidates_found": 0, "reason": "empty_response"}

        parsed = json.loads(json_str)
    except Exception as e:
        logger.error(
            "Enrichment analysis failed for app=%d doc=%s: %s",
            application_id,
            document_type,
            e,
        )
        return {"candidates_found": 0, "reason": "llm_error", "error": str(e)}

    # 5. Create candidates with service-layer dedup
    new_skills = parsed.get("new_skills", [])
    new_accomplishments = parsed.get("new_accomplishments", [])

    existing_skill_names = {s.name.strip().lower() for s in existing_skills}
    existing_acc_descs = {a.description.strip().lower() for a in existing_accomplishments}

    candidates_created = 0

    async with async_session_maker() as session:
        for skill in new_skills:
            name = skill.get("name", "").strip()
            if not name:
                continue
            if name.lower() in existing_skill_names:
                continue  # Service-layer dedup safety net

            candidate = EnrichmentCandidate(
                role_id=role_id,
                application_id=application_id,
                document_type=document_type,
                candidate_type="skill",
                name=name,
                category=skill.get("category"),
            )
            session.add(candidate)
            candidates_created += 1

        for acc in new_accomplishments:
            desc = acc.get("description", "").strip()
            if not desc:
                continue
            if desc.lower() in existing_acc_descs:
                continue  # Service-layer dedup safety net

            candidate = EnrichmentCandidate(
                role_id=role_id,
                application_id=application_id,
                document_type=document_type,
                candidate_type="accomplishment",
                name=desc,
                context=acc.get("context"),
            )
            session.add(candidate)
            candidates_created += 1

        await session.commit()

    logger.info(
        "Enrichment analysis for app=%d doc=%s: %d candidates created",
        application_id,
        document_type,
        candidates_created,
    )

    return {"candidates_found": candidates_created}


async def get_pending_candidates(role_id: int) -> list[EnrichmentCandidate]:
    """Fetch all pending enrichment candidates for a role."""
    if role_id is None:
        raise ValueError("role_id is required - data isolation violation")

    async with async_session_maker() as session:
        result = await session.execute(
            select(EnrichmentCandidate).where(
                EnrichmentCandidate.role_id == role_id,
                EnrichmentCandidate.status == "pending",
            )
        )
        candidates = result.scalars().all()
        for c in candidates:
            session.expunge(c)
        return list(candidates)


async def get_pending_count(role_id: int) -> int:
    """Count pending enrichment candidates for a role (efficient COUNT query)."""
    if role_id is None:
        raise ValueError("role_id is required - data isolation violation")

    async with async_session_maker() as session:
        result = await session.execute(
            select(func.count())
            .select_from(EnrichmentCandidate)
            .where(
                EnrichmentCandidate.role_id == role_id,
                EnrichmentCandidate.status == "pending",
            )
        )
        return result.scalar_one()


async def get_candidates_by_application(
    application_id: int, role_id: int
) -> list[EnrichmentCandidate]:
    """Fetch all candidates for a specific application."""
    if role_id is None:
        raise ValueError("role_id is required - data isolation violation")

    async with async_session_maker() as session:
        result = await session.execute(
            select(EnrichmentCandidate).where(
                EnrichmentCandidate.application_id == application_id,
                EnrichmentCandidate.role_id == role_id,
            )
        )
        candidates = result.scalars().all()
        for c in candidates:
            session.expunge(c)
        return list(candidates)


async def accept_candidate(candidate_id: int, role_id: int) -> bool:
    """Accept an enrichment candidate: add to experience DB, update status.

    Transaction ordering:
      1. Read candidate + extract values (session A, then closed)
      2. Create experience entry via experience_service (session B)
      3. Mark candidate accepted (session C)

    If step 2 fails, candidate stays pending (safe retry).
    If step 3 fails after step 2, dedup prevents duplicates on retry.

    Returns True if accepted, False if not found or already resolved.
    """
    if role_id is None:
        raise ValueError("role_id is required - data isolation violation")

    # Step 1: Read and validate candidate
    async with async_session_maker() as session:
        result = await session.execute(
            select(EnrichmentCandidate).where(
                EnrichmentCandidate.id == candidate_id,
                EnrichmentCandidate.role_id == role_id,
            )
        )
        candidate = result.scalar_one_or_none()
        if not candidate or candidate.status != "pending":
            return False
        # Capture values before session closes
        c_type = candidate.candidate_type
        c_name = candidate.name
        c_category = candidate.category
        c_context = candidate.context

    # Step 2: Create experience entry (separate session via experience_service).
    # If this fails, candidate stays pending — safe for user to retry.
    try:
        if c_type == "skill":
            existing_skills = await experience_service.get_skills(role_id)
            if not any(s.name.strip().lower() == c_name.strip().lower() for s in existing_skills):
                await experience_service.create_skill(
                    role_id=role_id,
                    data=SkillCreate(
                        name=c_name,
                        category=c_category,
                        source="application-enriched",
                    ),
                )
        elif c_type == "accomplishment":
            existing_accs = await experience_service.get_accomplishments(role_id)
            if not any(a.description.strip().lower() == c_name.strip().lower() for a in existing_accs):
                await experience_service.create_accomplishment(
                    role_id=role_id,
                    data=AccomplishmentCreate(
                        description=c_name,
                        context=c_context,
                        source="application-enriched",
                    ),
                )
    except Exception:
        logger.exception(
            "Experience creation failed for candidate %d; stays pending for retry",
            candidate_id,
        )
        return False

    # Step 3: Mark candidate accepted (fresh session).
    # If this fails after step 2, dedup prevents duplicates on retry.
    async with async_session_maker() as session:
        result = await session.execute(
            select(EnrichmentCandidate).where(
                EnrichmentCandidate.id == candidate_id,
                EnrichmentCandidate.role_id == role_id,
            )
        )
        candidate = result.scalar_one_or_none()
        if not candidate or candidate.status != "pending":
            return False
        candidate.status = "accepted"
        candidate.resolved_at = datetime.now(timezone.utc)
        session.add(candidate)
        await session.commit()
        return True


async def dismiss_candidate(candidate_id: int, role_id: int) -> bool:
    """Dismiss an enrichment candidate.

    Returns True if dismissed, False if not found.
    """
    if role_id is None:
        raise ValueError("role_id is required - data isolation violation")

    async with async_session_maker() as session:
        result = await session.execute(
            select(EnrichmentCandidate).where(
                EnrichmentCandidate.id == candidate_id,
                EnrichmentCandidate.role_id == role_id,
            )
        )
        candidate = result.scalar_one_or_none()
        if not candidate or candidate.status != "pending":
            return False

        candidate.status = "dismissed"
        candidate.resolved_at = datetime.now(timezone.utc)
        session.add(candidate)
        await session.commit()
        return True


async def bulk_resolve(
    candidate_ids: list[int], role_id: int, action: str
) -> dict:
    """Bulk accept or dismiss enrichment candidates.

    Args:
        candidate_ids: List of candidate IDs to resolve
        role_id: Role ID for data isolation
        action: "accept" or "dismiss"

    Returns:
        dict with resolved count and skipped count
    """
    if role_id is None:
        raise ValueError("role_id is required - data isolation violation")
    if action not in ("accept", "dismiss"):
        raise ValueError("action must be 'accept' or 'dismiss'")

    resolved = 0
    skipped = 0

    if action == "dismiss":
        # Batch dismiss in a single session for efficiency
        async with async_session_maker() as session:
            now = datetime.now(timezone.utc)
            for cid in candidate_ids:
                result = await session.execute(
                    select(EnrichmentCandidate).where(
                        EnrichmentCandidate.id == cid,
                        EnrichmentCandidate.role_id == role_id,
                    )
                )
                candidate = result.scalar_one_or_none()
                if candidate and candidate.status == "pending":
                    candidate.status = "dismissed"
                    candidate.resolved_at = now
                    session.add(candidate)
                    resolved += 1
                else:
                    skipped += 1
            await session.commit()
    else:
        # Accept requires individual calls (each creates experience DB entries)
        for cid in candidate_ids:
            success = await accept_candidate(cid, role_id)
            if success:
                resolved += 1
            else:
                skipped += 1

    return {"resolved": resolved, "skipped": skipped}
