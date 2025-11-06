from datetime import datetime
from typing import Optional, TYPE_CHECKING
from decimal import Decimal
from sqlalchemy import String, DateTime, ForeignKey, CheckConstraint, Numeric, Text
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


class ExpenseStatus(str, enum.Enum):
    """Expense reimbursement status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REIMBURSED = "reimbursed"


class Expense(Base):
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
            name="ck_expenses_status"
        ),
        CheckConstraint("amount >= 0", name="ck_expenses_amount_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4, 
        index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("companies.id", ondelete="CASCADE", name="fk_expenses_company"), 
        nullable=False, 
        index=True,
        comment="Company (tenant) this expense belongs to"
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("employees.id", ondelete="CASCADE", name="fk_expenses_employee"), 
        nullable=False, 
        index=True,
        comment="Employee who submitted this expense"
    )
    title: Mapped[str] = mapped_column(
        String(200), 
        nullable=False, 
        index=True,
        comment="Expense title/description"
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False,
        comment="Expense amount (e.g., 125.50)"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True,
        comment="Detailed description of the expense"
    )
    expense_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False,
        index=True,
        comment="Date when the expense was incurred"
    )
    status: Mapped[ExpenseStatus] = mapped_column(
        EnumType(ExpenseStatus, length=50),
        nullable=False,
        default=ExpenseStatus.PENDING,
        server_default=ExpenseStatus.PENDING.value,
        index=True,
        comment="Current status of the expense reimbursement"
    )
    receipt_url: Mapped[Optional[str]] = mapped_column(
        String(500), 
        nullable=True,
        comment="URL/path to uploaded receipt file (optional)"
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="SET NULL", name="fk_expenses_approved_by"), 
        nullable=True,
        comment="User (HR/Admin) who approved/rejected this expense"
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Date when expense was approved/rejected"
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Reason for rejection (if status is rejected)"
    )
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
    company: Mapped["Company"] = relationship("Company", back_populates="expenses")
    employee: Mapped["Employee"] = relationship("Employee", back_populates="expenses")
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by])
    
    def __repr__(self) -> str:
        """String representation of Expense"""
        return f"<Expense(id={self.id}, title={self.title}, amount={self.amount}, status={self.status.value})>"


