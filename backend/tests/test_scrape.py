"""Tests for scrape endpoint and service."""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.scrape_service import _extract_text_from_response, scrape_job_posting
from app.utils.url_validator import validate_url


@pytest_asyncio.fixture
async def client():
    """Async test client for FastAPI."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def authenticated_client(client):
    """Create client with authenticated session."""
    await client.post(
        "/api/v1/auth/register",
        json={"username": "scrapeuser", "password": "testpass123"},
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "scrapeuser", "password": "testpass123"},
    )
    client.cookies = login_response.cookies
    return client


class TestScrapeEndpoint:
    """Tests for POST /api/v1/scrape/job-posting endpoint."""

    @pytest.mark.asyncio
    async def test_scrape_requires_authentication(self, client):
        response = await client.post(
            "/api/v1/scrape/job-posting",
            json={"url": "https://example.com/job"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_scrape_validates_url_format(self, authenticated_client):
        response = await authenticated_client.post(
            "/api/v1/scrape/job-posting",
            json={"url": "not-a-valid-url"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    @patch("app.api.v1.scrape.scrape_job_posting", new_callable=AsyncMock)
    async def test_scrape_returns_content_on_success(
        self, mock_scrape, authenticated_client
    ):
        """Contract test: mock scrape service, test endpoint contract."""
        mock_scrape.return_value = "Senior Product Manager at Acme Corp..."

        response = await authenticated_client.post(
            "/api/v1/scrape/job-posting",
            json={"url": "https://example.com/job"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert data["content"] == "Senior Product Manager at Acme Corp..."
        assert data["url"] == "https://example.com/job"

    @pytest.mark.asyncio
    async def test_scrape_missing_url_field(self, authenticated_client):
        response = await authenticated_client.post(
            "/api/v1/scrape/job-posting",
            json={},
        )
        assert response.status_code == 422


class TestExtractTextFromResponse:
    """Tests for _extract_text_from_response helper."""

    def test_handles_code_blocks_with_language(self):
        wrapped = "```text\nJob description here\n```"
        assert _extract_text_from_response(wrapped) == "Job description here"

    def test_handles_code_blocks_without_language(self):
        wrapped = "```\nJob description here\n```"
        assert _extract_text_from_response(wrapped) == "Job description here"

    def test_handles_json_code_blocks(self):
        json_wrapped = '```json\n{"text": "content"}\n```'
        assert '"text": "content"' in _extract_text_from_response(json_wrapped)

    def test_handles_plain_text(self):
        plain = "Job description here"
        assert _extract_text_from_response(plain) == "Job description here"

    def test_handles_empty_string(self):
        assert _extract_text_from_response("") == ""

    def test_handles_none(self):
        assert _extract_text_from_response(None) == ""

    def test_strips_whitespace(self):
        assert _extract_text_from_response("  text  ") == "text"


class TestUrlValidator:
    """Tests for SSRF protection in URL validation."""

    def test_allows_valid_https_url(self):
        is_valid, error = validate_url("https://example.com/job")
        assert is_valid is True
        assert error is None

    def test_allows_valid_http_url(self):
        is_valid, error = validate_url("http://example.com/job")
        assert is_valid is True
        assert error is None

    def test_blocks_localhost(self):
        is_valid, error = validate_url("http://localhost/admin")
        assert is_valid is False
        assert "localhost" in error.lower()

    def test_blocks_127_0_0_1(self):
        is_valid, error = validate_url("http://127.0.0.1/admin")
        assert is_valid is False
        assert "private" in error.lower() or "internal" in error.lower()

    def test_blocks_private_ip_10(self):
        is_valid, error = validate_url("http://10.0.0.1/internal")
        assert is_valid is False

    def test_blocks_private_ip_192_168(self):
        is_valid, error = validate_url("http://192.168.1.1/router")
        assert is_valid is False

    def test_blocks_private_ip_172_16(self):
        is_valid, error = validate_url("http://172.16.0.1/internal")
        assert is_valid is False

    def test_blocks_link_local(self):
        is_valid, error = validate_url("http://169.254.169.254/metadata")
        assert is_valid is False

    def test_blocks_ftp_scheme(self):
        is_valid, error = validate_url("ftp://example.com/file")
        assert is_valid is False
        assert "http" in error.lower()

    def test_blocks_file_scheme(self):
        is_valid, error = validate_url("file:///etc/passwd")
        assert is_valid is False

    def test_blocks_empty_hostname(self):
        is_valid, error = validate_url("http:///path")
        assert is_valid is False

    def test_blocks_zero_ip(self):
        is_valid, error = validate_url("http://0.0.0.0/admin")
        assert is_valid is False


class TestScrapeService:
    """Tests for scrape_job_posting service function."""

    @pytest.mark.asyncio
    @patch("app.services.scrape_service.validate_url", return_value=(True, None))
    @patch("app.services.scrape_service._fetch_page_content", new_callable=AsyncMock)
    async def test_scrape_timeout_raises_408(self, mock_fetch, _mock_validate):
        """Test that timeout raises HTTPException with 408 status."""
        mock_fetch.side_effect = asyncio.TimeoutError()

        with pytest.raises(HTTPException) as exc_info:
            await scrape_job_posting("https://example.com/job")

        assert exc_info.value.status_code == 408
        assert "timed out" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.services.scrape_service.validate_url", return_value=(True, None))
    @patch("app.services.scrape_service._fetch_page_content", new_callable=AsyncMock)
    async def test_scrape_short_content_raises_422(self, mock_fetch, _mock_validate):
        """Test that too-short page content raises 422."""
        mock_fetch.return_value = "Short"

        with pytest.raises(HTTPException) as exc_info:
            await scrape_job_posting("https://example.com/job")

        assert exc_info.value.status_code == 422
        assert "too short" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.services.scrape_service.validate_url", return_value=(True, None))
    @patch("app.services.scrape_service._fetch_page_content", new_callable=AsyncMock)
    async def test_scrape_fetch_exception_raises_422(self, mock_fetch, _mock_validate):
        """Test that fetch exceptions raise 422 with helpful message."""
        mock_fetch.side_effect = Exception("Connection refused")

        with pytest.raises(HTTPException) as exc_info:
            await scrape_job_posting("https://example.com/job")

        assert exc_info.value.status_code == 422
        assert "Failed to fetch URL" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.services.scrape_service.validate_url", return_value=(True, None))
    @patch("app.services.scrape_service.get_llm_provider")
    @patch("app.services.scrape_service._fetch_page_content", new_callable=AsyncMock)
    async def test_scrape_successful_extraction(self, mock_fetch, mock_provider, _mock_validate):
        """Test successful page fetch and LLM extraction."""
        mock_fetch.return_value = "A" * 100  # Content long enough

        mock_response = AsyncMock()
        mock_response.content = "Extracted job description text that is long enough for validation"
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = mock_response
        mock_provider.return_value = mock_llm

        result = await scrape_job_posting("https://example.com/job")
        assert result == "Extracted job description text that is long enough for validation"

    @pytest.mark.asyncio
    @patch("app.services.scrape_service.validate_url", return_value=(True, None))
    @patch("app.services.scrape_service.get_llm_provider")
    @patch("app.services.scrape_service._fetch_page_content", new_callable=AsyncMock)
    async def test_scrape_llm_returns_short_content_raises_422(self, mock_fetch, mock_provider, _mock_validate):
        """Test that short LLM extraction result raises 422."""
        mock_fetch.return_value = "A" * 100

        mock_response = AsyncMock()
        mock_response.content = "Short"
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = mock_response
        mock_provider.return_value = mock_llm

        with pytest.raises(HTTPException) as exc_info:
            await scrape_job_posting("https://example.com/job")

        assert exc_info.value.status_code == 422
        assert "Could not extract" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.services.scrape_service.validate_url", return_value=(True, None))
    @patch("app.services.scrape_service.get_llm_provider")
    @patch("app.services.scrape_service._fetch_page_content", new_callable=AsyncMock)
    async def test_scrape_falls_back_to_raw_content_on_llm_failure(self, mock_fetch, mock_provider, _mock_validate):
        """Test that LLM failure returns raw content as fallback."""
        raw = "A" * 200
        mock_fetch.return_value = raw

        mock_llm = AsyncMock()
        mock_llm.generate.side_effect = Exception("LLM API timeout")
        mock_provider.return_value = mock_llm

        result = await scrape_job_posting("https://example.com/job")
        assert result == raw.strip()

    @pytest.mark.asyncio
    async def test_scrape_blocks_internal_url(self):
        """Test that SSRF protection blocks internal URLs."""
        with pytest.raises(HTTPException) as exc_info:
            await scrape_job_posting("http://localhost:8000/api/health")

        assert exc_info.value.status_code == 422
        assert "localhost" in exc_info.value.detail.lower()
