"""Tests for resume upload functionality."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlmodel import select

from app.main import app
from app.database import async_session_maker
from app.models.resume import Resume


# Database cleanup is handled by conftest.py's clean_database fixture


@pytest_asyncio.fixture
async def client():
    """Async test client for FastAPI."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def authenticated_client(client):
    """Create client with authenticated session."""
    await client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "password123"}
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "password123"}
    )
    client.cookies = login_response.cookies
    return client


@pytest_asyncio.fixture
async def authenticated_client_with_role(authenticated_client):
    """Create client with authenticated session and a role."""
    role_response = await authenticated_client.post(
        "/api/v1/roles",
        json={"name": "Test Developer"}
    )
    role_id = role_response.json()["id"]
    return authenticated_client, role_id


# Test Resume Model (Task 1)

@pytest.mark.asyncio
async def test_resume_model_exists():
    """Test that Resume model can be imported and has expected fields."""
    from app.models.resume import Resume, ResumeCreate, ResumeRead

    # Verify Resume table model has expected attributes
    assert hasattr(Resume, "id")
    assert hasattr(Resume, "role_id")
    assert hasattr(Resume, "filename")
    assert hasattr(Resume, "file_path")
    assert hasattr(Resume, "file_type")
    assert hasattr(Resume, "file_size")
    assert hasattr(Resume, "uploaded_at")
    assert hasattr(Resume, "processed")


@pytest.mark.asyncio
async def test_resume_create_schema():
    """Test ResumeCreate schema fields."""
    from app.models.resume import ResumeCreate

    # Should be able to create with valid data
    data = ResumeCreate(
        filename="resume.pdf",
        file_type="pdf",
        file_size=1024,
        file_path="uploads/1/abc123.pdf"
    )
    assert data.filename == "resume.pdf"
    assert data.file_type == "pdf"
    assert data.file_size == 1024


@pytest.mark.asyncio
async def test_resume_read_schema():
    """Test ResumeRead schema fields."""
    from app.models.resume import ResumeRead
    from datetime import datetime

    # Should match database model response format
    assert hasattr(ResumeRead, "model_fields")
    fields = ResumeRead.model_fields.keys()
    assert "id" in fields
    assert "role_id" in fields
    assert "filename" in fields
    assert "file_type" in fields
    assert "file_size" in fields
    assert "file_path" in fields
    assert "uploaded_at" in fields
    assert "processed" in fields


@pytest.mark.asyncio
async def test_resume_model_validation_empty_filename():
    """Test Resume model rejects empty filename."""
    from app.models.resume import Resume

    with pytest.raises(ValueError, match="filename cannot be empty"):
        Resume(
            role_id=1,
            filename="",
            file_type="pdf",
            file_size=1024,
            file_path="uploads/1/test.pdf"
        )


@pytest.mark.asyncio
async def test_resume_model_validation_missing_role_id():
    """Test Resume model requires role_id."""
    from app.models.resume import Resume

    with pytest.raises(ValueError, match="role_id is required"):
        Resume(
            role_id=None,
            filename="resume.pdf",
            file_type="pdf",
            file_size=1024,
            file_path="uploads/1/test.pdf"
        )


@pytest.mark.asyncio
async def test_resume_model_validation_invalid_file_type():
    """Test Resume model validates file type."""
    from app.models.resume import Resume

    with pytest.raises(ValueError, match="file_type must be"):
        Resume(
            role_id=1,
            filename="resume.txt",
            file_type="txt",
            file_size=1024,
            file_path="uploads/1/test.txt"
        )


@pytest.mark.asyncio
async def test_resume_database_creation():
    """Test Resume can be created in database."""
    from app.models.resume import Resume
    from app.models.role import Role
    from app.models.user import User

    async with async_session_maker() as session:
        # Create user first
        user = User(
            username="resumetest",
            password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Create role
        role = Role(user_id=user.id, name="Developer")
        session.add(role)
        await session.commit()
        await session.refresh(role)

        # Create resume
        resume = Resume(
            role_id=role.id,
            filename="test_resume.pdf",
            file_type="pdf",
            file_size=2048,
            file_path="uploads/1/unique123.pdf"
        )
        session.add(resume)
        await session.commit()
        await session.refresh(resume)

        # Verify
        assert resume.id is not None
        assert resume.role_id == role.id
        assert resume.filename == "test_resume.pdf"
        assert resume.file_type == "pdf"
        assert resume.file_size == 2048
        assert resume.processed is False
        assert resume.uploaded_at is not None


@pytest.mark.asyncio
async def test_resume_exported_from_models():
    """Test Resume model is exported from models package."""
    from app.models import Resume, ResumeCreate, ResumeRead

    assert Resume is not None
    assert ResumeCreate is not None
    assert ResumeRead is not None


# Test Resume Service (Task 4)

@pytest.mark.asyncio
async def test_resume_service_create():
    """Test resume service can create a resume record."""
    from app.services import resume_service
    from app.models.user import User
    from app.models.role import Role

    # Create user and role first
    async with async_session_maker() as session:
        user = User(
            username="service_test",
            password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        role = Role(user_id=user.id, name="Test Role")
        session.add(role)
        await session.commit()
        await session.refresh(role)
        role_id = role.id

    # Test service create
    resume = await resume_service.create_resume(
        role_id=role_id,
        filename="test.pdf",
        file_type="pdf",
        file_path="uploads/1/test.pdf",
        file_size=1024
    )

    assert resume.id is not None
    assert resume.role_id == role_id
    assert resume.filename == "test.pdf"


@pytest.mark.asyncio
async def test_resume_service_get_resumes():
    """Test resume service can list resumes for a role."""
    from app.services import resume_service
    from app.models.user import User
    from app.models.role import Role

    async with async_session_maker() as session:
        user = User(
            username="list_test",
            password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        role = Role(user_id=user.id, name="List Role")
        session.add(role)
        await session.commit()
        await session.refresh(role)
        role_id = role.id

    # Create two resumes
    await resume_service.create_resume(
        role_id=role_id, filename="r1.pdf", file_type="pdf",
        file_path="uploads/1/r1.pdf", file_size=1000
    )
    await resume_service.create_resume(
        role_id=role_id, filename="r2.docx", file_type="docx",
        file_path="uploads/1/r2.docx", file_size=2000
    )

    resumes = await resume_service.get_resumes(role_id)
    assert len(resumes) == 2


@pytest.mark.asyncio
async def test_resume_service_delete():
    """Test resume service can delete a resume."""
    from app.services import resume_service
    from app.models.user import User
    from app.models.role import Role

    async with async_session_maker() as session:
        user = User(
            username="delete_test",
            password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        role = Role(user_id=user.id, name="Delete Role")
        session.add(role)
        await session.commit()
        await session.refresh(role)
        role_id = role.id

    resume = await resume_service.create_resume(
        role_id=role_id, filename="to_delete.pdf", file_type="pdf",
        file_path="uploads/1/to_delete.pdf", file_size=500
    )

    # Delete should succeed
    result = await resume_service.delete_resume(resume.id, role_id)
    assert result is True

    # Should not exist anymore
    resumes = await resume_service.get_resumes(role_id)
    assert len(resumes) == 0


# Test Resume Upload API (Task 3)

@pytest.mark.asyncio
async def test_upload_resume_success_pdf(authenticated_client_with_role, tmp_path, monkeypatch):
    """Test successful PDF upload via API."""
    client, role_id = authenticated_client_with_role

    # Monkeypatch to use temp directory
    monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", tmp_path / "uploads")

    # Create fake PDF content
    pdf_content = b"%PDF-1.4 fake content"

    response = await client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.pdf", pdf_content, "application/pdf")},
        headers={"X-Role-Id": str(role_id)}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "resume.pdf"
    assert data["file_type"] == "pdf"
    assert data["role_id"] == role_id
    assert data["processed"] is False


@pytest.mark.asyncio
async def test_upload_resume_success_docx(authenticated_client_with_role, tmp_path, monkeypatch):
    """Test successful DOCX upload via API."""
    client, role_id = authenticated_client_with_role

    monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", tmp_path / "uploads")

    docx_content = b"PK fake docx content"

    response = await client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.docx", docx_content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        headers={"X-Role-Id": str(role_id)}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "resume.docx"
    assert data["file_type"] == "docx"


@pytest.mark.asyncio
async def test_upload_resume_rejects_invalid_type(authenticated_client_with_role):
    """Test that invalid file types are rejected with 400."""
    client, role_id = authenticated_client_with_role

    response = await client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.txt", b"text content", "text/plain")},
        headers={"X-Role-Id": str(role_id)}
    )

    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_resume_rejects_oversized(authenticated_client_with_role, tmp_path, monkeypatch):
    """Test that files > 10MB are rejected."""
    client, role_id = authenticated_client_with_role

    monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", tmp_path / "uploads")

    # Create content larger than 10MB
    large_content = b"x" * (10 * 1024 * 1024 + 1)

    response = await client.post(
        "/api/v1/resumes/upload",
        files={"file": ("large.pdf", large_content, "application/pdf")},
        headers={"X-Role-Id": str(role_id)}
    )

    assert response.status_code == 400
    assert "too large" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_resumes_returns_role_scoped(authenticated_client_with_role, tmp_path, monkeypatch):
    """Test that listing resumes only returns current role's resumes."""
    client, role_id = authenticated_client_with_role

    monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", tmp_path / "uploads")

    # Upload a resume
    await client.post(
        "/api/v1/resumes/upload",
        files={"file": ("my_resume.pdf", b"PDF content", "application/pdf")},
        headers={"X-Role-Id": str(role_id)}
    )

    # List resumes
    response = await client.get(
        "/api/v1/resumes",
        headers={"X-Role-Id": str(role_id)}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["filename"] == "my_resume.pdf"


@pytest.mark.asyncio
async def test_delete_resume_success(authenticated_client_with_role, tmp_path, monkeypatch):
    """Test deleting a resume."""
    client, role_id = authenticated_client_with_role

    monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", tmp_path / "uploads")

    # Upload a resume
    upload_response = await client.post(
        "/api/v1/resumes/upload",
        files={"file": ("to_delete.pdf", b"PDF content", "application/pdf")},
        headers={"X-Role-Id": str(role_id)}
    )
    resume_id = upload_response.json()["id"]

    # Delete it
    delete_response = await client.delete(
        f"/api/v1/resumes/{resume_id}",
        headers={"X-Role-Id": str(role_id)}
    )

    assert delete_response.status_code == 204

    # Verify deleted
    list_response = await client.get(
        "/api/v1/resumes",
        headers={"X-Role-Id": str(role_id)}
    )
    assert len(list_response.json()) == 0


@pytest.mark.asyncio
async def test_upload_requires_auth(client):
    """Test that upload requires authentication."""
    response = await client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.pdf", b"content", "application/pdf")},
        headers={"X-Role-Id": "1"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_requires_role_header(authenticated_client, tmp_path, monkeypatch):
    """Test that upload requires X-Role-Id header."""
    monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", tmp_path / "uploads")

    response = await authenticated_client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.pdf", b"content", "application/pdf")}
    )
    assert response.status_code == 400
    assert "X-Role-Id" in response.json()["detail"]


# Test Role Scoping (AC #1, #3 - Files are associated with role)

@pytest.mark.asyncio
async def test_resume_role_isolation(client, tmp_path, monkeypatch):
    """Test that resumes are role-scoped (AC #3 - all resumes available for role)."""
    monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", tmp_path / "uploads")

    # Create user with two roles
    await client.post(
        "/api/v1/auth/register",
        json={"username": "isolation_test", "password": "password123"}
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "isolation_test", "password": "password123"}
    )
    client.cookies = login.cookies

    # Create two roles
    role1_resp = await client.post("/api/v1/roles", json={"name": "Role A"})
    role1_id = role1_resp.json()["id"]

    role2_resp = await client.post("/api/v1/roles", json={"name": "Role B"})
    role2_id = role2_resp.json()["id"]

    # Upload resume to role 1
    await client.post(
        "/api/v1/resumes/upload",
        files={"file": ("role1_resume.pdf", b"PDF for Role 1", "application/pdf")},
        headers={"X-Role-Id": str(role1_id)}
    )

    # Upload resume to role 2
    await client.post(
        "/api/v1/resumes/upload",
        files={"file": ("role2_resume.pdf", b"PDF for Role 2", "application/pdf")},
        headers={"X-Role-Id": str(role2_id)}
    )

    # List resumes for role 1 - should only see role 1's resume
    role1_resumes = await client.get(
        "/api/v1/resumes",
        headers={"X-Role-Id": str(role1_id)}
    )
    assert len(role1_resumes.json()) == 1
    assert role1_resumes.json()[0]["filename"] == "role1_resume.pdf"

    # List resumes for role 2 - should only see role 2's resume
    role2_resumes = await client.get(
        "/api/v1/resumes",
        headers={"X-Role-Id": str(role2_id)}
    )
    assert len(role2_resumes.json()) == 1
    assert role2_resumes.json()[0]["filename"] == "role2_resume.pdf"


@pytest.mark.asyncio
async def test_multiple_resumes_per_role(authenticated_client_with_role, tmp_path, monkeypatch):
    """Test uploading multiple resumes to the same role (AC #3)."""
    client, role_id = authenticated_client_with_role
    monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", tmp_path / "uploads")

    # Upload multiple resumes
    await client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume1.pdf", b"PDF content 1", "application/pdf")},
        headers={"X-Role-Id": str(role_id)}
    )
    await client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume2.docx", b"DOCX content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        headers={"X-Role-Id": str(role_id)}
    )
    await client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume3.pdf", b"PDF content 3", "application/pdf")},
        headers={"X-Role-Id": str(role_id)}
    )

    # All three should be available
    response = await client.get(
        "/api/v1/resumes",
        headers={"X-Role-Id": str(role_id)}
    )
    assert response.status_code == 200
    assert len(response.json()) == 3


@pytest.mark.asyncio
async def test_upload_creates_file_in_correct_directory(authenticated_client_with_role, tmp_path, monkeypatch):
    """Test that uploaded files are stored in data/uploads/{role_id}/ directory."""
    client, role_id = authenticated_client_with_role
    upload_dir = tmp_path / "uploads"
    monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", upload_dir)

    await client.post(
        "/api/v1/resumes/upload",
        files={"file": ("test.pdf", b"PDF content", "application/pdf")},
        headers={"X-Role-Id": str(role_id)}
    )

    # Check directory was created
    role_dir = upload_dir / str(role_id)
    assert role_dir.exists()

    # Check file exists in role directory
    files = list(role_dir.iterdir())
    assert len(files) == 1
    assert files[0].suffix == ".pdf"


@pytest.mark.asyncio
async def test_delete_resume_removes_file(authenticated_client_with_role, tmp_path, monkeypatch):
    """Test that deleting a resume removes the file from disk."""
    client, role_id = authenticated_client_with_role
    upload_dir = tmp_path / "uploads"
    monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", upload_dir)

    # Upload a resume
    upload_response = await client.post(
        "/api/v1/resumes/upload",
        files={"file": ("to_delete.pdf", b"Will be deleted", "application/pdf")},
        headers={"X-Role-Id": str(role_id)}
    )
    resume_id = upload_response.json()["id"]

    # Verify file exists
    role_dir = upload_dir / str(role_id)
    files_before = list(role_dir.iterdir())
    assert len(files_before) == 1

    # Delete the resume
    await client.delete(
        f"/api/v1/resumes/{resume_id}",
        headers={"X-Role-Id": str(role_id)}
    )

    # Verify file was deleted
    files_after = list(role_dir.iterdir())
    assert len(files_after) == 0


@pytest.mark.asyncio
async def test_cannot_delete_other_roles_resume(client, tmp_path, monkeypatch):
    """Test that users cannot delete resumes from other roles."""
    monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", tmp_path / "uploads")

    # Create user with a role
    await client.post(
        "/api/v1/auth/register",
        json={"username": "owner", "password": "password123"}
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "owner", "password": "password123"}
    )
    client.cookies = login.cookies

    role1_resp = await client.post("/api/v1/roles", json={"name": "Owner Role"})
    role1_id = role1_resp.json()["id"]

    role2_resp = await client.post("/api/v1/roles", json={"name": "Other Role"})
    role2_id = role2_resp.json()["id"]

    # Upload resume to role 1
    upload_response = await client.post(
        "/api/v1/resumes/upload",
        files={"file": ("protected.pdf", b"Protected content", "application/pdf")},
        headers={"X-Role-Id": str(role1_id)}
    )
    resume_id = upload_response.json()["id"]

    # Try to delete using role 2's context - should fail
    delete_response = await client.delete(
        f"/api/v1/resumes/{resume_id}",
        headers={"X-Role-Id": str(role2_id)}
    )
    assert delete_response.status_code == 404  # Not found because role-scoped

    # Resume should still exist in role 1
    list_response = await client.get(
        "/api/v1/resumes",
        headers={"X-Role-Id": str(role1_id)}
    )
    assert len(list_response.json()) == 1
