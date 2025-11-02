from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

from app.models.company import PlanType


class CompanyBase(BaseModel):
    """Base company schema with common fields"""
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr


class CompanyCreate(CompanyBase):
    """Schema for company signup - includes admin user details"""
    # Admin user details
    admin_name: str = Field(..., min_length=1, max_length=100)
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8, max_length=72)  # bcrypt limit is 72 bytes
    plan_type: PlanType = PlanType.FREE


class CompanyResponse(CompanyBase):
    """Schema for company response"""
    id: int
    plan_type: PlanType
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class CompanySignupResponse(BaseModel):
    """Response after company signup - includes company and admin user"""
    company: CompanyResponse
    admin_user: dict  # UserResponse would create circular import, using dict
    message: str = "Company registered successfully. Admin user created."

