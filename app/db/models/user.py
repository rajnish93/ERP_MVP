from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
import enum
from app.core.database import Base, UUIDMixin, TimestampMixin, CompanyMixin
from app.core.types import EnumType

if TYPE_CHECKING:
    from app.db.models.company import Company
    from app.db.models.employee import Employee


class UserRole(str, enum.Enum):
    """User roles in the system"""
    ADMIN = "admin"
    HR = "hr"
    EMPLOYEE = "employee"


class User(Base, UUIDMixin, TimestampMixin, CompanyMixin):
    """User model for multi-tenant SaaS - belongs to a company"""
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("company_id", "email", name="uq_users_company_email"),
        Index("ix_company_email", "company_id", "email"),
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        EnumType(UserRole),
        default=UserRole.EMPLOYEE,
        server_default=UserRole.EMPLOYEE.value,
        index=True,
        comment="User role (admin, hr, employee) - indexed for fast role-based access control queries"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="users")
    employee: Mapped[Optional["Employee"]] = relationship(
        "Employee",
        back_populates="user",
        uselist=False,
    )

    @validates("email")
    def validate_email(self, key, value: str) -> str:
        return value.strip().lower()
