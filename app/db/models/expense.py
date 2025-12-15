from datetime import datetime
from typing import Optional, TYPE_CHECKING
from decimal import Decimal
from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Numeric,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from uuid import UUID

from app.core.database import Base, UUIDMixin, TimestampMixin, CompanyMixin
from app.core.types import EnumType

if TYPE_CHECKING:
    from app.db.models.company import Company
    from app.db.models.employee import Employee
    from app.db.models.user import User


class ExpenseStatus(str, enum.Enum):
    """Expense reimbursement status"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REIMBURSED = "reimbursed"


class Expense(Base, UUIDMixin, TimestampMixin, CompanyMixin):
    """
    Expense Reimbursement model - tracks business expenses submitted by employees

    Workflow:
    - Employee submits → status = "pending"
    - HR/Admin approves → status = "approved"
    - HR/Admin rejects → status = "rejected"
    - Later: Payroll integration → status = "reimbursed"
    """

    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'reimbursed')",
            name="ck_expenses_status",
        ),
        CheckConstraint("amount > 0", name="ck_expenses_amount_positive"),
        # Integrity: If rejected, must have rejection_reason
        CheckConstraint(
            "(status = 'rejected' AND rejection_reason IS NOT NULL) OR (status != 'rejected')",
            name="ck_expenses_rejection_integrity",
        ),
        # Integrity: If approved/reimbursed, must have approved_by and approved_at
        CheckConstraint(
            "(status IN ('approved', 'reimbursed') AND approved_by IS NOT NULL AND approved_at IS NOT NULL) OR (status NOT IN ('approved', 'reimbursed'))",
            name="ck_expenses_approval_integrity",
        ),
    )

    employee_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("employees.id", ondelete="RESTRICT", name="fk_expenses_employee"),
        index=True,
        comment="Employee who submitted this expense",
    )
    title: Mapped[str] = mapped_column(
        String(200), index=True, comment="Expense title/description"
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        comment="Expense amount (e.g., 125.50)",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Detailed description of the expense"
    )
    expense_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        comment="Date when the expense was incurred",
    )
    status: Mapped[ExpenseStatus] = mapped_column(
        EnumType(ExpenseStatus, length=50),
        default=ExpenseStatus.PENDING,
        server_default=ExpenseStatus.PENDING.value,
        index=True,
        comment="Current status of the expense reimbursement",
    )
    receipt_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="URL/path to uploaded receipt file (optional)",
    )
    approved_by: Mapped[Optional[UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", name="fk_expenses_approved_by"),
        nullable=True,
        index=True,
        comment="User (HR/Admin) who approved/rejected this expense",
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date when expense was approved/rejected",
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Reason for rejection (if status is rejected)"
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="expenses")
    employee: Mapped["Employee"] = relationship("Employee", back_populates="expenses")
    approver: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[approved_by]
    )

    def __repr__(self) -> str:
        """String representation of Expense"""
        return f"<Expense(id={self.id}, title={self.title}, amount={self.amount}, status={self.status.value})>"
