"""
Database configuration and session management.
Provides async SQLAlchemy engine, session maker, and dependency injection.
"""
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from .config import settings

import re

logger = logging.getLogger(__name__)

database_url = settings.DATABASE_URL
# Replace postgresql:// or postgres:// with postgresql+asyncpg://
database_url = re.sub(
    r'^postgres(ql)?://', 
    'postgresql+asyncpg://', 
    database_url
)

engine = create_async_engine(
    database_url,
    pool_size=10,
    max_overflow=20,
    echo=False
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db():
    """Dependency for getting async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def test_connection() -> bool:
    """Test the PostgreSQL connection."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False
