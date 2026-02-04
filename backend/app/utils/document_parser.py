"""Document parsing utilities for extracting text from PDF and DOCX files."""

from pathlib import Path

from pypdf import PdfReader
from docx import Document

from app.config import DATA_DIR


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text content from a PDF file.

    Args:
        file_path: Path to the PDF file (relative to DATA_DIR or absolute)

    Returns:
        Extracted text content
    """
    # Handle both relative and absolute paths
    path = Path(file_path)
    if not path.is_absolute():
        path = DATA_DIR / file_path

    reader = PdfReader(str(path))

    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)

    return "\n\n".join(text_parts)


def extract_text_from_docx(file_path: str) -> str:
    """
    Extract text content from a DOCX file.

    Args:
        file_path: Path to the DOCX file (relative to DATA_DIR or absolute)

    Returns:
        Extracted text content
    """
    # Handle both relative and absolute paths
    path = Path(file_path)
    if not path.is_absolute():
        path = DATA_DIR / file_path

    doc = Document(str(path))

    text_parts = []
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text_parts.append(paragraph.text)

    return "\n\n".join(text_parts)


def extract_text(file_path: str, file_type: str) -> str:
    """
    Extract text from a document based on file type.

    Args:
        file_path: Path to the file
        file_type: File extension (pdf or docx)

    Returns:
        Extracted text content

    Raises:
        ValueError: If file type is not supported
    """
    if file_type == "pdf":
        return extract_text_from_pdf(file_path)
    elif file_type == "docx":
        return extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")
