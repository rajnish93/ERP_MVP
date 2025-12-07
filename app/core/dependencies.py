from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import decode_access_token
from app.core.config import settings
from app.core.database import get_db
from app.db.models.user import User, UserRole

# OAuth2 Password Flow scheme for token authentication
# This is FastAPI's built-in OAuth2 with Password Flow (and Bearer with JWT tokens)
# The tokenUrl points to the token endpoint where users authenticate
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
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
    
    # Find user by email in database
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    
    # Verify company_id matches (security check for tenant isolation)
    # Convert string UUID from token to UUID object for comparison
    if company_id_str is not None:
        try:
            company_id_from_token = UUID(company_id_str)
            if user.company_id != company_id_from_token:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Token company mismatch - possible security issue"
                )
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid company_id in token"
            )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get the current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    return current_user


def require_role(*allowed_roles: UserRole):
    """Dependency factory for role-based access control"""
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[role.value for role in allowed_roles]}"
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


# Tenant isolation dependency - ensures data is scoped to user's company
async def get_current_company_id(current_user: User = Depends(get_current_active_user)) -> UUID:
    """
    Get the current user's company_id for tenant isolation.
    
    Use this dependency to ensure all data queries filter by company_id.
    
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
    return current_user.company_id


# Helper to get users filtered by company
async def get_company_users(company_id: UUID, db: AsyncSession):
    """Get all users for a specific company (tenant isolation)"""
    stmt = select(User).where(User.company_id == company_id)
    result = await db.execute(stmt)
    return result.scalars().all()

