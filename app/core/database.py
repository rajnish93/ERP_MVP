from typing import AsyncGenerator
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings


# Create async engine with configurable settings
async_engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=settings.DB_POOL_SIZE,  # Configurable connection pool size
    max_overflow=settings.DB_MAX_OVERFLOW,  # Configurable maximum overflow connections
    echo=settings.DB_ECHO,  # Configurable SQL query logging for debugging
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,  # Recommended for FastAPI
    autoflush=False,
    autocommit=False,
)

# Base class for declarative models (SQLAlchemy 2.0 syntax)
class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async dependency function for getting database session.

    According to FastAPI and SQLAlchemy 2.0 best practices:
    - Yields an async database session
    - Automatically rolls back on exceptions
    - Always closes the session in finally block

    Usage:
        @router.get("/employees")
        async def get_employees(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Employee).where(Employee.company_id == company_id))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
