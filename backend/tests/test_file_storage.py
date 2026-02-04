"""Tests for file storage utility."""

import pytest
import pytest_asyncio
from pathlib import Path
from io import BytesIO
from unittest.mock import MagicMock, AsyncMock


# Test file validation

def test_validate_file_accepts_pdf():
    """Test that PDF files are accepted."""
    from app.utils.file_storage import validate_file

    mock_file = MagicMock()
    mock_file.filename = "resume.pdf"
    mock_file.content_type = "application/pdf"

    is_valid, error = validate_file(mock_file)
    assert is_valid is True
    assert error is None


def test_validate_file_accepts_docx():
    """Test that DOCX files are accepted."""
    from app.utils.file_storage import validate_file

    mock_file = MagicMock()
    mock_file.filename = "resume.docx"
    mock_file.content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    is_valid, error = validate_file(mock_file)
    assert is_valid is True
    assert error is None


def test_validate_file_rejects_txt():
    """Test that TXT files are rejected."""
    from app.utils.file_storage import validate_file

    mock_file = MagicMock()
    mock_file.filename = "resume.txt"
    mock_file.content_type = "text/plain"

    is_valid, error = validate_file(mock_file)
    assert is_valid is False
    assert "Invalid file type" in error


def test_validate_file_rejects_exe():
    """Test that EXE files are rejected."""
    from app.utils.file_storage import validate_file

    mock_file = MagicMock()
    mock_file.filename = "malware.exe"
    mock_file.content_type = "application/x-msdownload"

    is_valid, error = validate_file(mock_file)
    assert is_valid is False
    assert "Invalid file type" in error


def test_validate_file_rejects_mismatched_content_type():
    """Test that files with mismatched content type are rejected."""
    from app.utils.file_storage import validate_file

    mock_file = MagicMock()
    mock_file.filename = "resume.pdf"
    mock_file.content_type = "text/plain"  # Wrong content type

    is_valid, error = validate_file(mock_file)
    assert is_valid is False
    assert "content type" in error.lower()


def test_validate_file_handles_no_extension():
    """Test that files without extension are rejected."""
    from app.utils.file_storage import validate_file

    mock_file = MagicMock()
    mock_file.filename = "resume"
    mock_file.content_type = "application/pdf"

    is_valid, error = validate_file(mock_file)
    assert is_valid is False


def test_validate_file_handles_empty_filename():
    """Test that empty filenames are handled."""
    from app.utils.file_storage import validate_file

    mock_file = MagicMock()
    mock_file.filename = ""
    mock_file.content_type = "application/pdf"

    is_valid, error = validate_file(mock_file)
    assert is_valid is False


# Test save_uploaded_file

def mock_chunked_read(content: bytes):
    """Create a mock read function that simulates chunked reading."""
    chunks = [content, b""]  # Content on first read, empty on second to signal EOF
    async def read(size=None):
        if chunks:
            return chunks.pop(0)
        return b""
    return read


@pytest.mark.asyncio
async def test_save_uploaded_file_creates_directory(tmp_path, monkeypatch):
    """Test that save_uploaded_file creates role-specific directory."""
    from app.utils.file_storage import save_uploaded_file, UPLOAD_DIR

    # Monkeypatch UPLOAD_DIR to use temp path
    monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", tmp_path / "uploads")

    content = b"PDF content here"
    mock_file = MagicMock()
    mock_file.filename = "resume.pdf"
    mock_file.size = None  # Unknown size
    mock_file.read = mock_chunked_read(content)

    file_path, file_size = await save_uploaded_file(mock_file, role_id=42)

    # Verify directory was created
    assert (tmp_path / "uploads" / "42").exists()
    assert file_size == len(content)


@pytest.mark.asyncio
async def test_save_uploaded_file_generates_unique_names(tmp_path, monkeypatch):
    """Test that uploaded files get unique names."""
    from app.utils.file_storage import save_uploaded_file

    monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", tmp_path / "uploads")

    mock_file1 = MagicMock()
    mock_file1.filename = "resume.pdf"
    mock_file1.size = None
    mock_file1.read = mock_chunked_read(b"Content 1")

    mock_file2 = MagicMock()
    mock_file2.filename = "resume.pdf"
    mock_file2.size = None
    mock_file2.read = mock_chunked_read(b"Content 2")

    path1, _ = await save_uploaded_file(mock_file1, role_id=1)
    path2, _ = await save_uploaded_file(mock_file2, role_id=1)

    # Paths should be different (unique filenames)
    assert path1 != path2


@pytest.mark.asyncio
async def test_save_uploaded_file_preserves_extension(tmp_path, monkeypatch):
    """Test that file extension is preserved."""
    from app.utils.file_storage import save_uploaded_file

    monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", tmp_path / "uploads")

    mock_file = MagicMock()
    mock_file.filename = "my-resume.docx"
    mock_file.size = None
    mock_file.read = mock_chunked_read(b"DOCX content")

    file_path, _ = await save_uploaded_file(mock_file, role_id=1)

    assert file_path.endswith(".docx")


def mock_large_chunked_read(total_size: int, chunk_size: int = 8192):
    """Create a mock read function that simulates a large file being read in chunks."""
    bytes_remaining = total_size
    async def read(size=None):
        nonlocal bytes_remaining
        if bytes_remaining <= 0:
            return b""
        to_read = min(chunk_size, bytes_remaining)
        bytes_remaining -= to_read
        return b"x" * to_read
    return read


@pytest.mark.asyncio
async def test_save_uploaded_file_rejects_oversized(tmp_path, monkeypatch):
    """Test that oversized files are rejected."""
    from app.utils.file_storage import save_uploaded_file, MAX_FILE_SIZE

    monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", tmp_path / "uploads")

    mock_file = MagicMock()
    mock_file.filename = "large.pdf"
    mock_file.size = None  # Size unknown, will be rejected during streaming
    mock_file.read = mock_large_chunked_read(MAX_FILE_SIZE + 1)

    with pytest.raises(ValueError, match="File too large"):
        await save_uploaded_file(mock_file, role_id=1)


@pytest.mark.asyncio
async def test_save_uploaded_file_returns_relative_path(tmp_path, monkeypatch):
    """Test that returned path is relative to data directory."""
    from app.utils.file_storage import save_uploaded_file

    monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", tmp_path / "uploads")

    mock_file = MagicMock()
    mock_file.filename = "resume.pdf"
    mock_file.size = None
    mock_file.read = mock_chunked_read(b"Content")

    file_path, _ = await save_uploaded_file(mock_file, role_id=99)

    # Path should start with uploads/role_id/
    assert file_path.startswith("uploads/99/")


@pytest.mark.asyncio
async def test_save_uploaded_file_early_rejects_when_size_known(tmp_path, monkeypatch):
    """Test that files are rejected early when size is known upfront."""
    from app.utils.file_storage import save_uploaded_file, MAX_FILE_SIZE

    monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", tmp_path / "uploads")

    mock_file = MagicMock()
    mock_file.filename = "large.pdf"
    mock_file.size = MAX_FILE_SIZE + 1  # Size known upfront
    # read should NOT be called because early rejection happens first
    mock_file.read = MagicMock(side_effect=AssertionError("read should not be called"))

    with pytest.raises(ValueError, match="File too large"):
        await save_uploaded_file(mock_file, role_id=1)


# Test delete_file

def test_delete_file_removes_existing(tmp_path, monkeypatch):
    """Test that delete_file removes an existing file."""
    from app.utils.file_storage import delete_file

    # Create a test file
    test_file = tmp_path / "uploads" / "1" / "test.pdf"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_bytes(b"test content")

    # Monkeypatch the base path
    monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", tmp_path / "uploads")

    result = delete_file("uploads/1/test.pdf")

    assert result is True
    assert not test_file.exists()


def test_delete_file_returns_false_for_nonexistent(tmp_path, monkeypatch):
    """Test that delete_file returns False for non-existent file."""
    from app.utils.file_storage import delete_file

    monkeypatch.setattr("app.utils.file_storage.UPLOAD_DIR", tmp_path / "uploads")

    result = delete_file("uploads/1/nonexistent.pdf")

    assert result is False


# Test constants

def test_allowed_extensions():
    """Test that only PDF and DOCX are allowed."""
    from app.utils.file_storage import ALLOWED_EXTENSIONS

    assert "pdf" in ALLOWED_EXTENSIONS
    assert "docx" in ALLOWED_EXTENSIONS
    assert len(ALLOWED_EXTENSIONS) == 2


def test_max_file_size():
    """Test that max file size is 10MB."""
    from app.utils.file_storage import MAX_FILE_SIZE

    assert MAX_FILE_SIZE == 10 * 1024 * 1024  # 10MB
