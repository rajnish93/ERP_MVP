from enum import Enum
from typing import Optional
from datetime import datetime


class UserRole(str, Enum):
    """User roles in the system"""
    ADMIN = "admin"
    HR = "hr"
    EMPLOYEE = "employee"


class User:
    """User model for multi-tenant SaaS - belongs to a company"""
    
    def __init__(
        self,
        id: int,
        company_id: int,  # Foreign key to Company (tenant isolation)
        email: str,
        hashed_password: str,
        full_name: str,
        role: UserRole = UserRole.EMPLOYEE,
        is_active: bool = True,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.company_id = company_id  # Critical for tenant isolation
        self.email = email
        self.hashed_password = hashed_password
        self.full_name = full_name
        self.role = role
        self.is_active = is_active
        self.created_at = created_at or datetime.utcnow()
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            "id": self.id,
            "company_id": self.company_id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# In-memory user storage (replace with database later)
users_db: list[User] = []
next_user_id = 1

