from typing import TYPE_CHECKING, List
from sqlalchemy import (
    String,
    Boolean,
    CheckConstraint,
    PrimaryKeyConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
import enum
import re

from app.core.database import Base, UUIDMixin, TimestampMixin
from app.core.types import EnumType

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.employee import Employee
    from app.db.models.asset import Asset
    from app.db.models.expense import Expense


SLUG_REGEX_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class PlanType(str, enum.Enum):
    """Company subscription plan types"""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Company(Base, UUIDMixin, TimestampMixin):
    """Company model for multi-workspace SaaS"""

    __tablename__ = "companies"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_companies_id"),
        CheckConstraint(
            "plan_type IN ('free', 'pro', 'enterprise')", name="ck_companies_plan_type"
        ),
        CheckConstraint(
            f"slug ~ '{SLUG_REGEX_PATTERN}'", name="ck_companies_slug_format"
        ),
    )

    name: Mapped[str] = mapped_column(String(200), index=True)
    slug: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        comment="URL-friendly identifier (e.g. test-corp)",
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    plan_type: Mapped[PlanType] = mapped_column(
        EnumType(PlanType, length=100),
        default=PlanType.FREE,
        server_default=PlanType.FREE.value,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    users: Mapped[List["User"]] = relationship(
        "User", back_populates="company", cascade="all, delete-orphan"
    )
    employees: Mapped[List["Employee"]] = relationship(
        "Employee", back_populates="company", cascade="all, delete-orphan"
    )
    assets: Mapped[List["Asset"]] = relationship(
        "Asset", back_populates="company", cascade="all, delete-orphan"
    )
    expenses: Mapped[List["Expense"]] = relationship(
        "Expense", back_populates="company", cascade="all, delete-orphan"
    )

    @validates("slug")
    def validate_slug(self, key, slug):
        """Validate slug format: lowercase alphanumeric with hyphens"""
        if not slug:
            raise ValueError("Slug cannot be empty")

        # Check format: lowercase letters, numbers, and hyphens only
        if not re.match(SLUG_REGEX_PATTERN, slug):
            raise ValueError(
                "Slug must contain only lowercase letters, numbers, and hyphens. "
                "It cannot start or end with a hyphen."
            )

        return slug.lower()
