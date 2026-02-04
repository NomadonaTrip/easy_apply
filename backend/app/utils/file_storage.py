"""File storage utility for resume uploads."""

import uuid
from pathlib import Path
from fastapi import UploadFile

# Base path for file uploads (relative to project root)
UPLOAD_DIR = Path("data/uploads")

# Allowed file extensions
ALLOWED_EXTENSIONS = {"pdf", "docx"}

# Maximum file size in bytes (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Valid content types for each extension
VALID_CONTENT_TYPES = {
    "pdf": ["application/pdf"],
    "docx": [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ],
}


def validate_file(file: UploadFile) -> tuple[bool, str | None]:
    """
    Validate uploaded file type and content type.

    Args:
        file: The uploaded file to validate

    Returns:
        Tuple of (is_valid, error_message).
        If valid, error_message is None.
    """
    # Check filename exists
    filename = file.filename or ""
    if not filename:
        return False, "Filename is required"

    # Extract extension
    if "." not in filename:
        return False, "Invalid file type. Allowed: pdf, docx"

    extension = filename.rsplit(".", 1)[-1].lower()

    # Check extension is allowed
    if extension not in ALLOWED_EXTENSIONS:
        return False, f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"

    # Check content type matches extension
    content_type = file.content_type or ""
    if extension not in VALID_CONTENT_TYPES:
        return False, f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"

    if content_type not in VALID_CONTENT_TYPES[extension]:
        return False, f"File content type does not match extension. Expected one of {VALID_CONTENT_TYPES[extension]}, got {content_type}"

    return True, None


async def save_uploaded_file(file: UploadFile, role_id: int) -> tuple[str, int]:
    """
    Save uploaded file to disk with streaming and early size validation.

    Args:
        file: The uploaded file
        role_id: The role ID to associate the file with

    Returns:
        Tuple of (relative_file_path, file_size).
        The path is relative to the UPLOAD_DIR parent.

    Raises:
        ValueError: If file is too large
    """
    # Check Content-Length header first if available (early rejection)
    # file.size may be None, an int, or a mock in tests - check it's actually an int
    if hasattr(file, 'size') and isinstance(file.size, int) and file.size > MAX_FILE_SIZE:
        raise ValueError(
            f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)}MB"
        )

    # Create role-specific directory
    role_dir = UPLOAD_DIR / str(role_id)
    role_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename preserving extension
    filename = file.filename or "file"
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    unique_name = f"{uuid.uuid4().hex}.{extension}"
    file_path = role_dir / unique_name

    # Stream file to disk with size tracking (prevents full memory load)
    file_size = 0
    try:
        with open(file_path, "wb") as f:
            while chunk := await file.read(8192):  # 8KB chunks
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE:
                    raise ValueError(
                        f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)}MB"
                    )
                f.write(chunk)
    except ValueError:
        # Clean up partial file on size error
        if file_path.exists():
            file_path.unlink()
        raise

    # Return path relative to data directory (for database storage)
    # e.g., "uploads/42/abc123.pdf"
    relative_path = str(file_path.relative_to(UPLOAD_DIR.parent))
    return relative_path, file_size


def delete_file(file_path: str) -> bool:
    """
    Delete a file from storage.

    Args:
        file_path: Path relative to data directory (e.g., "uploads/1/abc.pdf")

    Returns:
        True if file was deleted, False if file didn't exist
    """
    # UPLOAD_DIR is data/uploads, so parent is data
    full_path = UPLOAD_DIR.parent / file_path
    if full_path.exists():
        full_path.unlink()
        return True
    return False
