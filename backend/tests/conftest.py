import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.config import settings, DATA_DIR

TEST_DB_PATH = DATA_DIR / "test_easy_apply.db"


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Switch to test DB, create schema once for the entire session."""
    # Activate test database URL
    settings.testing = True

    # Remove old test DB if present
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    # Reconfigure engine to use the test URL, then create tables
    from app.database import configure_engine, init_db
    configure_engine()
    await init_db()

    yield

    # Cleanup after all tests
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest_asyncio.fixture(autouse=True)
async def clean_database():
    """Delete all records before each test.

    Uses raw SQL DELETE in FK dependency order to avoid autoflush issues.
    """
    from app.database import async_session_maker

    async with async_session_maker() as session:
        # Delete in FK dependency order using raw SQL to avoid ORM autoflush issues
        await session.execute(text("DELETE FROM llm_call_log"))
        await session.execute(text("DELETE FROM enrichment_candidates"))
        await session.execute(text("DELETE FROM keyword_patterns"))
        await session.execute(text("DELETE FROM applications"))
        await session.execute(text("DELETE FROM resumes"))
        await session.execute(text("DELETE FROM skills"))
        await session.execute(text("DELETE FROM accomplishments"))
        await session.execute(text("DELETE FROM roles"))
        await session.execute(text("DELETE FROM users"))
        await session.commit()
    yield


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client():
    """Async test client for FastAPI."""
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
