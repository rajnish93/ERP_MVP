from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.db.models.user import UserRole


class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)


class UserCreate(UserBase):
    """Schema for creating a new user (inviting employee to portal)"""
    password: str = Field(..., min_length=8, max_length=72)  # bcrypt limit is 72 bytes
    role: UserRole = UserRole.EMPLOYEE
    # Link to existing employee (if inviting an employee who already has an employee record)
    employee_id: Optional[UUID] = Field(None, description="Optional: Link to existing employee record by employee UUID")
    # Or create employee record if not linking (only used if employee_id is not provided)
    department: Optional[str] = Field(None, min_length=1, max_length=100, description="Department name (used if creating new employee record)")
    job_role: Optional[str] = Field(None, min_length=1, max_length=100, description="Job role/title (used if creating new employee record)")
    joining_date: Optional[datetime] = Field(None, description="Employee joining date (used if creating new employee record)")


class UserResponse(UserBase):
    """Schema for user response (without sensitive data)"""
    id: UUID
    company_id: UUID
    role: UserRole
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


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
    user_id: Optional[UUID] = None
    company_id: Optional[UUID] = None
    role: Optional[UserRole] = None

