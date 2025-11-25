from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class EmployeeBase(BaseModel):
    """Base employee schema with common fields"""
    name: str = Field(..., min_length=1, max_length=200)
    department: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., min_length=1, max_length=100, description="Job role/title")
    joining_date: datetime = Field(..., description="Employee joining date")
    employee_id: Optional[str] = Field(None, max_length=50, description="Optional employee ID/code")
    phone: Optional[str] = Field(None, max_length=20)


class EmployeeCreate(EmployeeBase):
    """Schema for creating a new employee"""
    user_id: Optional[UUID] = Field(None, description="Optional user account ID to link employee to. Employees can exist without user accounts.")


class EmployeeUpdate(BaseModel):
    """Schema for updating an employee (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    department: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[str] = Field(None, min_length=1, max_length=100)
    joining_date: Optional[datetime] = None
    employee_id: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    user_id: Optional[UUID] = Field(None, description="Optional user account ID to link employee to")
    is_active: Optional[bool] = None


class EmployeeResponse(EmployeeBase):
    """Schema for employee response"""
    id: UUID
    company_id: UUID
    user_id: Optional[UUID]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class EmployeeListResponse(BaseModel):
    """Response schema for employee list with pagination info"""
    employees: list[EmployeeResponse]
    total: int

