from typing import TYPE_CHECKING, List
from sqlalchemy import String, Boolean, CheckConstraint, UniqueConstraint, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base, UUIDMixin, TimestampMixin
from app.core.types import EnumType

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.employee import Employee
    from app.db.models.asset import Asset
    from app.db.models.expense import Expense


class PlanType(str, enum.Enum):
    """Company subscription plan types"""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Company(Base, UUIDMixin, TimestampMixin):
    """Company (Tenant) model for multi-tenant SaaS"""
    __tablename__ = "companies"
    __table_args__ = (
        PrimaryKeyConstraint('id', name='pk_companies_id'),
        CheckConstraint(
            "plan_type IN ('free', 'pro', 'enterprise')",
            name="ck_companies_plan_type"
        ),
        UniqueConstraint('email', name='uq_companies_email'),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    plan_type: Mapped[PlanType] = mapped_column(
        EnumType(PlanType, length=100),
        nullable=False,
        default=PlanType.FREE,
        server_default=PlanType.FREE.value
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    users: Mapped[List["User"]] = relationship("User", back_populates="company", cascade="all, delete-orphan")
    employees: Mapped[List["Employee"]] = relationship("Employee", back_populates="company", cascade="all, delete-orphan")
    assets: Mapped[List["Asset"]] = relationship("Asset", back_populates="company", cascade="all, delete-orphan")
    expenses: Mapped[List["Expense"]] = relationship("Expense", back_populates="company", cascade="all, delete-orphan")

