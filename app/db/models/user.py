from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum
import uuid

from app.core.database import Base
from app.core.types import EnumType

if TYPE_CHECKING:
    from app.db.models.company import Company
    from app.db.models.employee import Employee


class UserRole(str, enum.Enum):
    """User roles in the system"""
    ADMIN = "admin"
    HR = "hr"
    EMPLOYEE = "employee"


class User(Base):
    """User model for multi-tenant SaaS - belongs to a company"""
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'hr', 'employee')",
            name="ck_users_role"
        ),
        UniqueConstraint('company_id', 'email', name='uq_users_company_email'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4, 
        index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("companies.id", ondelete="CASCADE", name="fk_users_company"), 
        nullable=False, 
        index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        EnumType(UserRole, length=100),
        nullable=False,
        default=UserRole.EMPLOYEE,
        server_default=UserRole.EMPLOYEE.value,
        index=True,
        comment="User role (admin, hr, employee) - indexed for fast role-based access control queries"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="users")
    employee: Mapped[Optional["Employee"]] = relationship(
        "Employee", 
        back_populates="user", 
        uselist=False
    )

