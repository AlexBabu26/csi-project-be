from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.common.config import get_settings

settings = get_settings()

# Convert database URL for async driver
# postgresql+psycopg:// -> postgresql+psycopg:// (psycopg3 supports both sync and async)
database_url = settings.database_url

# Sync engine and session (for sync endpoints like auth)
sync_engine = create_engine(database_url, echo=settings.debug, future=True)
SyncSessionLocal = sessionmaker(
    bind=sync_engine, autoflush=False, autocommit=False, expire_on_commit=False
)

# Async engine and session (for async endpoints)
# psycopg3 uses the same URL for async, just needs AsyncSession
async_engine = create_async_engine(
    database_url.replace("postgresql+psycopg", "postgresql+psycopg"),
    echo=settings.debug,
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, autoflush=False, autocommit=False, expire_on_commit=False
)

Base = declarative_base()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager for sync database sessions."""
    session: Session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a sync database session."""
    with session_scope() as session:
        yield session


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
