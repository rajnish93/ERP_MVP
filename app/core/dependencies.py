from typing import Optional, Annotated
from uuid import UUID
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.workspace import get_company_id_by_slug
from app.core.security import decode_access_token
from app.core.config import settings
from app.core.database import get_db
from app.db.models.user import User, UserRole

# OAuth2 Password Flow scheme for token authentication
# This is FastAPI's built-in OAuth2 with Password Flow (and Bearer with JWT tokens)
# The tokenUrl points to the token endpoint where users authenticate
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Get the current authenticated user from JWT token.

    This is the core dependency for FastAPI's OAuth2 Password Flow.
    It extracts the Bearer token from the Authorization header, decodes the JWT,
    and returns the corresponding user.

    Usage:
        @router.get("/protected")
        async def protected_route(current_user: User = Depends(get_current_user)):
            return current_user

    The token is automatically extracted by OAuth2PasswordBearer from:
    Authorization: Bearer <token>
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    # Extract email and company_id from token
    email: Optional[str] = payload.get("sub")
    company_id_str: Optional[str] = payload.get("company_id")

    if email is None:
        raise credentials_exception

    # Require company_id in token (strict multi-tenancy)
    if not company_id_str:
        raise credentials_exception

    try:
        company_id = UUID(company_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid company_id in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Find user by email AND company_id in database
    # This enforces strict tenant isolation at the query level
    stmt = select(User).where(User.email == email, User.company_id == company_id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get the current active user (already validated by get_current_user)"""
    return current_user


def require_role(*allowed_roles: UserRole):
    """Dependency factory for role-based access control"""

    async def role_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[role.value for role in allowed_roles]}",
            )
        return current_user

    return role_checker


# Convenience dependencies for common role checks
# These can be used directly in route decorators
# Example: Depends(require_admin_dependency())
def require_admin_dependency():
    """Dependency for admin-only access"""
    return require_role(UserRole.ADMIN)


def require_hr_dependency():
    """Dependency for HR or Admin access"""
    return require_role(UserRole.HR, UserRole.ADMIN)


def require_employee_dependency():
    """Dependency for any authenticated user"""
    return require_role(UserRole.EMPLOYEE, UserRole.HR, UserRole.ADMIN)


# Company isolation dependency - ensures data is scoped to user's company
async def get_current_company_id(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    x_workspace: Annotated[
        str | None,
        Header(alias="X-Workspace", description="Workspace slug (e.g. test, xyz)"),
    ] = None,
) -> UUID:
    """
    Get the current user's company_id for company isolation.

    This dependency enforces header-based multi-tenancy using workspace slugs.
    It validates that the `X-Workspace` header matches the authenticated user's company.

    Usage:
        @router.get("/employees")
        async def get_employees(
            company_id: UUID = Depends(get_current_company_id),
            current_user: User = Depends(get_current_active_user)
        ):
            # Filter employees by company_id
            stmt = select(Employee).where(Employee.company_id == company_id)
            employees = (await db.execute(stmt)).scalars().all()
            return employees
    """
    # If no header provided, just use the user's company_id
    # (This is simpler since we already authenticated the user with company context)
    if not x_workspace:
        return current_user.company_id

    # If header is provided, verify it matches user's company
    company_id_str = await get_company_id_by_slug(db, x_workspace)
    if not company_id_str:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{x_workspace}' not found",
        )

    try:
        header_company_id = UUID(company_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid workspace configuration",
        ) from None

    if header_company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace mismatch. X-Workspace does not match your assigned company.",
        )

    return current_user.company_id


# Helper to get users filtered by company
async def get_company_users(company_id: UUID, db: AsyncSession):
    """Get all users for a specific company (company isolation)"""
    stmt = select(User).where(User.company_id == company_id)
    result = await db.execute(stmt)
    return result.scalars().all()
