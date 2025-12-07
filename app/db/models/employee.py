from datetime import datetime
from typing import Optional, TYPE_CHECKING, List
from sqlalchemy import String, Boolean, DateTime, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID

from app.core.database import Base, UUIDMixin, TimestampMixin, CompanyMixin

if TYPE_CHECKING:
    from app.db.models.company import Company
    from app.db.models.user import User
    from app.db.models.asset import Asset
    from app.db.models.expense import Expense


class Employee(Base, UUIDMixin, TimestampMixin, CompanyMixin):
    """
    Employee model - linked to user account and company (tenant)
    
    **Important Notes:**
    - `user_id` is OPTIONAL - employees can exist without user accounts
      (e.g., employees not yet onboarded to the portal)
    - `employee_id` is OPTIONAL - human-readable employee code (e.g., "EMP-001")
    - All users must have employee records, but employees can exist without user accounts
    - When downgrading migrations, employees with NULL user_id must be handled/deleted
    """
    __tablename__ = "employees"
    __table_args__ = (
        UniqueConstraint('user_id', name='uq_employees_user_id'),
    )

    user_id: Mapped[Optional[UUID]] = mapped_column(
        Uuid(as_uuid=True), 
        ForeignKey("users.id", ondelete="SET NULL", name="fk_employees_user"), 
        nullable=True, 
        index=True,
        comment="Optional user account ID. NULL means employee exists but doesn't have login credentials yet. "
                "When downgrading migrations that require NOT NULL, these records must be handled/deleted."
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    role: Mapped[str] = mapped_column(
        String(100), 
        nullable=False, 
        index=True, 
        comment="Job role/title"
    )
    joining_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    employee_id: Mapped[Optional[str]] = mapped_column(
        String(50), 
        nullable=True, 
        unique=True, 
        index=True, 
        comment="Optional employee ID/code"
    )
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="employees")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="employee")
    assets: Mapped[List["Asset"]] = relationship("Asset", back_populates="employee")
    expenses: Mapped[List["Expense"]] = relationship("Expense", back_populates="employee")

