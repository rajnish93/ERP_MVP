from datetime import datetime
from typing import TYPE_CHECKING, List
from sqlalchemy import String, Boolean, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum
import uuid

from app.core.database import Base
from app.core.types import EnumType

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.employee import Employee


class PlanType(str, enum.Enum):
    """Company subscription plan types"""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Company(Base):
    """Company (Tenant) model for multi-tenant SaaS"""
    __tablename__ = "companies"
    __table_args__ = (
        CheckConstraint(
            "plan_type IN ('free', 'pro', 'enterprise')",
            name="check_plan_type"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4, 
        index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    plan_type: Mapped[PlanType] = mapped_column(
        EnumType(PlanType, length=20),
        nullable=False,
        default=PlanType.FREE,
        server_default=PlanType.FREE.value
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
    users: Mapped[List["User"]] = relationship("User", back_populates="company", cascade="all, delete-orphan")
    employees: Mapped[List["Employee"]] = relationship("Employee", back_populates="company", cascade="all, delete-orphan")

