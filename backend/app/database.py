"""Database configuration with SQLite and async SQLModel."""

from collections.abc import AsyncGenerator

from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import event, text

from app.config import settings, DATA_DIR

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

_engine = create_async_engine(
    settings.database_url,
    echo=settings.debug
)

_session_factory = async_sessionmaker(
    _engine,
    class_=AsyncSession,
    expire_on_commit=False
)


def _attach_pragmas(eng):
    """Attach SQLite pragma listeners to an engine."""
    @event.listens_for(eng.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Set SQLite pragmas on connection."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Enable WAL mode for better concurrent read performance
_attach_pragmas(_engine)


class _SessionMakerProxy:
    """Proxy that always delegates to the current _session_factory.

    This ensures that code which imported async_session_maker at module level
    still uses the correct session factory even after configure_engine() swaps it.
    """

    def __call__(self, *args, **kwargs):
        return _session_factory(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(_session_factory, name)


async_session_maker = _SessionMakerProxy()


# Module-level engine alias for backward compatibility (e.g. test assertions)
# Use get_engine() for reliable access after configure_engine()
engine = _engine


def configure_engine(url: str | None = None):
    """Reconfigure the database engine and session maker.

    Used by test infrastructure to switch to a test database.
    If url is not provided, reads from settings.database_url.
    """
    global _engine, _session_factory, engine

    # Dispose old engine to release connection pool resources
    if _engine is not None:
        _engine.sync_engine.dispose()

    db_url = url or settings.database_url
    _engine = create_async_engine(db_url, echo=settings.debug)
    engine = _engine
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    _attach_pragmas(_engine)


def get_engine():
    """Get the current database engine."""
    return _engine


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Async dependency for getting database session."""
    async with _session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def _ensure_columns(conn, table: str, columns: list[tuple[str, str]]):
    """Add missing columns to an existing table (SQLite ALTER TABLE).

    Checks PRAGMA table_info for existing columns and adds any that are missing.
    Safe to call repeatedly — skips columns that already exist.
    """
    result = await conn.execute(text(f"PRAGMA table_info({table})"))
    existing = {row[1] for row in result}
    for col_name, col_type in columns:
        if col_name not in existing:
            await conn.execute(
                text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
            )


async def init_db():
    """Initialize database tables."""
    # Import models here to ensure they're registered with SQLModel metadata
    from app.models.user import User  # noqa: F401
    from app.models.role import Role  # noqa: F401
    from app.models.experience import Skill, Accomplishment  # noqa: F401
    from app.models.application import Application  # noqa: F401
    from app.models.resume import Resume  # noqa: F401
    from app.models.llm_call_log import LLMCallLog  # noqa: F401
    from app.models.keyword_pattern import KeywordPattern  # noqa: F401
    async with _engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

        # Add columns introduced after initial schema creation
        await _ensure_columns(conn, "accomplishments", [
            ("company_name", "TEXT"),
            ("role_title", "TEXT"),
            ("dates", "TEXT"),
        ])
