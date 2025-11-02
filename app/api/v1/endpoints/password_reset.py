from fastapi import APIRouter, HTTPException, status

from app.models.user import users_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_password_reset_token,
    verify_password_reset_token,
    invalidate_password_reset_token,
)
from app.schemas.auth import PasswordResetRequest, PasswordReset, PasswordResetResponse

router = APIRouter()


@router.post("/forgot-password", response_model=dict)
async def forgot_password(request: PasswordResetRequest):
    """
    Request a password reset.
    
    Generates a reset token and returns it (in production, send via email).
    
    **Note**: In production, the token should be sent via email.
    For MVP, the token is returned in the response.
    
    **Request**: email
    
    **Response**: reset_token (use this in /reset-password endpoint)
    """
    # Find user by email
    user = next((u for u in users_db if u.email == request.email), None)
    if not user:
        # Don't reveal if user exists (security best practice)
        return {
            "message": "If the email exists, a password reset token has been generated.",
            # In production, don't return the token - send via email
            "reset_token": None if not user else create_password_reset_token(
                user.email, user.company_id
            )
        }
    
    # Generate reset token
    reset_token = create_password_reset_token(user.email, user.company_id)
    
    # In production: Send email with reset link
    # For MVP: Return token in response (remove in production!)
    return {
        "message": "Password reset token generated. Check your email.",
        "reset_token": reset_token,  # Remove this in production - send via email only
        "expires_in_minutes": 15
    }


@router.post("/reset-password", response_model=PasswordResetResponse)
async def reset_password(reset_data: PasswordReset):
    """
    Reset password using the reset token.
    
    **Request**:
    - token: Password reset token (from /forgot-password)
    - new_password: New password (min 8 characters)
    
    **Response**: Success message
    """
    # Verify reset token
    token_data = verify_password_reset_token(reset_data.token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Find user
    user = next((u for u in users_db if u.email == token_data["email"]), None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify company_id matches (security check)
    if user.company_id != token_data["company_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token company mismatch"
        )
    
    # Update password
    user.hashed_password = get_password_hash(reset_data.new_password)
    
    # Invalidate reset token (one-time use)
    invalidate_password_reset_token(reset_data.token)
    
    return PasswordResetResponse(message="Password reset successfully")

