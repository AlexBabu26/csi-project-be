from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.common.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, echo=settings.debug, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)

Base = declarative_base()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
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
    """FastAPI dependency that provides a database session."""
    with session_scope() as session:
        yield session

