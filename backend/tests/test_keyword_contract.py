"""Cross-layer contract tests for keyword extraction API boundary.

These tests validate the exact JSON shape that the frontend expects.
If either the backend response shape or the frontend interface changes,
these tests MUST break to prevent silent contract drift.

Frontend contract (from frontend/src/api/applications.ts):
  Keyword: { text: string, priority: number, category: string, pattern_boosted?: boolean }
  KeywordExtractionResponse: {
    application_id: number, keywords: Keyword[], status: string,
    patterns_applied: boolean, pattern_count: number
  }
"""

import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock

from app.main import app
from app.models.keyword import Keyword, KeywordList, KeywordCategory, KeywordExtractionResponse
from app.services.keyword_service import keywords_to_json, json_to_keywords


# --- Contract Shape Constants ---
# These mirror the frontend TypeScript interfaces exactly.
# If you change these, you MUST update the frontend interfaces too.

KEYWORD_REQUIRED_FIELDS = {"text", "priority", "category"}
KEYWORD_OPTIONAL_FIELDS = {"pattern_boosted"}
KEYWORD_ALL_FIELDS = KEYWORD_REQUIRED_FIELDS | KEYWORD_OPTIONAL_FIELDS

EXTRACTION_RESPONSE_REQUIRED_FIELDS = {
    "application_id", "keywords", "status", "patterns_applied", "pattern_count"
}


class TestKeywordSerializationContract:
    """Verify serialized keyword JSON matches frontend Keyword interface."""

    def test_serialized_keyword_contains_all_contract_fields(self):
        """Keywords stored in DB must contain all fields the frontend expects."""
        keyword = Keyword(
            text="Python",
            priority=9,
            category=KeywordCategory.TECHNICAL_SKILL,
            pattern_boosted=True,
        )
        keyword_list = KeywordList(keywords=[keyword])
        json_str = keywords_to_json(keyword_list)
        data = json.loads(json_str)

        kw = data[0]
        # All contract fields present
        for field in KEYWORD_ALL_FIELDS:
            assert field in kw, f"Missing contract field: {field}"

        # No extra fields that frontend doesn't expect
        assert set(kw.keys()) == KEYWORD_ALL_FIELDS, (
            f"Unexpected fields in serialized keyword: {set(kw.keys()) - KEYWORD_ALL_FIELDS}"
        )

    def test_serialized_keyword_field_types(self):
        """Field types must match frontend TypeScript types."""
        keyword = Keyword(
            text="React",
            priority=8,
            category=KeywordCategory.TOOL,
            pattern_boosted=False,
        )
        keyword_list = KeywordList(keywords=[keyword])
        json_str = keywords_to_json(keyword_list)
        data = json.loads(json_str)

        kw = data[0]
        assert isinstance(kw["text"], str), "text must be string"
        assert isinstance(kw["priority"], int), "priority must be number (int)"
        assert isinstance(kw["category"], str), "category must be string"
        assert isinstance(kw["pattern_boosted"], bool), "pattern_boosted must be boolean"

    def test_category_serializes_as_string_value(self):
        """Category enum must serialize as its string value, not enum name."""
        keyword = Keyword(text="AWS", priority=7, category=KeywordCategory.TOOL)
        keyword_list = KeywordList(keywords=[keyword])
        json_str = keywords_to_json(keyword_list)
        data = json.loads(json_str)

        # Frontend expects lowercase snake_case string values
        assert data[0]["category"] == "tool"
        assert not data[0]["category"].startswith("KeywordCategory")

    def test_pattern_boosted_defaults_to_false(self):
        """Keywords without explicit pattern_boosted must serialize as false."""
        keyword = Keyword(text="Python", priority=9)
        keyword_list = KeywordList(keywords=[keyword])
        json_str = keywords_to_json(keyword_list)
        data = json.loads(json_str)

        assert data[0]["pattern_boosted"] is False

    def test_roundtrip_preserves_all_fields(self):
        """Serialize -> deserialize must preserve all contract fields."""
        original = Keyword(
            text="Docker",
            priority=6,
            category=KeywordCategory.TOOL,
            pattern_boosted=True,
        )
        keyword_list = KeywordList(keywords=[original])
        json_str = keywords_to_json(keyword_list)
        restored = json_to_keywords(json_str)

        restored_kw = restored.keywords[0]
        assert restored_kw.text == original.text
        assert restored_kw.priority == original.priority
        assert restored_kw.category == original.category
        assert restored_kw.pattern_boosted == original.pattern_boosted


class TestKeywordExtractionResponseContract:
    """Verify extraction endpoint response matches frontend KeywordExtractionResponse."""

    def test_response_model_has_all_contract_fields(self):
        """KeywordExtractionResponse must contain all fields frontend expects."""
        response = KeywordExtractionResponse(
            application_id=1,
            keywords=[
                Keyword(text="Python", priority=9, category=KeywordCategory.TECHNICAL_SKILL),
            ],
            status="keywords",
            patterns_applied=False,
            pattern_count=0,
        )
        data = response.model_dump()

        for field in EXTRACTION_RESPONSE_REQUIRED_FIELDS:
            assert field in data, f"Missing contract field: {field}"

    def test_response_model_field_types(self):
        """Response field types must match frontend TypeScript types."""
        response = KeywordExtractionResponse(
            application_id=1,
            keywords=[
                Keyword(text="Python", priority=9, pattern_boosted=True),
            ],
            status="keywords",
            patterns_applied=True,
            pattern_count=3,
        )
        # Serialize as JSON (mimics FastAPI response serialization)
        data = json.loads(response.model_dump_json())

        assert isinstance(data["application_id"], int)
        assert isinstance(data["keywords"], list)
        assert isinstance(data["status"], str)
        assert isinstance(data["patterns_applied"], bool)
        assert isinstance(data["pattern_count"], int)

        # Verify nested keyword shape
        kw = data["keywords"][0]
        for field in KEYWORD_REQUIRED_FIELDS:
            assert field in kw, f"Nested keyword missing field: {field}"

    def test_response_json_serialization_matches_frontend(self):
        """JSON serialization must produce exact shape frontend parses."""
        response = KeywordExtractionResponse(
            application_id=42,
            keywords=[
                Keyword(
                    text="Kubernetes",
                    priority=8,
                    category=KeywordCategory.TOOL,
                    pattern_boosted=True,
                ),
            ],
            status="keywords",
            patterns_applied=True,
            pattern_count=5,
        )
        data = json.loads(response.model_dump_json())

        # Exact shape check
        assert data["application_id"] == 42
        assert data["status"] == "keywords"
        assert data["patterns_applied"] is True
        assert data["pattern_count"] == 5
        assert len(data["keywords"]) == 1

        kw = data["keywords"][0]
        assert kw["text"] == "Kubernetes"
        assert kw["priority"] == 8
        assert kw["category"] == "tool"
        assert kw["pattern_boosted"] is True


@pytest_asyncio.fixture
async def authenticated_client():
    """Create an authenticated client with a session cookie."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/v1/auth/register", json={
            "username": "contractuser", "password": "TestPass123!"
        })
        await ac.post("/api/v1/auth/login", json={
            "username": "contractuser", "password": "TestPass123!"
        })
        yield ac


@pytest_asyncio.fixture
async def client_with_role(authenticated_client):
    """Create a client with an authenticated session and active role."""
    role_response = await authenticated_client.post("/api/v1/roles", json={"name": "Contract Test Role"})
    role_id = role_response.json()["id"]
    authenticated_client.headers["X-Role-Id"] = str(role_id)
    return authenticated_client, role_id


class TestKeywordExtractionEndpointContract:
    """Integration test: actual endpoint response matches frontend contract."""

    @pytest.mark.asyncio
    @patch('app.services.keyword_service.get_llm_provider')
    async def test_extraction_response_shape_matches_frontend_contract(
        self, mock_get_provider, client_with_role
    ):
        """The actual HTTP response must contain all fields the frontend expects."""
        mock_response_json = json.dumps({
            "keywords": [
                {"text": "Python", "priority": 9, "category": "technical_skill"},
                {"text": "Leadership", "priority": 7, "category": "soft_skill"},
            ]
        })
        mock_provider = AsyncMock()
        mock_provider.generate.return_value = MagicMock(content=mock_response_json)
        mock_get_provider.return_value = mock_provider

        client, role_id = client_with_role

        # Create application
        app_response = await client.post("/api/v1/applications", json={
            "company_name": "Contract Test Corp",
            "job_posting": "We need a Senior Developer with Python and leadership skills.",
        })
        app_id = app_response.json()["id"]

        # Extract keywords
        response = await client.post(f"/api/v1/applications/{app_id}/keywords/extract")
        assert response.status_code == 200
        data = response.json()

        # Validate top-level response fields
        for field in EXTRACTION_RESPONSE_REQUIRED_FIELDS:
            assert field in data, f"Response missing contract field: {field}"

        assert isinstance(data["application_id"], int)
        assert isinstance(data["keywords"], list)
        assert isinstance(data["status"], str)
        assert isinstance(data["patterns_applied"], bool)
        assert isinstance(data["pattern_count"], int)

        # Validate each keyword matches Keyword interface
        for kw in data["keywords"]:
            assert isinstance(kw["text"], str), f"keyword.text must be string, got {type(kw['text'])}"
            assert isinstance(kw["priority"], int), f"keyword.priority must be int, got {type(kw['priority'])}"
            assert isinstance(kw["category"], str), f"keyword.category must be string, got {type(kw['category'])}"
            assert isinstance(kw["pattern_boosted"], bool), (
                f"keyword.pattern_boosted must be bool, got {type(kw['pattern_boosted'])}"
            )

    @pytest.mark.asyncio
    @patch('app.services.keyword_service.get_llm_provider')
    async def test_stored_keywords_match_frontend_parsing(
        self, mock_get_provider, client_with_role
    ):
        """Keywords stored in application.keywords JSON must be parseable by frontend."""
        mock_response_json = json.dumps({
            "keywords": [
                {"text": "React", "priority": 8, "category": "technical_skill"},
            ]
        })
        mock_provider = AsyncMock()
        mock_provider.generate.return_value = MagicMock(content=mock_response_json)
        mock_get_provider.return_value = mock_provider

        client, role_id = client_with_role

        app_response = await client.post("/api/v1/applications", json={
            "company_name": "Storage Test Corp",
            "job_posting": "We need a React developer.",
        })
        app_id = app_response.json()["id"]

        # Extract keywords (stores in DB)
        await client.post(f"/api/v1/applications/{app_id}/keywords/extract")

        # Fetch application (frontend's code path: getApplication -> JSON.parse(keywords))
        get_response = await client.get(f"/api/v1/applications/{app_id}")
        app_data = get_response.json()

        # Frontend does: JSON.parse(application.keywords) -> Keyword[]
        keywords_json = app_data["keywords"]
        assert keywords_json is not None
        parsed_keywords = json.loads(keywords_json)

        assert isinstance(parsed_keywords, list)
        for kw in parsed_keywords:
            for field in KEYWORD_REQUIRED_FIELDS:
                assert field in kw, f"Stored keyword missing contract field: {field}"
            assert isinstance(kw["text"], str)
            assert isinstance(kw["priority"], int)
            assert isinstance(kw["category"], str)
