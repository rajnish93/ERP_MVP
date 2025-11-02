from typing import Optional
from datetime import datetime
from enum import Enum


class PlanType(str, Enum):
    """Company subscription plan types"""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Company:
    """Company (Tenant) model for multi-tenant SaaS"""
    
    def __init__(
        self,
        id: int,
        name: str,
        email: str,
        plan_type: PlanType = PlanType.FREE,
        is_active: bool = True,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.name = name
        self.email = email
        self.plan_type = plan_type
        self.is_active = is_active
        self.created_at = created_at or datetime.utcnow()
    
    def to_dict(self):
        """Convert company to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "plan_type": self.plan_type.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# In-memory company storage (replace with database later)
companies_db: list[Company] = []
next_company_id = 1

