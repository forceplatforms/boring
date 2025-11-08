"""
Database configuration and session management.
Provides both sync and async database connections with proper connection pooling.
"""

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from complianceguard.config import get_settings

settings = get_settings()

# Create sync engine for Celery and migrations
sync_engine = create_engine(
    settings.get_sync_database_url(),
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
    echo=settings.database_echo,
    pool_pre_ping=True,  # Verify connections before using
    poolclass=NullPool if settings.environment == "test" else None,
)

# Create async engine for FastAPI
async_engine = create_async_engine(
    settings.get_database_url_with_driver(),
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
    echo=settings.database_echo,
    pool_pre_ping=True,
)

# Session factories
SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)

# Base class for models
Base = declarative_base()


# Dependency for FastAPI (async)
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async database session dependency for FastAPI.

    Yields:
        AsyncSession instance.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Dependency for sync operations (Celery)
def get_sync_db() -> Generator[Session, None, None]:
    """
    Sync database session for Celery tasks.

    Yields:
        Session instance.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# Context managers for explicit session management
@asynccontextmanager
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions.

    Usage:
        async with async_db_session() as session:
            result = await session.execute(query)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@contextmanager
def sync_db_session() -> Generator[Session, None, None]:
    """
    Sync context manager for database sessions.

    Usage:
        with sync_db_session() as session:
            result = session.execute(query)
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def init_async_db() -> None:
    """Initialize async database (create tables if needed)."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def init_sync_db() -> None:
    """Initialize sync database (create tables if needed)."""
    Base.metadata.create_all(bind=sync_engine)


async def close_async_db() -> None:
    """Close async database connections."""
    await async_engine.dispose()


def close_sync_db() -> None:
    """Close sync database connections."""
    sync_engine.dispose()