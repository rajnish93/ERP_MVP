from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
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
        CheckConstraint(
            "role IN ('admin', 'hr', 'employee')",
            name="ck_users_role"
        ),
        UniqueConstraint('company_id', 'email', name='uq_users_company_email'),
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        EnumType(UserRole, length=100),
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
        uselist=False
    )

