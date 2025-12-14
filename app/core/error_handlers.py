from contextlib import asynccontextmanager
import logging
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

# Configure logger
logger = logging.getLogger(__name__)


@asynccontextmanager
async def handle_db_operation(db: AsyncSession, operation_name: str):
    """
    Context manager for database operations with automatic error handling.

    Usage:
        async with handle_db_operation(db, "create user"):
            # Your database operations here
            db.add(new_user)
            await db.commit()

    Args:
        db: AsyncSession instance
        operation_name: Human-readable operation name (e.g., "create user", "update asset")

    Raises:
        HTTPException: 500 Internal Server Error if operation fails
    """
    try:
        yield
    except HTTPException:
        # Re-raise HTTP exceptions (like 404, 401, etc.) without modification
        await db.rollback()
        raise
    except Exception as e:
        # Catch any other exception, rollback, and return generic error
        await db.rollback()
        # Log the actual error for debugging
        logger.error(f"Failed to {operation_name}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to {operation_name} due to an internal server error.",
        )
