"""Tests for experience enrichment (Story 5.6)."""

import pytest
import pytest_asyncio
from datetime import datetime, timezone

from app.models.experience import SkillCreate, AccomplishmentCreate
from app.models.enrichment import EnrichmentCandidate, EnrichmentCandidateRead
from app.models.role import RoleCreate
from app.models.user import UserCreate
from app.services import auth_service, role_service, experience_service, enrichment_service


# ─── Helper ────────────────────────────────────────────────────────────────

async def _create_role() -> int:
    """Create a user and role, return role_id."""
    user = await auth_service.create_user(
        UserCreate(username="enrichtest", password="password123")
    )
    role = await role_service.create_role(user.id, RoleCreate(name="Dev"))
    return role.id


# ─── Task 0: Integration Smoke Tests ───────────────────────────────────────


class TestSmokeExperienceServiceCRUD:
    """Verify existing experience service CRUD works."""

    @pytest.mark.asyncio
    async def test_get_skills_returns_list(self):
        """GET skills for a role returns a list."""
        from app.services import experience_service

        role_id = await _create_role()
        skills = await experience_service.get_skills(role_id)
        assert isinstance(skills, list)
        assert len(skills) == 0

    @pytest.mark.asyncio
    async def test_create_and_get_skill(self):
        """POST then GET skill round-trips correctly."""
        from app.services import experience_service

        role_id = await _create_role()
        skill_data = SkillCreate(name="Python", category="Language", source="resume")
        created = await experience_service.create_skill(role_id, skill_data)
        assert created.name == "Python"
        assert created.source == "resume"

        skills = await experience_service.get_skills(role_id)
        assert len(skills) == 1
        assert skills[0].name == "Python"

    @pytest.mark.asyncio
    async def test_create_and_get_accomplishment(self):
        """POST then GET accomplishment round-trips correctly."""
        from app.services import experience_service

        role_id = await _create_role()
        acc_data = AccomplishmentCreate(
            description="Led team of 5",
            context="Engineering Manager at Acme",
            source="resume",
        )
        created = await experience_service.create_accomplishment(role_id, acc_data)
        assert created.description == "Led team of 5"
        assert created.source == "resume"

        accs = await experience_service.get_accomplishments(role_id)
        assert len(accs) == 1
        assert accs[0].description == "Led team of 5"


class TestSmokeExtractionDedup:
    """Verify extraction_service.py dedup functions work correctly."""

    @pytest.mark.asyncio
    async def test_add_skill_if_not_exists_adds_new(self):
        from app.services.extraction_service import add_skill_if_not_exists

        role_id = await _create_role()
        result = await add_skill_if_not_exists(role_id, "Docker", "Tool", "resume")
        assert result is True

    @pytest.mark.asyncio
    async def test_add_skill_if_not_exists_deduplicates(self):
        from app.services.extraction_service import add_skill_if_not_exists

        role_id = await _create_role()
        await add_skill_if_not_exists(role_id, "Docker", "Tool", "resume")
        result = await add_skill_if_not_exists(role_id, "docker", "Tool", "resume")
        assert result is False  # Case-insensitive dedup

    @pytest.mark.asyncio
    async def test_add_accomplishment_if_not_exists_adds_new(self):
        from app.services.extraction_service import add_accomplishment_if_not_exists

        role_id = await _create_role()
        result = await add_accomplishment_if_not_exists(
            role_id, "Reduced latency by 50%", "Backend team", "resume"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_add_accomplishment_if_not_exists_deduplicates(self):
        from app.services.extraction_service import add_accomplishment_if_not_exists

        role_id = await _create_role()
        await add_accomplishment_if_not_exists(
            role_id, "Reduced latency by 50%", "Backend team", "resume"
        )
        result = await add_accomplishment_if_not_exists(
            role_id, "reduced latency by 50%", "Backend team", "resume"
        )
        assert result is False  # Case-insensitive dedup


class TestSmokeApplicationFields:
    """Verify application model has required fields for enrichment."""

    def test_application_has_resume_content_field(self):
        from app.models.application import Application

        app = Application(
            role_id=1,
            company_name="Test Co",
            job_posting="A job description for testing purposes.",
            resume_content="My resume content",
        )
        assert app.resume_content == "My resume content"

    def test_application_has_cover_letter_content_field(self):
        from app.models.application import Application

        app = Application(
            role_id=1,
            company_name="Test Co",
            job_posting="A job description for testing purposes.",
            cover_letter_content="My cover letter",
        )
        assert app.cover_letter_content == "My cover letter"

    def test_application_has_resume_approved_field(self):
        from app.models.application import Application

        app = Application(
            role_id=1,
            company_name="Test Co",
            job_posting="A job description for testing purposes.",
            resume_approved=True,
        )
        assert app.resume_approved is True

    def test_application_has_cover_letter_approved_field(self):
        from app.models.application import Application

        app = Application(
            role_id=1,
            company_name="Test Co",
            job_posting="A job description for testing purposes.",
            cover_letter_approved=True,
        )
        assert app.cover_letter_approved is True

    def test_application_approved_defaults_to_false(self):
        from app.models.application import Application

        app = Application(
            role_id=1,
            company_name="Test Co",
            job_posting="A job description for testing purposes.",
        )
        assert app.resume_approved is False
        assert app.cover_letter_approved is False


class TestSmokePromptRegistry:
    """Verify PromptRegistry loads and serves existing extraction prompts."""

    def test_prompt_registry_has_skill_extraction(self):
        from app.llm.prompts import PromptRegistry

        prompts = PromptRegistry.list()
        assert "skill_extraction" in prompts

    def test_prompt_registry_has_accomplishment_extraction(self):
        from app.llm.prompts import PromptRegistry

        prompts = PromptRegistry.list()
        assert "accomplishment_extraction" in prompts

    def test_prompt_registry_get_skill_extraction(self):
        from app.llm.prompts import PromptRegistry

        prompt = PromptRegistry.get(
            "skill_extraction", resume_text="Sample resume text"
        )
        assert "Sample resume text" in prompt
        assert len(prompt) > 50

    def test_prompt_registry_get_accomplishment_extraction(self):
        from app.llm.prompts import PromptRegistry

        prompt = PromptRegistry.get(
            "accomplishment_extraction", resume_text="Sample resume text"
        )
        assert "Sample resume text" in prompt
        assert len(prompt) > 50


# ─── Task 2: Enrichment Prompt Tests ──────────────────────────────────────


class TestEnrichmentPrompt:
    """Verify enrichment analysis prompt is registered and works."""

    def test_enrichment_prompt_registered(self):
        from app.llm.prompts import PromptRegistry

        prompts = PromptRegistry.list()
        assert "enrichment_analysis" in prompts

    def test_enrichment_prompt_accepts_variables(self):
        from app.llm.prompts import PromptRegistry

        prompt = PromptRegistry.get(
            "enrichment_analysis",
            document_content="Resume with Python and Docker skills",
            existing_skills="Python, JavaScript",
            existing_accomplishments="Led team of 5",
        )
        assert "Resume with Python and Docker skills" in prompt
        assert "Python, JavaScript" in prompt
        assert "Led team of 5" in prompt

    def test_enrichment_prompt_requests_json_output(self):
        from app.llm.prompts import PromptRegistry

        prompt = PromptRegistry.get(
            "enrichment_analysis",
            document_content="test",
            existing_skills="none",
            existing_accomplishments="none",
        )
        assert "new_skills" in prompt
        assert "new_accomplishments" in prompt
        assert "JSON" in prompt

    def test_enrichment_prompt_instructs_dedup(self):
        from app.llm.prompts import PromptRegistry

        prompt = PromptRegistry.get(
            "enrichment_analysis",
            document_content="test",
            existing_skills="none",
            existing_accomplishments="none",
        )
        assert "NOT" in prompt
        assert "duplicate" in prompt.lower()


# ─── Task 1: EnrichmentCandidate Model Tests ──────────────────────────────


class TestEnrichmentCandidateModel:
    """Verify EnrichmentCandidate model validation and schema."""

    def test_create_valid_skill_candidate(self):
        candidate = EnrichmentCandidate(
            role_id=1,
            application_id=1,
            document_type="resume",
            candidate_type="skill",
            name="Kubernetes",
            category="DevOps",
        )
        assert candidate.name == "Kubernetes"
        assert candidate.status == "pending"
        assert candidate.resolved_at is None
        assert isinstance(candidate.created_at, datetime)

    def test_create_valid_accomplishment_candidate(self):
        candidate = EnrichmentCandidate(
            role_id=1,
            application_id=1,
            document_type="cover_letter",
            candidate_type="accomplishment",
            name="Led migration to microservices",
            context="At TechCo as Senior Engineer",
        )
        assert candidate.candidate_type == "accomplishment"
        assert candidate.document_type == "cover_letter"
        assert candidate.context == "At TechCo as Senior Engineer"

    def test_rejects_empty_name(self):
        with pytest.raises(ValueError, match="name cannot be empty"):
            EnrichmentCandidate(
                role_id=1,
                application_id=1,
                document_type="resume",
                candidate_type="skill",
                name="",
            )

    def test_rejects_invalid_document_type(self):
        with pytest.raises(ValueError, match="document_type"):
            EnrichmentCandidate(
                role_id=1,
                application_id=1,
                document_type="letter",
                candidate_type="skill",
                name="Python",
            )

    def test_rejects_invalid_candidate_type(self):
        with pytest.raises(ValueError, match="candidate_type"):
            EnrichmentCandidate(
                role_id=1,
                application_id=1,
                document_type="resume",
                candidate_type="certification",
                name="AWS",
            )

    def test_rejects_invalid_status(self):
        with pytest.raises(ValueError, match="status"):
            EnrichmentCandidate(
                role_id=1,
                application_id=1,
                document_type="resume",
                candidate_type="skill",
                name="Python",
                status="approved",
            )

    def test_read_schema_fields(self):
        """EnrichmentCandidateRead has all expected fields."""
        read = EnrichmentCandidateRead(
            id=1,
            role_id=1,
            application_id=10,
            document_type="resume",
            candidate_type="skill",
            name="Docker",
            category="DevOps",
            context=None,
            status="pending",
            created_at=datetime.now(timezone.utc),
            resolved_at=None,
        )
        assert read.id == 1
        assert read.application_id == 10
        assert read.category == "DevOps"

    def test_category_truncated_to_max_length(self):
        """Long category strings are truncated to 50 chars."""
        candidate = EnrichmentCandidate(
            role_id=1,
            application_id=1,
            document_type="resume",
            candidate_type="skill",
            name="Some Skill",
            category="A" * 100,
        )
        assert len(candidate.category) == 50

    @pytest.mark.asyncio
    async def test_enrichment_candidate_persists_to_db(self):
        """Verify EnrichmentCandidate round-trips through database."""
        from app.database import async_session_maker
        from app.models.application import Application
        from sqlmodel import select

        role_id = await _create_role()

        # Create an application first (FK requirement)
        async with async_session_maker() as session:
            app = Application(
                role_id=role_id,
                company_name="Test Co",
                job_posting="A job description for testing",
            )
            session.add(app)
            await session.commit()
            await session.refresh(app)
            app_id = app.id

        # Create enrichment candidate
        async with async_session_maker() as session:
            candidate = EnrichmentCandidate(
                role_id=role_id,
                application_id=app_id,
                document_type="resume",
                candidate_type="skill",
                name="Terraform",
                category="IaC",
            )
            session.add(candidate)
            await session.commit()
            await session.refresh(candidate)
            candidate_id = candidate.id

        # Read back
        async with async_session_maker() as session:
            result = await session.execute(
                select(EnrichmentCandidate).where(
                    EnrichmentCandidate.id == candidate_id
                )
            )
            loaded = result.scalar_one()
            assert loaded.name == "Terraform"
            assert loaded.category == "IaC"
            assert loaded.status == "pending"
            assert loaded.role_id == role_id


# ─── Task 3: Enrichment Service Tests ─────────────────────────────────────

async def _create_application_with_content(role_id: int) -> int:
    """Create an application with resume/cover letter content, return app_id."""
    from app.database import async_session_maker
    from app.models.application import Application

    async with async_session_maker() as session:
        app = Application(
            role_id=role_id,
            company_name="Acme Corp",
            job_posting="Senior Python Developer at Acme Corp. Requirements: Python, Kubernetes, Terraform.",
            resume_content="Experienced engineer with Python, Docker, and Kubernetes. Led migration to microservices reducing deployment time by 60%. Designed event-driven architecture for real-time data processing.",
            cover_letter_content="I am excited to apply for the Senior Python role. My experience with Terraform and CI/CD pipelines makes me a strong fit.",
        )
        session.add(app)
        await session.commit()
        await session.refresh(app)
        session.expunge(app)
        return app.id


class TestEnrichmentServiceAnalysis:
    """Test analyze_document_for_enrichment function."""

    @pytest.mark.asyncio
    async def test_analyze_creates_candidates(self):
        """Successful LLM call creates enrichment candidates."""
        from unittest.mock import AsyncMock, patch
        from app.services import enrichment_service
        from app.llm import Message as LLMMessage

        role_id = await _create_role()
        app_id = await _create_application_with_content(role_id)

        mock_response = LLMMessage(
            role="model",
            content='{"new_skills": [{"name": "Terraform", "category": "IaC"}], "new_accomplishments": [{"description": "Designed event-driven architecture", "context": "Data Engineering"}]}',
        )
        with patch(
            "app.services.enrichment_service.generate_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await enrichment_service.analyze_document_for_enrichment(
                app_id, role_id, "resume"
            )

        assert result["candidates_found"] == 2

        candidates = await enrichment_service.get_pending_candidates(role_id)
        assert len(candidates) == 2
        types = {c.candidate_type for c in candidates}
        assert types == {"skill", "accomplishment"}

    @pytest.mark.asyncio
    async def test_analyze_no_content_returns_zero(self):
        """Application with no document content returns zero candidates."""
        from app.database import async_session_maker
        from app.models.application import Application
        from app.services import enrichment_service

        role_id = await _create_role()
        async with async_session_maker() as session:
            app = Application(
                role_id=role_id,
                company_name="Empty Co",
                job_posting="A position that needs filling",
            )
            session.add(app)
            await session.commit()
            await session.refresh(app)
            app_id = app.id

        result = await enrichment_service.analyze_document_for_enrichment(
            app_id, role_id, "resume"
        )
        assert result["candidates_found"] == 0
        assert result["reason"] == "no_content"

    @pytest.mark.asyncio
    async def test_analyze_idempotent(self):
        """Re-running enrichment for same app+doc doesn't create duplicates."""
        from unittest.mock import AsyncMock, patch
        from app.services import enrichment_service
        from app.llm import Message as LLMMessage

        role_id = await _create_role()
        app_id = await _create_application_with_content(role_id)

        mock_response = LLMMessage(
            role="model",
            content='{"new_skills": [{"name": "Go", "category": "Language"}], "new_accomplishments": []}',
        )
        with patch(
            "app.services.enrichment_service.generate_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result1 = await enrichment_service.analyze_document_for_enrichment(
                app_id, role_id, "resume"
            )
            result2 = await enrichment_service.analyze_document_for_enrichment(
                app_id, role_id, "resume"
            )

        assert result1["candidates_found"] == 1
        assert result2["candidates_found"] == 0
        assert result2["reason"] == "already_analyzed"

    @pytest.mark.asyncio
    async def test_analyze_deduplicates_existing_skills(self):
        """Skills already in experience DB are not suggested."""
        from unittest.mock import AsyncMock, patch
        from app.services import enrichment_service
        from app.llm import Message as LLMMessage

        role_id = await _create_role()
        app_id = await _create_application_with_content(role_id)

        # Pre-seed a skill
        await experience_service.create_skill(
            role_id, SkillCreate(name="Python", category="Language", source="resume")
        )

        mock_response = LLMMessage(
            role="model",
            content='{"new_skills": [{"name": "Python", "category": "Language"}, {"name": "Rust", "category": "Language"}], "new_accomplishments": []}',
        )
        with patch(
            "app.services.enrichment_service.generate_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await enrichment_service.analyze_document_for_enrichment(
                app_id, role_id, "resume"
            )

        assert result["candidates_found"] == 1  # Only Rust, not Python
        candidates = await enrichment_service.get_pending_candidates(role_id)
        assert len(candidates) == 1
        assert candidates[0].name == "Rust"

    @pytest.mark.asyncio
    async def test_analyze_graceful_degradation_on_llm_failure(self):
        """LLM failure returns error dict, doesn't raise."""
        from unittest.mock import AsyncMock, patch
        from app.services import enrichment_service

        role_id = await _create_role()
        app_id = await _create_application_with_content(role_id)

        with patch(
            "app.services.enrichment_service.generate_with_retry",
            new_callable=AsyncMock,
            side_effect=Exception("LLM is down"),
        ):
            result = await enrichment_service.analyze_document_for_enrichment(
                app_id, role_id, "resume"
            )

        assert result["candidates_found"] == 0
        assert result["reason"] == "llm_error"

    @pytest.mark.asyncio
    async def test_analyze_no_new_items(self):
        """LLM returns empty arrays when no new items found."""
        from unittest.mock import AsyncMock, patch
        from app.services import enrichment_service
        from app.llm import Message as LLMMessage

        role_id = await _create_role()
        app_id = await _create_application_with_content(role_id)

        mock_response = LLMMessage(
            role="model",
            content='{"new_skills": [], "new_accomplishments": []}',
        )
        with patch(
            "app.services.enrichment_service.generate_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await enrichment_service.analyze_document_for_enrichment(
                app_id, role_id, "resume"
            )

        assert result["candidates_found"] == 0


class TestEnrichmentServicePendingCount:
    """Test get_pending_count function."""

    @pytest.mark.asyncio
    async def test_pending_count_zero(self):
        """No candidates returns 0."""
        role_id = await _create_role()
        count = await enrichment_service.get_pending_count(role_id)
        assert count == 0

    @pytest.mark.asyncio
    async def test_pending_count_matches_candidates(self):
        """Count matches number of pending candidates."""
        from app.database import async_session_maker

        role_id = await _create_role()
        app_id = await _create_application_with_content(role_id)

        async with async_session_maker() as session:
            for name in ["Go", "Rust", "Zig"]:
                c = EnrichmentCandidate(
                    role_id=role_id,
                    application_id=app_id,
                    document_type="resume",
                    candidate_type="skill",
                    name=name,
                )
                session.add(c)
            await session.commit()

        count = await enrichment_service.get_pending_count(role_id)
        assert count == 3

    @pytest.mark.asyncio
    async def test_pending_count_excludes_resolved(self):
        """Count excludes accepted/dismissed candidates."""
        from app.database import async_session_maker

        role_id = await _create_role()
        app_id = await _create_application_with_content(role_id)

        async with async_session_maker() as session:
            c1 = EnrichmentCandidate(
                role_id=role_id,
                application_id=app_id,
                document_type="resume",
                candidate_type="skill",
                name="Go",
            )
            session.add(c1)
            await session.commit()
            await session.refresh(c1)
            cid = c1.id

        await enrichment_service.dismiss_candidate(cid, role_id)
        count = await enrichment_service.get_pending_count(role_id)
        assert count == 0


class TestEnrichmentServiceAcceptDismiss:
    """Test accept/dismiss/bulk operations."""

    @pytest.mark.asyncio
    async def test_accept_candidate_creates_skill(self):
        """Accepting a skill candidate creates a Skill in experience DB."""
        from app.services import enrichment_service

        role_id = await _create_role()
        app_id = await _create_application_with_content(role_id)

        # Directly create a candidate for testing
        from app.database import async_session_maker

        async with async_session_maker() as session:
            candidate = EnrichmentCandidate(
                role_id=role_id,
                application_id=app_id,
                document_type="resume",
                candidate_type="skill",
                name="Terraform",
                category="IaC",
            )
            session.add(candidate)
            await session.commit()
            await session.refresh(candidate)
            cid = candidate.id

        result = await enrichment_service.accept_candidate(cid, role_id)
        assert result is True

        # Verify skill was created in experience DB
        skills = await experience_service.get_skills(role_id)
        terraform = [s for s in skills if s.name == "Terraform"]
        assert len(terraform) == 1
        assert terraform[0].source == "application-enriched"
        assert terraform[0].category == "IaC"

    @pytest.mark.asyncio
    async def test_accept_candidate_creates_accomplishment(self):
        """Accepting an accomplishment candidate creates an Accomplishment."""
        from app.services import enrichment_service
        from app.database import async_session_maker

        role_id = await _create_role()
        app_id = await _create_application_with_content(role_id)

        async with async_session_maker() as session:
            candidate = EnrichmentCandidate(
                role_id=role_id,
                application_id=app_id,
                document_type="resume",
                candidate_type="accomplishment",
                name="Led migration to microservices",
                context="At TechCo",
            )
            session.add(candidate)
            await session.commit()
            await session.refresh(candidate)
            cid = candidate.id

        result = await enrichment_service.accept_candidate(cid, role_id)
        assert result is True

        accs = await experience_service.get_accomplishments(role_id)
        matched = [a for a in accs if "microservices" in a.description]
        assert len(matched) == 1
        assert matched[0].source == "application-enriched"

    @pytest.mark.asyncio
    async def test_dismiss_candidate(self):
        """Dismissing sets status and resolved_at."""
        from app.services import enrichment_service
        from app.database import async_session_maker

        role_id = await _create_role()
        app_id = await _create_application_with_content(role_id)

        async with async_session_maker() as session:
            candidate = EnrichmentCandidate(
                role_id=role_id,
                application_id=app_id,
                document_type="resume",
                candidate_type="skill",
                name="COBOL",
            )
            session.add(candidate)
            await session.commit()
            await session.refresh(candidate)
            cid = candidate.id

        result = await enrichment_service.dismiss_candidate(cid, role_id)
        assert result is True

        # Verify candidate is no longer pending
        pending = await enrichment_service.get_pending_candidates(role_id)
        assert len(pending) == 0

        # Verify skill was NOT added to experience DB
        skills = await experience_service.get_skills(role_id)
        assert len(skills) == 0

    @pytest.mark.asyncio
    async def test_accept_wrong_role_returns_false(self):
        """Accepting a candidate from another role returns False."""
        from app.services import enrichment_service
        from app.database import async_session_maker

        role_id = await _create_role()
        app_id = await _create_application_with_content(role_id)

        async with async_session_maker() as session:
            candidate = EnrichmentCandidate(
                role_id=role_id,
                application_id=app_id,
                document_type="resume",
                candidate_type="skill",
                name="Terraform",
            )
            session.add(candidate)
            await session.commit()
            await session.refresh(candidate)
            cid = candidate.id

        result = await enrichment_service.accept_candidate(cid, role_id + 999)
        assert result is False

    @pytest.mark.asyncio
    async def test_bulk_resolve_accept(self):
        """Bulk accept resolves multiple candidates."""
        from app.services import enrichment_service
        from app.database import async_session_maker

        role_id = await _create_role()
        app_id = await _create_application_with_content(role_id)

        ids = []
        async with async_session_maker() as session:
            for name in ["Go", "Rust", "Elixir"]:
                c = EnrichmentCandidate(
                    role_id=role_id,
                    application_id=app_id,
                    document_type="resume",
                    candidate_type="skill",
                    name=name,
                    category="Language",
                )
                session.add(c)
            await session.commit()
            # Re-query to get ids
        pending = await enrichment_service.get_pending_candidates(role_id)
        ids = [c.id for c in pending]

        result = await enrichment_service.bulk_resolve(ids, role_id, "accept")
        assert result["resolved"] == 3
        assert result["skipped"] == 0

        # Verify all three skills exist in experience DB
        skills = await experience_service.get_skills(role_id)
        skill_names = {s.name for s in skills}
        assert "Go" in skill_names
        assert "Rust" in skill_names
        assert "Elixir" in skill_names

    @pytest.mark.asyncio
    async def test_bulk_resolve_dismiss(self):
        """Bulk dismiss resolves multiple candidates without adding to DB."""
        from app.services import enrichment_service
        from app.database import async_session_maker

        role_id = await _create_role()
        app_id = await _create_application_with_content(role_id)

        async with async_session_maker() as session:
            for name in ["COBOL", "Fortran"]:
                c = EnrichmentCandidate(
                    role_id=role_id,
                    application_id=app_id,
                    document_type="resume",
                    candidate_type="skill",
                    name=name,
                )
                session.add(c)
            await session.commit()

        pending = await enrichment_service.get_pending_candidates(role_id)
        ids = [c.id for c in pending]

        result = await enrichment_service.bulk_resolve(ids, role_id, "dismiss")
        assert result["resolved"] == 2

        # No skills should be in experience DB
        skills = await experience_service.get_skills(role_id)
        assert len(skills) == 0


# ─── Task 4: API Endpoint Tests ───────────────────────────────────────────

@pytest_asyncio.fixture
async def api_client():
    """Async test client for FastAPI."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_client_with_role(api_client):
    """Authenticated client with a role and X-Role-Id header."""
    await api_client.post(
        "/api/v1/auth/register",
        json={"username": "enrichapiuser", "password": "password123"},
    )
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"username": "enrichapiuser", "password": "password123"},
    )
    api_client.cookies = login.cookies

    role_resp = await api_client.post(
        "/api/v1/roles", json={"name": "Dev"}
    )
    role_id = role_resp.json()["id"]
    api_client.headers["X-Role-Id"] = str(role_id)
    return api_client, role_id


class TestEnrichmentAPIEndpoints:
    """Test enrichment API endpoints via HTTP."""

    @pytest.mark.asyncio
    async def test_get_enrichment_empty(self, auth_client_with_role):
        client, role_id = auth_client_with_role
        resp = await client.get("/api/v1/experience/enrichment")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_pending"] == 0
        assert data["candidates"] == {}

    @pytest.mark.asyncio
    async def test_get_enrichment_includes_company_name(self, auth_client_with_role):
        """GET /experience/enrichment includes company_name per group."""
        client, role_id = auth_client_with_role

        from app.database import async_session_maker
        from app.models.application import Application

        async with async_session_maker() as session:
            app = Application(
                role_id=role_id,
                company_name="Acme Corp",
                job_posting="Testing company name in enrichment response",
            )
            session.add(app)
            await session.commit()
            await session.refresh(app)
            app_id = app.id

        async with async_session_maker() as session:
            c = EnrichmentCandidate(
                role_id=role_id,
                application_id=app_id,
                document_type="resume",
                candidate_type="skill",
                name="GraphQL",
            )
            session.add(c)
            await session.commit()

        resp = await client.get("/api/v1/experience/enrichment")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_pending"] == 1
        group = data["candidates"][str(app_id)]
        assert group["company_name"] == "Acme Corp"
        assert len(group["candidates"]) == 1
        assert group["candidates"][0]["name"] == "GraphQL"

    @pytest.mark.asyncio
    async def test_get_enrichment_stats_empty(self, auth_client_with_role):
        client, role_id = auth_client_with_role
        resp = await client.get("/api/v1/experience/enrichment/stats")
        assert resp.status_code == 200
        assert resp.json()["pending_count"] == 0

    @pytest.mark.asyncio
    async def test_accept_nonexistent_returns_404(self, auth_client_with_role):
        client, role_id = auth_client_with_role
        resp = await client.post("/api/v1/experience/enrichment/999/accept")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_dismiss_nonexistent_returns_404(self, auth_client_with_role):
        client, role_id = auth_client_with_role
        resp = await client.post("/api/v1/experience/enrichment/999/dismiss")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_accept_candidate_via_api(self, auth_client_with_role):
        client, role_id = auth_client_with_role

        # Create application and candidate directly
        from app.database import async_session_maker
        from app.models.application import Application

        async with async_session_maker() as session:
            app = Application(
                role_id=role_id,
                company_name="API Test Co",
                job_posting="Testing enrichment API endpoints",
            )
            session.add(app)
            await session.commit()
            await session.refresh(app)
            app_id = app.id

        async with async_session_maker() as session:
            candidate = EnrichmentCandidate(
                role_id=role_id,
                application_id=app_id,
                document_type="resume",
                candidate_type="skill",
                name="GraphQL",
                category="API",
            )
            session.add(candidate)
            await session.commit()
            await session.refresh(candidate)
            cid = candidate.id

        # Accept via API
        resp = await client.post(f"/api/v1/experience/enrichment/{cid}/accept")
        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"

        # Verify no longer in pending
        stats = await client.get("/api/v1/experience/enrichment/stats")
        assert stats.json()["pending_count"] == 0

    @pytest.mark.asyncio
    async def test_bulk_resolve_via_api(self, auth_client_with_role):
        client, role_id = auth_client_with_role

        from app.database import async_session_maker
        from app.models.application import Application

        async with async_session_maker() as session:
            app = Application(
                role_id=role_id,
                company_name="Bulk Test Co",
                job_posting="Testing bulk enrichment operations",
            )
            session.add(app)
            await session.commit()
            await session.refresh(app)
            app_id = app.id

        ids = []
        async with async_session_maker() as session:
            for name in ["Scala", "Haskell"]:
                c = EnrichmentCandidate(
                    role_id=role_id,
                    application_id=app_id,
                    document_type="resume",
                    candidate_type="skill",
                    name=name,
                )
                session.add(c)
            await session.commit()

        # Get IDs from pending (new response shape: group has company_name + candidates)
        pending_resp = await client.get("/api/v1/experience/enrichment")
        candidates = pending_resp.json()["candidates"]
        for group in candidates.values():
            for c in group["candidates"]:
                ids.append(c["id"])

        resp = await client.post(
            "/api/v1/experience/enrichment/bulk",
            json={"candidate_ids": ids, "action": "dismiss"},
        )
        assert resp.status_code == 200
        assert resp.json()["resolved"] == 2

    @pytest.mark.asyncio
    async def test_trigger_enrichment_via_api(self, auth_client_with_role):
        """POST /applications/{id}/enrich triggers enrichment."""
        client, role_id = auth_client_with_role

        # Create application with content
        from app.database import async_session_maker
        from app.models.application import Application
        from unittest.mock import AsyncMock, patch
        from app.llm import Message as LLMMessage

        async with async_session_maker() as session:
            app = Application(
                role_id=role_id,
                company_name="Trigger Co",
                job_posting="Testing enrichment trigger endpoint",
                resume_content="Expert in Zig programming and WASM compilation",
                resume_approved=True,
            )
            session.add(app)
            await session.commit()
            await session.refresh(app)
            app_id = app.id

        mock_response = LLMMessage(
            role="model",
            content='{"new_skills": [{"name": "Zig", "category": "Language"}], "new_accomplishments": []}',
        )
        with patch(
            "app.services.enrichment_service.generate_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            resp = await client.post(f"/api/v1/applications/{app_id}/enrich")

        assert resp.status_code == 200
        data = resp.json()
        assert data["application_id"] == app_id
        assert data["resume_result"]["candidates_found"] == 1


# ─── Task 5: Document Approval Hook Tests ─────────────────────────────────


class TestEnrichmentApprovalHook:
    """Test that enrichment triggers on document approval."""

    @pytest.mark.asyncio
    async def test_approval_does_not_block_response(self, auth_client_with_role):
        """Setting resume_approved=True returns immediately (background task)."""
        client, role_id = auth_client_with_role

        from app.database import async_session_maker
        from app.models.application import Application

        async with async_session_maker() as session:
            app = Application(
                role_id=role_id,
                company_name="Approval Co",
                job_posting="Testing approval hook for enrichment",
                resume_content="Resume with advanced Python skills",
            )
            session.add(app)
            await session.commit()
            await session.refresh(app)
            app_id = app.id

        # Patch the enrichment service to verify it gets called
        from unittest.mock import AsyncMock, patch

        mock_analyze = AsyncMock(return_value={"candidates_found": 0, "reason": "mocked"})
        with patch.object(
            enrichment_service,
            "analyze_document_for_enrichment",
            mock_analyze,
        ):
            resp = await client.patch(
                f"/api/v1/applications/{app_id}",
                json={"resume_approved": True},
            )

        assert resp.status_code == 200
        assert resp.json()["resume_approved"] is True
        # Verify enrichment was actually triggered as a background task
        mock_analyze.assert_called_once_with(
            application_id=app_id, role_id=role_id, document_type="resume"
        )

    @pytest.mark.asyncio
    async def test_approval_false_does_not_trigger(self, auth_client_with_role):
        """Setting resume_approved=False does not trigger enrichment."""
        client, role_id = auth_client_with_role

        from app.database import async_session_maker
        from app.models.application import Application
        from unittest.mock import AsyncMock, patch

        async with async_session_maker() as session:
            app = Application(
                role_id=role_id,
                company_name="NoApproval Co",
                job_posting="Testing that no enrichment triggers",
                resume_content="Resume content here",
            )
            session.add(app)
            await session.commit()
            await session.refresh(app)
            app_id = app.id

        mock_analyze = AsyncMock()
        with patch.object(
            enrichment_service,
            "analyze_document_for_enrichment",
            mock_analyze,
        ):
            resp = await client.patch(
                f"/api/v1/applications/{app_id}",
                json={"resume_approved": False},
            )

        assert resp.status_code == 200
        mock_analyze.assert_not_called()
