from typing import Optional
from datetime import datetime


class Employee:
    """Employee model - linked to user account and company (tenant)"""
    
    def __init__(
        self,
        id: int,
        company_id: int,  # Tenant isolation - employee belongs to a company
        user_id: int,  # Link to User account (one-to-one relationship)
        name: str,
        department: str,
        role: str,  # Job role/title (e.g., "Software Engineer", "Manager")
        joining_date: datetime,
        employee_id: Optional[str] = None,  # Optional employee ID/code
        phone: Optional[str] = None,
        is_active: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.company_id = company_id  # Critical for tenant isolation
        self.user_id = user_id  # Link to User account
        self.name = name
        self.department = department
        self.role = role
        self.joining_date = joining_date
        self.employee_id = employee_id  # Employee ID/code (e.g., "EMP001")
        self.phone = phone
        self.is_active = is_active
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    def to_dict(self):
        """Convert employee to dictionary"""
        return {
            "id": self.id,
            "company_id": self.company_id,
            "user_id": self.user_id,
            "name": self.name,
            "department": self.department,
            "role": self.role,
            "joining_date": self.joining_date.isoformat() if self.joining_date else None,
            "employee_id": self.employee_id,
            "phone": self.phone,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# In-memory employee storage (replace with database later)
employees_db: list[Employee] = []
next_employee_id = 1

