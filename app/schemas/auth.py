from pydantic import BaseModel, EmailStr, Field


class PasswordResetRequest(BaseModel):
    """Schema for password reset request"""

    email: EmailStr
    workspace: str = Field(..., description="Workspace slug (e.g. test, xyz)")


class PasswordReset(BaseModel):
    """Schema for password reset"""

    token: str = Field(..., min_length=1)
    new_password: str = Field(
        ..., min_length=8, max_length=72
    )  # bcrypt limit is 72 bytes


class PasswordResetResponse(BaseModel):
    """Response after password reset"""

    message: str = "Password reset successfully"
