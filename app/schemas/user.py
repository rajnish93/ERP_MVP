from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(..., min_length=8, max_length=72)  # bcrypt limit is 72 bytes
    role: UserRole = UserRole.EMPLOYEE


class UserResponse(UserBase):
    """Schema for user response (without sensitive data)"""
    id: int
    company_id: int
    role: UserRole
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str


class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for token data (decoded JWT)"""
    email: Optional[str] = None
    user_id: Optional[int] = None
    company_id: Optional[int] = None
    role: Optional[UserRole] = None

