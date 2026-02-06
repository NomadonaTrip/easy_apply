"""Tests for keyword extraction service and endpoint."""

import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock

from app.main import app
from app.services.keyword_service import (
    extract_keywords,
    keywords_to_json,
    json_to_keywords,
)
from app.utils.llm_helpers import extract_json_from_response
from app.models.keyword import Keyword, KeywordList, KeywordCategory


# --- Unit Tests: _extract_json_from_response ---


class TestExtractJsonFromResponse:
    """Test JSON extraction from LLM responses."""

    def test_handles_markdown_json_code_blocks(self):
        wrapped = '```json\n{"keywords": [{"text": "Python", "priority": 9}]}\n```'
        result = extract_json_from_response(wrapped)
        data = json.loads(result)
        assert data["keywords"][0]["text"] == "Python"

    def test_handles_plain_code_blocks(self):
        wrapped = '```\n{"keywords": [{"text": "React", "priority": 8}]}\n```'
        result = extract_json_from_response(wrapped)
        data = json.loads(result)
        assert data["keywords"][0]["text"] == "React"

    def test_handles_plain_json(self):
        plain = '{"keywords": [{"text": "React", "priority": 8}]}'
        result = extract_json_from_response(plain)
        data = json.loads(result)
        assert data["keywords"][0]["text"] == "React"

    def test_handles_empty_string(self):
        assert extract_json_from_response("") == ""

    def test_handles_none(self):
        assert extract_json_from_response(None) == ""


# --- Unit Tests: Keyword Serialization ---


class TestKeywordSerialization:
    """Test keyword serialization/deserialization."""

    def test_keywords_to_json_and_back(self):
        keywords = KeywordList(keywords=[
            Keyword(text="Python", priority=9, category=KeywordCategory.TECHNICAL_SKILL),
            Keyword(text="Leadership", priority=7, category=KeywordCategory.SOFT_SKILL),
        ])

        json_str = keywords_to_json(keywords)
        restored = json_to_keywords(json_str)

        assert len(restored.keywords) == 2
        assert restored.keywords[0].text == "Python"
        assert restored.keywords[0].priority == 9
        assert restored.keywords[0].category == KeywordCategory.TECHNICAL_SKILL
        assert restored.keywords[1].text == "Leadership"

    def test_json_to_keywords_empty_string(self):
        result = json_to_keywords("")
        assert len(result.keywords) == 0

    def test_json_to_keywords_none(self):
        result = json_to_keywords(None)
        assert len(result.keywords) == 0


# --- Unit Tests: Keyword Model Validation ---


class TestKeywordModel:
    """Test Keyword Pydantic model validation."""

    def test_valid_keyword(self):
        k = Keyword(text="Python", priority=9, category="technical_skill")
        assert k.text == "Python"
        assert k.priority == 9

    def test_priority_min_boundary(self):
        k = Keyword(text="Test", priority=1)
        assert k.priority == 1

    def test_priority_max_boundary(self):
        k = Keyword(text="Test", priority=10)
        assert k.priority == 10

    def test_priority_below_min_fails(self):
        with pytest.raises(Exception):
            Keyword(text="Test", priority=0)

    def test_priority_above_max_fails(self):
        with pytest.raises(Exception):
            Keyword(text="Test", priority=11)

    def test_empty_text_fails(self):
        with pytest.raises(Exception):
            Keyword(text="", priority=5)

    def test_default_category_is_general(self):
        k = Keyword(text="Test", priority=5)
        assert k.category == KeywordCategory.GENERAL


# --- Unit Tests: extract_keywords service ---


@pytest.fixture
def sample_job_posting():
    return """
    Senior Product Manager

    Requirements:
    - 5+ years of product management experience
    - Strong analytical skills
    - Experience with Agile methodologies
    - Excellent communication skills
    - Technical background preferred
    """


@pytest.fixture
def mock_llm_response():
    return json.dumps({
        "keywords": [
            {"text": "Product Management", "priority": 9, "category": "experience"},
            {"text": "Analytical Skills", "priority": 7, "category": "soft_skill"},
            {"text": "Agile", "priority": 8, "category": "tool"},
            {"text": "Communication", "priority": 6, "category": "soft_skill"},
        ]
    })


class TestExtractKeywords:
    """Test keyword extraction service function."""

    @pytest.mark.asyncio
    @patch('app.services.keyword_service.get_llm_provider')
    async def test_returns_sorted_keyword_list(self, mock_get_provider, sample_job_posting, mock_llm_response):
        mock_provider = AsyncMock()
        mock_provider.generate.return_value = MagicMock(content=mock_llm_response)
        mock_get_provider.return_value = mock_provider

        result = await extract_keywords(sample_job_posting)

        assert isinstance(result, KeywordList)
        assert len(result.keywords) == 4
        # Verify sorted by priority descending
        for i in range(len(result.keywords) - 1):
            assert result.keywords[i].priority >= result.keywords[i + 1].priority

    @pytest.mark.asyncio
    @patch('app.services.keyword_service.get_llm_provider')
    async def test_handles_markdown_wrapped_response(self, mock_get_provider, sample_job_posting, mock_llm_response):
        wrapped = f'```json\n{mock_llm_response}\n```'
        mock_provider = AsyncMock()
        mock_provider.generate.return_value = MagicMock(content=wrapped)
        mock_get_provider.return_value = mock_provider

        result = await extract_keywords(sample_job_posting)

        assert isinstance(result, KeywordList)
        assert len(result.keywords) == 4

    @pytest.mark.asyncio
    @patch('app.services.keyword_service.get_llm_provider')
    async def test_raises_on_empty_response(self, mock_get_provider, sample_job_posting):
        mock_provider = AsyncMock()
        mock_provider.generate.return_value = MagicMock(content='')
        mock_get_provider.return_value = mock_provider

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await extract_keywords(sample_job_posting)
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    @patch('app.services.keyword_service.get_llm_provider')
    async def test_raises_on_invalid_json(self, mock_get_provider, sample_job_posting):
        mock_provider = AsyncMock()
        mock_provider.generate.return_value = MagicMock(content='not valid json at all')
        mock_get_provider.return_value = mock_provider

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await extract_keywords(sample_job_posting)
        assert exc_info.value.status_code == 500


# --- Integration Tests: Keyword Extraction Endpoint ---


@pytest_asyncio.fixture
async def authenticated_client():
    """Create an authenticated client with a session cookie."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Register and login
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


class TestExtractKeywordsEndpoint:
    """Test POST /api/v1/applications/{id}/keywords/extract endpoint."""

    @pytest.mark.asyncio
    @patch('app.services.keyword_service.get_llm_provider')
    async def test_extract_keywords_success(self, mock_get_provider, client_with_role, mock_llm_response):
        client, role_id = client_with_role

        mock_provider = AsyncMock()
        mock_provider.generate.return_value = MagicMock(content=mock_llm_response)
        mock_get_provider.return_value = mock_provider

        # Create an application first
        app_response = await client.post("/api/v1/applications", json={
            "company_name": "Test Corp",
            "job_posting": "We need a Senior Python Developer with 5+ years experience.",
        })
        assert app_response.status_code == 201
        app_id = app_response.json()["id"]

        # Extract keywords
        response = await client.post(f"/api/v1/applications/{app_id}/keywords/extract")
        assert response.status_code == 200

        data = response.json()
        assert data["application_id"] == app_id
        assert len(data["keywords"]) == 4
        assert data["status"] == "keywords"

    @pytest.mark.asyncio
    async def test_extract_keywords_not_found(self, client_with_role):
        client, _ = client_with_role
        response = await client.post("/api/v1/applications/9999/keywords/extract")
        assert response.status_code == 404

    @pytest.mark.asyncio
    @patch('app.services.keyword_service.get_llm_provider')
    async def test_extract_keywords_updates_application_status(self, mock_get_provider, client_with_role, mock_llm_response):
        client, role_id = client_with_role

        mock_provider = AsyncMock()
        mock_provider.generate.return_value = MagicMock(content=mock_llm_response)
        mock_get_provider.return_value = mock_provider

        app_response = await client.post("/api/v1/applications", json={
            "company_name": "Test Corp",
            "job_posting": "We need a Senior Python Developer with 5+ years experience.",
        })
        app_id = app_response.json()["id"]

        await client.post(f"/api/v1/applications/{app_id}/keywords/extract")

        # Verify the application was updated
        get_response = await client.get(f"/api/v1/applications/{app_id}")
        assert get_response.status_code == 200
        app_data = get_response.json()
        assert app_data["status"] == "keywords"
        assert app_data["keywords"] is not None
        keywords_data = json.loads(app_data["keywords"])
        assert len(keywords_data) == 4

    @pytest.mark.asyncio
    @patch('app.services.application_service.get_application', new_callable=AsyncMock)
    async def test_extract_keywords_no_job_posting(self, mock_get_app, client_with_role):
        """Test returns 400 when application has no job_posting."""
        client, role_id = client_with_role

        mock_app = MagicMock()
        mock_app.job_posting = None
        mock_get_app.return_value = mock_app

        response = await client.post("/api/v1/applications/1/keywords/extract")
        assert response.status_code == 400
