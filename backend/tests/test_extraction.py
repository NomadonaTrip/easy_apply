"""Tests for skill and accomplishment extraction from resumes."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.database import async_session_maker
from app.models.user import User
from app.models.role import Role


@pytest_asyncio.fixture
async def client():
    """Async test client for FastAPI."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def authenticated_client_with_role(client):
    """Create client with authenticated session and a role."""
    await client.post(
        "/api/v1/auth/register",
        json={"username": "extractuser", "password": "password123"}
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "extractuser", "password": "password123"}
    )
    client.cookies = login_response.cookies

    role_response = await client.post(
        "/api/v1/roles",
        json={"name": "Software Engineer"}
    )
    role_id = role_response.json()["id"]
    return client, role_id


@pytest_asyncio.fixture
async def user_and_role():
    """Create a user and role for testing."""
    async with async_session_maker() as session:
        user = User(
            username="extract_test",
            password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        role = Role(user_id=user.id, name="Developer")
        session.add(role)
        await session.commit()
        await session.refresh(role)
        role_id = role.id

    return role_id


# ============================================================================
# Task 1: Document Parser Tests
# ============================================================================

class TestDocumentParser:
    """Tests for the document parsing utilities."""

    @pytest.mark.asyncio
    async def test_extract_text_from_pdf(self, tmp_path):
        """Test extracting text from a PDF file."""
        from app.utils.document_parser import extract_text_from_pdf

        # Create a simple PDF (using pypdf structure)
        pdf_path = tmp_path / "test.pdf"

        # We'll mock pypdf since creating real PDFs is complex
        with patch('app.utils.document_parser.PdfReader') as mock_reader:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "John Doe\nSoftware Engineer\nPython, JavaScript"
            mock_reader.return_value.pages = [mock_page]

            result = extract_text_from_pdf(str(pdf_path))

            assert "John Doe" in result
            assert "Software Engineer" in result
            assert "Python" in result

    @pytest.mark.asyncio
    async def test_extract_text_from_docx(self, tmp_path):
        """Test extracting text from a DOCX file."""
        from app.utils.document_parser import extract_text_from_docx

        docx_path = tmp_path / "test.docx"

        with patch('app.utils.document_parser.Document') as mock_doc:
            mock_para1 = MagicMock()
            mock_para1.text = "Jane Smith"
            mock_para2 = MagicMock()
            mock_para2.text = "Data Scientist"
            mock_para3 = MagicMock()
            mock_para3.text = "Machine Learning, SQL"
            mock_doc.return_value.paragraphs = [mock_para1, mock_para2, mock_para3]

            result = extract_text_from_docx(str(docx_path))

            assert "Jane Smith" in result
            assert "Data Scientist" in result
            assert "Machine Learning" in result

    @pytest.mark.asyncio
    async def test_extract_text_dispatches_correctly(self, tmp_path):
        """Test that extract_text dispatches to correct parser based on file type."""
        from app.utils.document_parser import extract_text

        with patch('app.utils.document_parser.extract_text_from_pdf') as mock_pdf, \
             patch('app.utils.document_parser.extract_text_from_docx') as mock_docx:
            mock_pdf.return_value = "PDF content"
            mock_docx.return_value = "DOCX content"

            # Test PDF dispatch
            pdf_result = extract_text("test.pdf", "pdf")
            mock_pdf.assert_called_once()
            assert pdf_result == "PDF content"

            # Test DOCX dispatch
            docx_result = extract_text("test.docx", "docx")
            mock_docx.assert_called_once()
            assert docx_result == "DOCX content"

    @pytest.mark.asyncio
    async def test_extract_text_invalid_type(self):
        """Test that extract_text raises error for unsupported file types."""
        from app.utils.document_parser import extract_text

        with pytest.raises(ValueError, match="Unsupported file type"):
            extract_text("test.txt", "txt")


# ============================================================================
# Task 1: Extraction Service Tests
# ============================================================================

class TestExtractionService:
    """Tests for the extraction service."""

    @pytest.mark.asyncio
    async def test_extract_skills_with_llm(self):
        """Test that LLM skill extraction returns structured data."""
        from app.services.extraction_service import extract_skills_with_llm

        resume_text = """
        John Doe
        Software Engineer

        Skills: Python, JavaScript, React, SQL, AWS
        Experience: 5 years in software development
        """

        # Mock the LLM provider
        mock_response = MagicMock()
        mock_response.content = '{"skills": [{"name": "Python", "category": "Programming"}, {"name": "JavaScript", "category": "Programming"}, {"name": "React", "category": "Frontend"}, {"name": "SQL", "category": "Database"}, {"name": "AWS", "category": "Cloud"}]}'

        with patch('app.services.extraction_service.get_llm_provider') as mock_provider:
            mock_provider.return_value.generate = AsyncMock(return_value=mock_response)

            skills = await extract_skills_with_llm(resume_text)

            assert len(skills) == 5
            assert any(s["name"] == "Python" for s in skills)
            assert any(s["name"] == "AWS" for s in skills)

    @pytest.mark.asyncio
    async def test_extract_accomplishments_with_llm(self):
        """Test that LLM accomplishment extraction returns structured data."""
        from app.services.extraction_service import extract_accomplishments_with_llm

        resume_text = """
        Senior Engineer at TechCorp
        - Led migration to microservices, reducing deployment time by 60%
        - Grew team from 3 to 12 engineers while maintaining velocity
        """

        mock_response = MagicMock()
        mock_response.content = '{"accomplishments": [{"description": "Led migration to microservices, reducing deployment time by 60%", "context": "Senior Engineer at TechCorp"}, {"description": "Grew team from 3 to 12 engineers while maintaining velocity", "context": "Senior Engineer at TechCorp"}]}'

        with patch('app.services.extraction_service.get_llm_provider') as mock_provider:
            mock_provider.return_value.generate = AsyncMock(return_value=mock_response)

            accomplishments = await extract_accomplishments_with_llm(resume_text)

            assert len(accomplishments) == 2
            assert any("microservices" in a["description"] for a in accomplishments)

    @pytest.mark.asyncio
    async def test_extract_skills_handles_invalid_json(self):
        """Test that skill extraction handles invalid JSON gracefully."""
        from app.services.extraction_service import extract_skills_with_llm

        mock_response = MagicMock()
        mock_response.content = "This is not valid JSON"

        with patch('app.services.extraction_service.get_llm_provider') as mock_provider:
            mock_provider.return_value.generate = AsyncMock(return_value=mock_response)

            skills = await extract_skills_with_llm("Some resume text")

            # Should return empty list on parse failure
            assert skills == []

    @pytest.mark.asyncio
    async def test_add_skill_if_not_exists_adds_new(self, user_and_role):
        """Test that new skills are added."""
        from app.services.extraction_service import add_skill_if_not_exists
        from app.services import experience_service

        role_id = user_and_role

        # First skill should be added
        added = await add_skill_if_not_exists(
            role_id, name="Python", category="Programming", source="resume"
        )
        assert added is True

        # Verify skill exists
        skills = await experience_service.get_skills(role_id)
        assert len(skills) == 1
        assert skills[0].name == "Python"

    @pytest.mark.asyncio
    async def test_add_skill_if_not_exists_deduplicates(self, user_and_role):
        """Test that duplicate skills are not added (AC #5)."""
        from app.services.extraction_service import add_skill_if_not_exists
        from app.services import experience_service

        role_id = user_and_role

        # Add first skill
        added1 = await add_skill_if_not_exists(role_id, name="Python", source="resume")
        assert added1 is True

        # Try to add same skill again (should be deduplicated)
        added2 = await add_skill_if_not_exists(role_id, name="Python", source="resume")
        assert added2 is False

        # Try with different case (should still be deduplicated)
        added3 = await add_skill_if_not_exists(role_id, name="PYTHON", source="resume")
        assert added3 is False

        # Try with whitespace (should still be deduplicated)
        added4 = await add_skill_if_not_exists(role_id, name="  python  ", source="resume")
        assert added4 is False

        # Verify only one skill exists
        skills = await experience_service.get_skills(role_id)
        assert len(skills) == 1

    @pytest.mark.asyncio
    async def test_extract_from_resume_full_flow(self, user_and_role, tmp_path, monkeypatch):
        """Test full extraction flow from a resume."""
        from app.services.extraction_service import extract_from_resume
        from app.services import resume_service, experience_service

        role_id = user_and_role

        # Setup mock upload directory
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir(parents=True)
        monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", upload_dir)

        # Create a mock resume in the database
        resume = await resume_service.create_resume(
            role_id=role_id,
            filename="test_resume.pdf",
            file_type="pdf",
            file_path="uploads/1/test.pdf",
            file_size=1024
        )

        # Mock document parsing and LLM calls
        with patch('app.services.extraction_service.extract_text') as mock_extract, \
             patch('app.services.extraction_service.extract_skills_with_llm') as mock_skills, \
             patch('app.services.extraction_service.extract_accomplishments_with_llm') as mock_acc:

            mock_extract.return_value = "John Doe, Software Engineer, Python"
            mock_skills.return_value = [
                {"name": "Python", "category": "Programming"},
                {"name": "FastAPI", "category": "Framework"}
            ]
            mock_acc.return_value = [
                {"description": "Built scalable API", "context": "Lead Engineer"}
            ]

            result = await extract_from_resume(resume.id, role_id)

            # Verify result counts
            assert result["skills_count"] == 2
            assert result["accomplishments_count"] == 1

            # Verify skills were stored
            skills = await experience_service.get_skills(role_id)
            assert len(skills) == 2

            # Verify accomplishments were stored
            accomplishments = await experience_service.get_accomplishments(role_id)
            assert len(accomplishments) == 1

            # Verify resume marked as processed
            updated_resume = await resume_service.get_resume(resume.id, role_id)
            assert updated_resume.processed is True

    @pytest.mark.asyncio
    async def test_extract_from_resume_stores_structured_fields(self, user_and_role, tmp_path, monkeypatch):
        """Structured company_name, role_title, dates are stored when present."""
        from app.services.extraction_service import extract_from_resume
        from app.services import resume_service, experience_service

        role_id = user_and_role

        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir(parents=True)
        monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", upload_dir)

        resume = await resume_service.create_resume(
            role_id=role_id,
            filename="structured.pdf",
            file_type="pdf",
            file_path="uploads/1/structured.pdf",
            file_size=1024
        )

        with patch('app.services.extraction_service.extract_text') as mock_extract, \
             patch('app.services.extraction_service.extract_skills_with_llm') as mock_skills, \
             patch('app.services.extraction_service.extract_accomplishments_with_llm') as mock_acc:

            mock_extract.return_value = "Jane Doe, Senior Engineer at TechCorp"
            mock_skills.return_value = []
            mock_acc.return_value = [
                {
                    "description": "Led API migration reducing latency by 40%",
                    "context": "Senior Engineer at TechCorp",
                    "company_name": "TechCorp",
                    "role_title": "Senior Engineer",
                    "dates": "2020-2024",
                }
            ]

            await extract_from_resume(resume.id, role_id)

        accomplishments = await experience_service.get_accomplishments(role_id)
        assert len(accomplishments) == 1
        acc = accomplishments[0]
        assert acc.company_name == "TechCorp"
        assert acc.role_title == "Senior Engineer"
        assert acc.dates == "2020-2024"
        assert acc.context == "Senior Engineer at TechCorp"

    @pytest.mark.asyncio
    async def test_extract_from_resume_handles_missing_structured_fields(self, user_and_role, tmp_path, monkeypatch):
        """Accomplishments without structured fields store None (backward compat)."""
        from app.services.extraction_service import extract_from_resume
        from app.services import resume_service, experience_service

        role_id = user_and_role

        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir(parents=True)
        monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", upload_dir)

        resume = await resume_service.create_resume(
            role_id=role_id,
            filename="legacy.pdf",
            file_type="pdf",
            file_path="uploads/1/legacy.pdf",
            file_size=1024
        )

        with patch('app.services.extraction_service.extract_text') as mock_extract, \
             patch('app.services.extraction_service.extract_skills_with_llm') as mock_skills, \
             patch('app.services.extraction_service.extract_accomplishments_with_llm') as mock_acc:

            mock_extract.return_value = "John Doe, Software Engineer"
            mock_skills.return_value = []
            mock_acc.return_value = [
                {"description": "Built scalable API", "context": "Lead Engineer"}
            ]

            await extract_from_resume(resume.id, role_id)

        accomplishments = await experience_service.get_accomplishments(role_id)
        assert len(accomplishments) == 1
        acc = accomplishments[0]
        assert acc.company_name is None
        assert acc.role_title is None
        assert acc.dates is None
        assert acc.context == "Lead Engineer"

    @pytest.mark.asyncio
    async def test_extract_from_resume_not_found(self, user_and_role):
        """Test extraction fails gracefully for non-existent resume."""
        from app.services.extraction_service import extract_from_resume

        role_id = user_and_role

        with pytest.raises(ValueError, match="Resume not found"):
            await extract_from_resume(99999, role_id)

    @pytest.mark.asyncio
    async def test_extract_all_unprocessed(self, user_and_role, tmp_path, monkeypatch):
        """Test extracting from all unprocessed resumes."""
        from app.services.extraction_service import extract_all_unprocessed
        from app.services import resume_service

        role_id = user_and_role

        # Create two unprocessed resumes
        await resume_service.create_resume(
            role_id=role_id, filename="r1.pdf", file_type="pdf",
            file_path="uploads/1/r1.pdf", file_size=1000
        )
        await resume_service.create_resume(
            role_id=role_id, filename="r2.pdf", file_type="pdf",
            file_path="uploads/1/r2.pdf", file_size=2000
        )

        with patch('app.services.extraction_service.extract_from_resume') as mock_extract:
            mock_extract.return_value = {
                "skills_count": 3,
                "accomplishments_count": 2
            }

            result = await extract_all_unprocessed(role_id)

            assert result["resumes_processed"] == 2
            assert result["total_skills"] == 6  # 3 per resume
            assert result["total_accomplishments"] == 4  # 2 per resume


# ============================================================================
# Task 3: API Endpoint Tests
# ============================================================================

class TestExtractionAPI:
    """Tests for the extraction API endpoints."""

    @pytest.mark.asyncio
    async def test_extract_single_resume_endpoint(
        self, authenticated_client_with_role, tmp_path, monkeypatch
    ):
        """Test POST /resumes/{id}/extract endpoint."""
        client, role_id = authenticated_client_with_role

        monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", tmp_path / "uploads")

        # Upload a resume first
        upload_response = await client.post(
            "/api/v1/resumes/upload",
            files={"file": ("test.pdf", b"PDF content", "application/pdf")},
            headers={"X-Role-Id": str(role_id)}
        )
        resume_id = upload_response.json()["id"]

        # Mock the extraction
        with patch('app.services.extraction_service.extract_from_resume') as mock_extract:
            mock_extract.return_value = {
                "skills_count": 5,
                "accomplishments_count": 3
            }

            response = await client.post(
                f"/api/v1/resumes/{resume_id}/extract",
                headers={"X-Role-Id": str(role_id)}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["skills_count"] == 5
            assert data["accomplishments_count"] == 3
            assert "5 skills identified" in data["message"]
            assert "3 accomplishments extracted" in data["message"]

    @pytest.mark.asyncio
    async def test_extract_single_resume_not_found(self, authenticated_client_with_role):
        """Test extract endpoint returns 404 for non-existent resume."""
        client, role_id = authenticated_client_with_role

        response = await client.post(
            "/api/v1/resumes/99999/extract",
            headers={"X-Role-Id": str(role_id)}
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_extract_all_resumes_endpoint(
        self, authenticated_client_with_role, tmp_path, monkeypatch
    ):
        """Test POST /resumes/extract-all endpoint."""
        client, role_id = authenticated_client_with_role

        monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", tmp_path / "uploads")

        # Upload two resumes
        await client.post(
            "/api/v1/resumes/upload",
            files={"file": ("r1.pdf", b"PDF 1", "application/pdf")},
            headers={"X-Role-Id": str(role_id)}
        )
        await client.post(
            "/api/v1/resumes/upload",
            files={"file": ("r2.pdf", b"PDF 2", "application/pdf")},
            headers={"X-Role-Id": str(role_id)}
        )

        with patch('app.services.extraction_service.extract_all_unprocessed') as mock_extract:
            mock_extract.return_value = {
                "resumes_processed": 2,
                "total_skills": 10,
                "total_accomplishments": 5
            }

            response = await client.post(
                "/api/v1/resumes/extract-all",
                headers={"X-Role-Id": str(role_id)}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["resumes_processed"] == 2
            assert data["total_skills"] == 10
            assert data["total_accomplishments"] == 5

    @pytest.mark.asyncio
    async def test_extract_requires_auth(self, client):
        """Test that extraction requires authentication."""
        response = await client.post(
            "/api/v1/resumes/1/extract",
            headers={"X-Role-Id": "1"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_extract_requires_role_header(self, authenticated_client_with_role):
        """Test that extraction requires X-Role-Id header."""
        client, role_id = authenticated_client_with_role

        # No X-Role-Id header
        response = await client.post("/api/v1/resumes/1/extract")
        assert response.status_code == 400


# ============================================================================
# Task 4: Deduplication Tests
# ============================================================================

class TestDeduplication:
    """Tests for skill deduplication across multiple resumes (AC #5)."""

    @pytest.mark.asyncio
    async def test_skills_deduplicated_across_resumes(self, user_and_role, tmp_path, monkeypatch):
        """Test that skills from multiple resumes are deduplicated."""
        from app.services.extraction_service import extract_from_resume
        from app.services import resume_service, experience_service

        role_id = user_and_role

        # Create two resumes
        resume1 = await resume_service.create_resume(
            role_id=role_id, filename="r1.pdf", file_type="pdf",
            file_path="uploads/1/r1.pdf", file_size=1000
        )
        resume2 = await resume_service.create_resume(
            role_id=role_id, filename="r2.pdf", file_type="pdf",
            file_path="uploads/1/r2.pdf", file_size=2000
        )

        # Both resumes have overlapping skills
        with patch('app.services.extraction_service.extract_text') as mock_extract, \
             patch('app.services.extraction_service.extract_skills_with_llm') as mock_skills, \
             patch('app.services.extraction_service.extract_accomplishments_with_llm') as mock_acc:

            mock_extract.return_value = "Resume text"
            mock_acc.return_value = []

            # First resume: Python, JavaScript
            mock_skills.return_value = [
                {"name": "Python", "category": "Programming"},
                {"name": "JavaScript", "category": "Programming"}
            ]
            await extract_from_resume(resume1.id, role_id)

            # Second resume: Python (duplicate), React (new)
            mock_skills.return_value = [
                {"name": "Python", "category": "Programming"},  # Duplicate
                {"name": "React", "category": "Frontend"}  # New
            ]
            await extract_from_resume(resume2.id, role_id)

            # Should have 3 unique skills, not 4
            skills = await experience_service.get_skills(role_id)
            skill_names = [s.name for s in skills]
            assert len(skills) == 3
            assert "Python" in skill_names
            assert "JavaScript" in skill_names
            assert "React" in skill_names
