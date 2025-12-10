from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.db.models.company import PlanType


class CompanyBase(BaseModel):
    """Base company schema with common fields"""
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    slug: str = Field(..., min_length=1, max_length=50)


class CompanyCreate(CompanyBase):
    """Schema for company signup - includes admin user details"""
    # Admin user details
    admin_name: str = Field(..., min_length=1, max_length=100)
    admin_email: EmailStr
    admin_password: str = Field(
        ..., 
        min_length=8, 
        max_length=72,
        description="Admin password must be at least 8 characters long",
        json_schema_extra={
            "example": "SecurePassword123!"
        }
    )  # bcrypt limit is 72 bytes
    plan_type: PlanType = PlanType.FREE


class CompanyResponse(CompanyBase):
    """Schema for company response"""
    id: UUID
    plan_type: PlanType
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class CompanySignupResponse(BaseModel):
    """Response after company signup - includes company and admin user"""
    company: CompanyResponse
    admin_user: dict  # UserResponse would create circular import, using dict
    message: str = "Company registered successfully. Admin user created."

