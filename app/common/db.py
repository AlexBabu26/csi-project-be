"""Database configuration with lazy initialization for serverless environments.

This module implements lazy database connection initialization to reduce cold start
times on Vercel serverless functions. Connections are only established when first
needed, not at module import time.
"""

from contextlib import contextmanager
from functools import lru_cache
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from app.common.config import get_settings

# Base class for all ORM models - this is safe to initialize at import time
Base = declarative_base()


@lru_cache(maxsize=1)
def get_sync_engine():
    """
    Lazily create sync engine on first database access.
    
    Uses NullPool for serverless environments where connection pooling
    doesn't persist across function invocations.
    """
    settings = get_settings()
    return create_engine(
        settings.database_url,
        echo=settings.debug,
        future=True,
        poolclass=NullPool,  # No pooling - better for serverless
    )


@lru_cache(maxsize=1)
def get_async_engine():
    """
    Lazily create async engine on first database access.
    
    Uses NullPool for serverless environments where connection pooling
    doesn't persist across function invocations.
    """
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        poolclass=NullPool,  # No pooling - better for serverless
    )


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager for sync database sessions."""
    SessionLocal = sessionmaker(
        bind=get_sync_engine(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False
    )
    session: Session = SessionLocal()
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
    AsyncSessionLocal = async_sessionmaker(
        bind=get_async_engine(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False
    )
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Backward compatibility aliases for code that imports engines directly
# These will trigger lazy initialization when accessed
def _get_sync_engine_compat():
    """Backward compatibility: returns sync engine (triggers lazy init)."""
    return get_sync_engine()


def _get_async_engine_compat():
    """Backward compatibility: returns async engine (triggers lazy init)."""
    return get_async_engine()


# For backward compatibility with existing code that imports these directly
# Note: These are now functions, not module-level variables
sync_engine = property(lambda self: get_sync_engine())
async_engine = property(lambda self: get_async_engine())
