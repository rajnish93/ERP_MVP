from uuid import UUID
from fastapi import APIRouter, HTTPException, status

from sqlalchemy import select
from app.core.deps import SessionDep
from app.core.error_handlers import handle_db_operation
from app.core.workspace import get_company_id_by_slug
from app.db.models.user import User
from app.core.security import (
    get_password_hash,
    create_password_reset_token,
    verify_password_reset_token,
    invalidate_password_reset_token,
)
from app.schemas.auth import PasswordResetRequest, PasswordReset, PasswordResetResponse

router = APIRouter()


@router.post("/forgot-password", response_model=dict)
async def forgot_password(request: PasswordResetRequest, db: SessionDep):
    """
    Request a password reset.

    Generates a reset token and returns it (in production, send via email).

    **Note**: In production, the token should be sent via email.
    For MVP, the token is returned in the response.

    **Request**:
    - email: User's email address
    - workspace: Workspace slug (e.g. test, xyz)

    **Response**: reset_token (use this in /reset-password endpoint)
    """
    # Resolve company_id from workspace slug
    company_id_str = await get_company_id_by_slug(db, request.workspace)
    if not company_id_str:
        # Don't reveal workspace existence for security
        return {
            "message": "If the email and workspace are valid, a password reset token has been generated.",
            "reset_token": None
        }

    try:
        company_id = UUID(company_id_str)
    except ValueError:
        # Don't reveal invalid workspace configuration
        return {
            "message": "If the email and workspace are valid, a password reset token has been generated.",
            "reset_token": None
        }

    # Find user by email AND company_id (tenant-scoped lookup)
    stmt = select(User).where(
        User.email == request.email,
        User.company_id == company_id
    )
    user = (await db.execute(stmt)).scalars().first()
    if not user:
        # Don't reveal if user exists (security best practice)
        return {
            "message": "If the email and workspace are valid, a password reset token has been generated.",
            "reset_token": None
        }
    
    # Generate reset token
    reset_token = await create_password_reset_token(db, user.email, user.company_id)
    
    # In production: Send email with reset link
    # For MVP: Return token in response (remove in production!)
    return {
        "message": "Password reset token generated. Check your email.",
        "reset_token": reset_token,  # Remove this in production - send via email only
        "expires_in_minutes": 15
    }


@router.post("/reset-password", response_model=PasswordResetResponse)
async def reset_password(reset_data: PasswordReset, db: SessionDep):
    """
    Reset password using the reset token.
    
    **Request**:
    - token: Password reset token (from /forgot-password)
    - new_password: New password (min 8 characters)
    
    **Response**: Success message
    """
    # Verify reset token
    token_data = await verify_password_reset_token(db, reset_data.token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Find user by email AND company_id (tenant-scoped lookup)
    stmt = select(User).where(
        User.email == token_data["email"],
        User.company_id == token_data["company_id"]
    )
    user = (await db.execute(stmt)).scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update password
    user.hashed_password = get_password_hash(reset_data.new_password)
    async with handle_db_operation(db, "reset password"):
        await db.commit()
    
    # Invalidate reset token (one-time use)
    await invalidate_password_reset_token(db, reset_data.token)
    
    return PasswordResetResponse(message="Password reset successfully")

