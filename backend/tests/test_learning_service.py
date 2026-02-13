"""Tests for learning service and keyword pattern model."""

import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock

from app.main import app
from app.database import async_session_maker
from app.models.application import ApplicationStatus
from app.models.keyword_pattern import KeywordPattern, KeywordPatternRead
from app.services import application_service
from app.services.learning_service import (
    get_keyword_patterns,
    record_keyword_usage,
    record_application_success,
    apply_pattern_boost,
    MIN_CONFIDENCE_THRESHOLD,
    SUCCESS_STATUSES,
)


# --- Unit Tests: KeywordPattern Model ---


class TestKeywordPatternModel:
    """Test KeywordPattern SQLModel table model."""

    def test_create_keyword_pattern(self):
        pattern = KeywordPattern(
            role_id=1,
            keyword="python",
        )
        assert pattern.role_id == 1
        assert pattern.keyword == "python"
        assert pattern.times_used == 0
        assert pattern.times_successful == 0
        assert pattern.success_rate == 0.0

    def test_keyword_pattern_requires_role_id(self):
        with pytest.raises(ValueError, match="role_id is required"):
            KeywordPattern(keyword="python")

    def test_keyword_pattern_requires_keyword(self):
        with pytest.raises(ValueError, match="keyword cannot be empty"):
            KeywordPattern(role_id=1, keyword="")

    def test_keyword_pattern_read_schema(self):
        read = KeywordPatternRead(
            id=1,
            role_id=1,
            keyword="python",
            times_used=5,
            times_successful=3,
            success_rate=0.6,
        )
        assert read.keyword == "python"
        assert read.success_rate == 0.6


# --- Unit Tests: apply_pattern_boost ---


class TestApplyPatternBoost:
    """Test pattern-based keyword score boosting."""

    def test_no_patterns_returns_keywords_unchanged(self):
        keywords = [
            {"keyword": "Python", "score": 0.8},
            {"keyword": "React", "score": 0.6},
        ]
        result = apply_pattern_boost(keywords, {})
        assert len(result) == 2
        assert result[0]["score"] == 0.8
        assert result[1]["score"] == 0.6

    def test_pattern_boost_increases_score(self):
        keywords = [
            {"keyword": "Python", "score": 0.5},
            {"keyword": "React", "score": 0.5},
        ]
        patterns = {"python": 1.0}  # 100% success rate

        result = apply_pattern_boost(keywords, patterns, boost_weight=0.3)

        # Python should be boosted: (0.7 * 0.5) + (0.3 * 1.0) = 0.65
        python_kw = next(k for k in result if k["keyword"] == "Python")
        assert python_kw["score"] == pytest.approx(0.65, abs=0.01)
        assert python_kw["pattern_boosted"] is True

        # React should be unchanged
        react_kw = next(k for k in result if k["keyword"] == "React")
        assert react_kw["score"] == 0.5
        assert react_kw["pattern_boosted"] is False

    def test_pattern_boost_re_sorts_by_score(self):
        keywords = [
            {"keyword": "React", "score": 0.7},
            {"keyword": "Python", "score": 0.5},
        ]
        patterns = {"python": 1.0}  # High success rate

        result = apply_pattern_boost(keywords, patterns, boost_weight=0.5)

        # Python boosted to (0.5 * 0.5) + (0.5 * 1.0) = 0.75, above React's 0.7
        assert result[0]["keyword"] == "Python"
        assert result[1]["keyword"] == "React"

    def test_pattern_boost_case_insensitive(self):
        keywords = [{"keyword": "Python", "score": 0.5}]
        patterns = {"python": 0.8}

        result = apply_pattern_boost(keywords, patterns)
        assert result[0]["pattern_boosted"] is True

    def test_pattern_boost_preserves_extra_fields(self):
        keywords = [{"keyword": "Python", "score": 0.5, "category": "technical_skill"}]
        patterns = {"python": 0.8}

        result = apply_pattern_boost(keywords, patterns)
        assert result[0]["category"] == "technical_skill"


# --- Integration Tests: Learning Service Database Operations ---


@pytest_asyncio.fixture
async def authenticated_client():
    """Create an authenticated client with a session cookie."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/v1/auth/register", json={
            "username": "testuser", "password": "TestPass123!"
        })
        await ac.post("/api/v1/auth/login", json={
            "username": "testuser", "password": "TestPass123!"
        })
        yield ac


@pytest_asyncio.fixture
async def client_with_role(authenticated_client):
    """Create a client with an authenticated session and active role."""
    role_response = await authenticated_client.post("/api/v1/roles", json={"name": "Software Engineer"})
    role_id = role_response.json()["id"]
    authenticated_client.headers["X-Role-Id"] = str(role_id)
    return authenticated_client, role_id


class TestRecordKeywordUsage:
    """Test recording keyword usage in the database."""

    @pytest.mark.asyncio
    async def test_records_new_keywords(self, client_with_role):
        _, role_id = client_with_role

        await record_keyword_usage(role_id, ["python", "react"])

        patterns = await get_keyword_patterns(role_id)
        # No patterns returned yet - below threshold
        assert len(patterns) == 0

    @pytest.mark.asyncio
    async def test_increments_usage_count(self, client_with_role):
        _, role_id = client_with_role

        await record_keyword_usage(role_id, ["python"])
        await record_keyword_usage(role_id, ["python"])

        # Verify count via direct query
        from sqlmodel import select
        async with async_session_maker() as session:
            result = await session.execute(
                select(KeywordPattern).where(
                    KeywordPattern.role_id == role_id,
                    KeywordPattern.keyword == "python"
                )
            )
            pattern = result.scalar_one()
            assert pattern.times_used == 2

    @pytest.mark.asyncio
    async def test_normalizes_keyword_case(self, client_with_role):
        _, role_id = client_with_role

        await record_keyword_usage(role_id, ["Python"])
        await record_keyword_usage(role_id, ["PYTHON"])

        from sqlmodel import select
        async with async_session_maker() as session:
            result = await session.execute(
                select(KeywordPattern).where(
                    KeywordPattern.role_id == role_id,
                    KeywordPattern.keyword == "python"
                )
            )
            pattern = result.scalar_one()
            assert pattern.times_used == 2


class TestRecordApplicationSuccess:
    """Test recording successful application outcomes."""

    @pytest.mark.asyncio
    async def test_updates_success_count_and_rate(self, client_with_role):
        client, role_id = client_with_role

        # First, record keyword usage enough times to meet threshold
        for _ in range(MIN_CONFIDENCE_THRESHOLD):
            await record_keyword_usage(role_id, ["python"])

        # Create an application with keywords
        app_response = await client.post("/api/v1/applications", json={
            "company_name": "Test Corp",
            "job_posting": "We need a Senior Python Developer with 5+ years experience.",
        })
        app_id = app_response.json()["id"]

        # Set keywords on the application
        from app.models.application import ApplicationUpdate
        from app.services.keyword_service import keywords_to_json
        from app.models.keyword import Keyword, KeywordList

        kw_list = KeywordList(keywords=[
            Keyword(text="python", priority=9, category="technical_skill")
        ])
        await application_service.update_application(
            app_id, role_id, ApplicationUpdate(keywords=keywords_to_json(kw_list))
        )

        # Get the application for recording success
        application = await application_service.get_application(app_id, role_id)

        # Record success
        await record_application_success(application)

        # Verify patterns updated
        patterns = await get_keyword_patterns(role_id)
        assert "python" in patterns
        assert patterns["python"] > 0

    @pytest.mark.asyncio
    async def test_no_keywords_is_noop(self, client_with_role):
        """If application has no keywords, record_application_success should be a no-op."""
        client, role_id = client_with_role

        app_response = await client.post("/api/v1/applications", json={
            "company_name": "Test Corp",
            "job_posting": "We need a Senior Python Developer with 5+ years experience.",
        })
        app_id = app_response.json()["id"]

        application = await application_service.get_application(app_id, role_id)

        # Should not raise
        await record_application_success(application)


class TestGetKeywordPatterns:
    """Test retrieving keyword patterns."""

    @pytest.mark.asyncio
    async def test_returns_empty_without_data(self, client_with_role):
        _, role_id = client_with_role

        patterns = await get_keyword_patterns(role_id)

        assert patterns == {}

    @pytest.mark.asyncio
    async def test_only_returns_patterns_above_threshold(self, client_with_role):
        _, role_id = client_with_role

        # Record python enough times
        for _ in range(MIN_CONFIDENCE_THRESHOLD):
            await record_keyword_usage(role_id, ["python"])
        # Record react only once (below threshold)
        await record_keyword_usage(role_id, ["react"])

        patterns = await get_keyword_patterns(role_id)

        # Python meets threshold (3 uses), returned with success_rate 0.0
        assert "python" in patterns
        assert patterns["python"] == 0.0
        # React doesn't meet threshold, should not be returned
        assert "react" not in patterns

    @pytest.mark.asyncio
    async def test_role_isolation(self, client_with_role):
        """Patterns from one role should not leak to another."""
        client, role_id = client_with_role

        for _ in range(MIN_CONFIDENCE_THRESHOLD):
            await record_keyword_usage(role_id, ["python"])

        # Create second role
        role2_response = await client.post("/api/v1/roles", json={"name": "Data Scientist"})
        role2_id = role2_response.json()["id"]

        patterns = await get_keyword_patterns(role2_id)

        assert patterns == {}

    @pytest.mark.asyncio
    async def test_requires_role_id(self):
        with pytest.raises(ValueError, match="role_id is required"):
            await get_keyword_patterns(None)


# --- Integration Tests: Keyword Extraction with Pattern Boosting (Task 3) ---


class TestKeywordExtractionWithPatterns:
    """Test that keyword extraction integrates pattern boosting."""

    @pytest.mark.asyncio
    @patch('app.services.keyword_service.get_llm_provider')
    async def test_extraction_returns_pattern_info(self, mock_get_provider, client_with_role):
        """Extract keywords endpoint returns patterns_applied and pattern_count."""
        client, role_id = client_with_role

        mock_llm_response = json.dumps({
            "keywords": [
                {"text": "Python", "priority": 9, "category": "technical_skill"},
                {"text": "React", "priority": 7, "category": "tool"},
            ]
        })
        mock_provider = AsyncMock()
        mock_provider.generate.return_value = MagicMock(content=mock_llm_response)
        mock_get_provider.return_value = mock_provider

        app_response = await client.post("/api/v1/applications", json={
            "company_name": "Test Corp",
            "job_posting": "We need a Senior Python Developer with React experience.",
        })
        app_id = app_response.json()["id"]

        response = await client.post(f"/api/v1/applications/{app_id}/keywords/extract")
        assert response.status_code == 200

        data = response.json()
        assert "patterns_applied" in data
        assert "pattern_count" in data
        # No patterns yet, so should be False/0
        assert data["patterns_applied"] is False
        assert data["pattern_count"] == 0

    @pytest.mark.asyncio
    @patch('app.services.keyword_service.get_llm_provider')
    async def test_extraction_applies_patterns_when_available(self, mock_get_provider, client_with_role):
        """When patterns exist with sufficient data, they influence keyword ranking."""
        client, role_id = client_with_role

        # Build up pattern data for "python" - record usage enough times
        for _ in range(MIN_CONFIDENCE_THRESHOLD):
            await record_keyword_usage(role_id, ["python"])

        # Record success for python pattern
        from sqlmodel import select
        async with async_session_maker() as session:
            result = await session.execute(
                select(KeywordPattern).where(
                    KeywordPattern.role_id == role_id,
                    KeywordPattern.keyword == "python"
                )
            )
            pattern = result.scalar_one()
            pattern.times_successful = 2
            pattern.success_rate = pattern.times_successful / pattern.times_used
            await session.commit()

        # Now extract keywords - python should be boosted
        mock_llm_response = json.dumps({
            "keywords": [
                {"text": "React", "priority": 8, "category": "tool"},
                {"text": "Python", "priority": 6, "category": "technical_skill"},
            ]
        })
        mock_provider = AsyncMock()
        mock_provider.generate.return_value = MagicMock(content=mock_llm_response)
        mock_get_provider.return_value = mock_provider

        app_response = await client.post("/api/v1/applications", json={
            "company_name": "Test Corp",
            "job_posting": "We need a Senior Python Developer with React experience.",
        })
        app_id = app_response.json()["id"]

        response = await client.post(f"/api/v1/applications/{app_id}/keywords/extract")
        assert response.status_code == 200

        data = response.json()
        assert data["patterns_applied"] is True
        assert data["pattern_count"] == 1

    @pytest.mark.asyncio
    @patch('app.services.keyword_service.get_llm_provider')
    async def test_extraction_records_keyword_usage(self, mock_get_provider, client_with_role):
        """Keyword extraction records usage for future pattern learning."""
        client, role_id = client_with_role

        mock_llm_response = json.dumps({
            "keywords": [
                {"text": "Python", "priority": 9, "category": "technical_skill"},
            ]
        })
        mock_provider = AsyncMock()
        mock_provider.generate.return_value = MagicMock(content=mock_llm_response)
        mock_get_provider.return_value = mock_provider

        app_response = await client.post("/api/v1/applications", json={
            "company_name": "Test Corp",
            "job_posting": "We need a Senior Python Developer.",
        })
        app_id = app_response.json()["id"]

        await client.post(f"/api/v1/applications/{app_id}/keywords/extract")

        # Verify keyword usage was recorded
        from sqlmodel import select
        async with async_session_maker() as session:
            result = await session.execute(
                select(KeywordPattern).where(
                    KeywordPattern.role_id == role_id,
                    KeywordPattern.keyword == "python"
                )
            )
            pattern = result.scalar_one_or_none()
            assert pattern is not None
            assert pattern.times_used == 1

    @pytest.mark.asyncio
    @patch('app.services.keyword_service.get_llm_provider')
    async def test_extraction_without_patterns_falls_back(self, mock_get_provider, client_with_role):
        """Without patterns, keywords are ranked by relevance only."""
        client, role_id = client_with_role

        mock_llm_response = json.dumps({
            "keywords": [
                {"text": "Python", "priority": 9, "category": "technical_skill"},
                {"text": "React", "priority": 7, "category": "tool"},
            ]
        })
        mock_provider = AsyncMock()
        mock_provider.generate.return_value = MagicMock(content=mock_llm_response)
        mock_get_provider.return_value = mock_provider

        app_response = await client.post("/api/v1/applications", json={
            "company_name": "Test Corp",
            "job_posting": "We need a Senior Python Developer with React.",
        })
        app_id = app_response.json()["id"]

        response = await client.post(f"/api/v1/applications/{app_id}/keywords/extract")
        data = response.json()

        assert data["patterns_applied"] is False
        # Keywords should be in original priority order
        assert data["keywords"][0]["text"] == "Python"
        assert data["keywords"][0]["priority"] == 9


# --- Integration Tests: Status Change Triggers Learning (Task 4) ---


class TestStatusChangeTriggersLearning:
    """Test that status changes to callback/offer record success patterns."""

    @pytest.mark.asyncio
    @patch('app.services.keyword_service.get_llm_provider')
    async def test_callback_status_records_success(self, mock_get_provider, client_with_role):
        """Transitioning to callback records keyword success patterns."""
        client, role_id = client_with_role

        mock_llm_response = json.dumps({
            "keywords": [
                {"text": "Python", "priority": 9, "category": "technical_skill"},
                {"text": "React", "priority": 7, "category": "tool"},
            ]
        })
        mock_provider = AsyncMock()
        mock_provider.generate.return_value = MagicMock(content=mock_llm_response)
        mock_get_provider.return_value = mock_provider

        # Create application and extract keywords
        app_response = await client.post("/api/v1/applications", json={
            "company_name": "Test Corp",
            "job_posting": "We need a Senior Python Developer with React experience.",
        })
        app_id = app_response.json()["id"]
        await client.post(f"/api/v1/applications/{app_id}/keywords/extract")

        # Progress through the workflow to reach "sent"
        for status in ["researching", "reviewed", "generating", "exported", "sent"]:
            resp = await client.patch(
                f"/api/v1/applications/{app_id}/status",
                json={"status": status},
            )
            assert resp.status_code == 200, f"Failed to transition to {status}: {resp.json()}"

        # Transition to callback - should trigger learning
        resp = await client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "callback"},
        )
        assert resp.status_code == 200

        # Verify success was recorded for keywords
        from sqlmodel import select
        async with async_session_maker() as session:
            result = await session.execute(
                select(KeywordPattern).where(
                    KeywordPattern.role_id == role_id,
                    KeywordPattern.keyword == "python"
                )
            )
            pattern = result.scalar_one_or_none()
            assert pattern is not None
            assert pattern.times_successful >= 1

    @pytest.mark.asyncio
    async def test_non_success_status_does_not_record(self, client_with_role):
        """Status changes that aren't callback/offer don't trigger learning."""
        client, role_id = client_with_role

        # Create application with keywords manually
        app_response = await client.post("/api/v1/applications", json={
            "company_name": "Test Corp",
            "job_posting": "We need a Senior Python Developer.",
        })
        app_id = app_response.json()["id"]

        # Set keywords directly
        from app.models.keyword import Keyword, KeywordList
        from app.services.keyword_service import keywords_to_json
        from app.models.application import ApplicationUpdate

        kw_list = KeywordList(keywords=[
            Keyword(text="python", priority=9, category="technical_skill")
        ])
        await application_service.update_application(
            app_id, role_id, ApplicationUpdate(
                keywords=keywords_to_json(kw_list),
                status=ApplicationStatus.CREATED,
            )
        )

        # Transition to keywords (not a success status)
        resp = await client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "keywords"},
        )
        assert resp.status_code == 200

        # Verify no success patterns were recorded
        from sqlmodel import select
        async with async_session_maker() as session:
            result = await session.execute(
                select(KeywordPattern).where(
                    KeywordPattern.role_id == role_id,
                )
            )
            patterns = result.scalars().all()
            # Either no patterns or none with successes
            for p in patterns:
                assert p.times_successful == 0

    @pytest.mark.asyncio
    @patch('app.services.keyword_service.get_llm_provider')
    async def test_offer_status_also_records_success(self, mock_get_provider, client_with_role):
        """Transitioning to offer (not just callback) also records success."""
        client, role_id = client_with_role

        mock_llm_response = json.dumps({
            "keywords": [
                {"text": "Python", "priority": 9, "category": "technical_skill"},
            ]
        })
        mock_provider = AsyncMock()
        mock_provider.generate.return_value = MagicMock(content=mock_llm_response)
        mock_get_provider.return_value = mock_provider

        app_response = await client.post("/api/v1/applications", json={
            "company_name": "Test Corp",
            "job_posting": "We need a Senior Python Developer.",
        })
        app_id = app_response.json()["id"]
        await client.post(f"/api/v1/applications/{app_id}/keywords/extract")

        # Progress to sent, then callback, then offer
        for status in ["researching", "reviewed", "generating", "exported", "sent"]:
            await client.patch(
                f"/api/v1/applications/{app_id}/status",
                json={"status": status},
            )

        await client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "callback"},
        )

        # Now transition callback -> offer
        resp = await client.patch(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "offer"},
        )
        assert resp.status_code == 200

        # Callback already recorded success, offer from callback should not double-count
        # (because callback is already a success status)
        from sqlmodel import select
        async with async_session_maker() as session:
            result = await session.execute(
                select(KeywordPattern).where(
                    KeywordPattern.role_id == role_id,
                    KeywordPattern.keyword == "python"
                )
            )
            pattern = result.scalar_one_or_none()
            assert pattern is not None
            # Should only be 1 success (from callback), not 2
            assert pattern.times_successful == 1


# --- Comprehensive AC Verification Tests (Task 6) ---


class TestPatternLearningACVerification:
    """Comprehensive tests verifying all acceptance criteria."""

    @pytest.mark.asyncio
    async def test_ac1_successful_apps_boost_keywords(self, client_with_role):
        """AC1: Keywords similar to successful applications are ranked higher."""
        _, role_id = client_with_role

        # Simulate a history: python used 5 times, 3 successes
        async with async_session_maker() as session:
            pattern = KeywordPattern(
                role_id=role_id,
                keyword="python",
                times_used=5,
                times_successful=3,
            )
            pattern.success_rate = 3 / 5  # 0.6
            session.add(pattern)
            await session.commit()

        # Verify boost applies
        keywords = [
            {"keyword": "React", "score": 0.7},
            {"keyword": "Python", "score": 0.5},
        ]
        patterns = await get_keyword_patterns(role_id)

        result = apply_pattern_boost(keywords, patterns)
        python_kw = next(k for k in result if k["keyword"] == "Python")
        react_kw = next(k for k in result if k["keyword"] == "React")

        # Python should be boosted above its original score
        assert python_kw["score"] > 0.5
        assert python_kw["pattern_boosted"] is True
        assert react_kw["pattern_boosted"] is False

    @pytest.mark.asyncio
    async def test_ac4_no_patterns_relevance_only(self, client_with_role):
        """AC4: Without successful applications, keywords ranked by relevance only."""
        _, role_id = client_with_role

        patterns = await get_keyword_patterns(role_id)

        assert patterns == {}

        keywords = [
            {"keyword": "Python", "score": 0.9},
            {"keyword": "React", "score": 0.7},
        ]
        result = apply_pattern_boost(keywords, patterns)

        # No change
        assert result[0]["keyword"] == "Python"
        assert result[0]["score"] == 0.9
        assert result[1]["keyword"] == "React"
        assert result[1]["score"] == 0.7

    @pytest.mark.asyncio
    async def test_patterns_scoped_to_role(self, client_with_role):
        """Patterns from role A don't affect role B (role isolation)."""
        client, role_id = client_with_role

        async with async_session_maker() as session:
            pattern = KeywordPattern(
                role_id=role_id,
                keyword="python",
                times_used=5,
                times_successful=5,
            )
            pattern.success_rate = 1.0
            session.add(pattern)
            await session.commit()

        # Create second role
        role2_response = await client.post("/api/v1/roles", json={"name": "Data Scientist"})
        role2_id = role2_response.json()["id"]

        # Role 2 should have no patterns
        patterns = await get_keyword_patterns(role2_id)
        assert patterns == {}

    @pytest.mark.asyncio
    async def test_pattern_storage_and_retrieval(self, client_with_role):
        """Test pattern storage: create, update, and retrieve patterns."""
        _, role_id = client_with_role

        # Record usage
        await record_keyword_usage(role_id, ["python", "react", "aws"])

        # Verify stored
        from sqlmodel import select
        async with async_session_maker() as session:
            result = await session.execute(
                select(KeywordPattern).where(KeywordPattern.role_id == role_id)
            )
            patterns = result.scalars().all()
            assert len(patterns) == 3
            assert all(p.times_used == 1 for p in patterns)

    @pytest.mark.asyncio
    async def test_min_confidence_threshold_respected(self, client_with_role):
        """Patterns below minimum confidence threshold are not returned."""
        _, role_id = client_with_role

        # Record usage below threshold
        await record_keyword_usage(role_id, ["python"])

        # Should not be returned
        patterns = await get_keyword_patterns(role_id)
        assert "python" not in patterns
