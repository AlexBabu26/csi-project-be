"""Database configuration with lazy initialization for serverless environments.

This module implements lazy database connection initialization to reduce cold start
times on Vercel serverless functions. Connections are only established when first
needed, not at module import time.

Local development uses a connection pool (remote Neon/Postgres is slow per connect).
Set DATABASE_USE_NULL_POOL=1 to force NullPool (serverless-style).
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from functools import lru_cache
from typing import AsyncGenerator, Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from app.common.config import get_settings

# Base class for all ORM models - this is safe to initialize at import time
Base = declarative_base()

_SyncSessionLocal: Optional[sessionmaker] = None
_AsyncSessionLocal: Optional[async_sessionmaker[AsyncSession]] = None


def _normalize_async_database_url(url: str) -> str:
    """Ensure async SQLAlchemy uses psycopg v3, not psycopg2."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def _use_null_pool() -> bool:
    """NullPool only for true serverless; pooled connections for local/long-running."""
    flag = os.getenv("DATABASE_USE_NULL_POOL", "").lower()
    if flag in ("1", "true", "yes"):
        return True
    if flag in ("0", "false", "no"):
        return False
    return bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))


def _engine_kwargs(*, async_engine: bool) -> dict:
    settings = get_settings()
    kwargs: dict = {
        "echo": settings.debug,
        "future": True,
    }
    if _use_null_pool():
        kwargs["poolclass"] = NullPool
    else:
        if not async_engine:
            kwargs["poolclass"] = QueuePool
        kwargs.update(
            {
                "pool_size": int(os.getenv("DATABASE_POOL_SIZE", "5")),
                "max_overflow": int(os.getenv("DATABASE_MAX_OVERFLOW", "10")),
                "pool_pre_ping": True,
                "pool_recycle": int(os.getenv("DATABASE_POOL_RECYCLE", "300")),
            }
        )
    if async_engine:
        kwargs["connect_args"] = {"connect_timeout": int(os.getenv("DATABASE_CONNECT_TIMEOUT", "15"))}
    return kwargs


@lru_cache(maxsize=1)
def get_sync_engine():
    """Lazily create sync engine on first database access."""
    settings = get_settings()
    return create_engine(settings.database_url, **_engine_kwargs(async_engine=False))


@lru_cache(maxsize=1)
def get_async_engine():
    """Lazily create async engine on first database access."""
    settings = get_settings()
    async_url = _normalize_async_database_url(settings.database_url)
    return create_async_engine(async_url, **_engine_kwargs(async_engine=True))


def get_sync_sessionmaker() -> sessionmaker:
    global _SyncSessionLocal
    if _SyncSessionLocal is None:
        _SyncSessionLocal = sessionmaker(
            bind=get_sync_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _SyncSessionLocal


def get_async_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(
            bind=get_async_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _AsyncSessionLocal


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager for sync database sessions."""
    session: Session = get_sync_sessionmaker()()
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
    session = get_async_sessionmaker()()
    try:
        yield session
        if session.new or session.dirty or session.deleted:
            await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# Backward compatibility aliases for code that imports engines directly
def _get_sync_engine_compat():
    """Backward compatibility: returns sync engine (triggers lazy init)."""
    return get_sync_engine()


def _get_async_engine_compat():
    """Backward compatibility: returns async engine (triggers lazy init)."""
    return get_async_engine()


sync_engine = property(lambda self: get_sync_engine())
async_engine = property(lambda self: get_async_engine())
