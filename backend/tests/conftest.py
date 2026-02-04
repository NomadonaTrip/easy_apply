import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlmodel import select

from app.main import app
from app.database import async_session_maker, init_db


@pytest.fixture
def client():
    return TestClient(app)


@pytest_asyncio.fixture(autouse=True)
async def clean_database():
    """Clean all tables before each test (shared fixture for all test files)."""
    await init_db()
    async with async_session_maker() as session:
        # Import all models for cleanup
        from app.models.user import User
        from app.models.role import Role
        from app.models.experience import Skill, Accomplishment
        from app.models.resume import Resume

        # Clean up resumes (foreign key to roles)
        result = await session.execute(select(Resume))
        resumes = result.scalars().all()
        for resume in resumes:
            await session.delete(resume)

        # Clean up skills (foreign key to roles)
        result = await session.execute(select(Skill))
        skills = result.scalars().all()
        for skill in skills:
            await session.delete(skill)

        # Clean up accomplishments (foreign key to roles)
        result = await session.execute(select(Accomplishment))
        accomplishments = result.scalars().all()
        for acc in accomplishments:
            await session.delete(acc)

        # Clean up roles (foreign key to users)
        result = await session.execute(select(Role))
        roles = result.scalars().all()
        for role in roles:
            await session.delete(role)

        # Clean up users
        result = await session.execute(select(User))
        users = result.scalars().all()
        for user in users:
            await session.delete(user)

        await session.commit()
    yield
