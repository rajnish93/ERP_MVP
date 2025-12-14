from typing import Optional
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from app.db.models.expense import ExpenseStatus


class ExpenseBase(BaseModel):
    """Base expense schema with common fields"""

    title: str = Field(
        ..., min_length=1, max_length=200, description="Expense title/description"
    )
    amount: Decimal = Field(
        ..., gt=0, decimal_places=2, description="Expense amount (must be positive)"
    )
    description: Optional[str] = Field(
        None, description="Detailed description of the expense"
    )
    expense_date: datetime = Field(
        ..., description="Date when the expense was incurred"
    )
    receipt_url: Optional[str] = Field(
        None, max_length=500, description="URL/path to uploaded receipt file (optional)"
    )


class ExpenseCreate(ExpenseBase):
    """Schema for creating/submitting a new expense"""

    employee_id: Optional[UUID] = Field(
        None, description="Employee ID (auto-set from current user's employee record)"
    )


class ExpenseUpdate(BaseModel):
    """Schema for updating an expense (employees can only update pending expenses)"""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    description: Optional[str] = None
    expense_date: Optional[datetime] = None
    receipt_url: Optional[str] = Field(None, max_length=500)


class ExpenseApproval(BaseModel):
    """Schema for approving an expense"""

    rejection_reason: Optional[str] = Field(
        None, description="Reason for rejection (required if rejecting)"
    )


class ExpenseRejection(BaseModel):
    """Schema for rejecting an expense"""

    rejection_reason: str = Field(..., min_length=1, description="Reason for rejection")


class ExpenseResponse(ExpenseBase):
    """Schema for expense response"""

    id: UUID
    company_id: UUID
    employee_id: UUID
    employee_name: Optional[str] = Field(None, description="Employee name")
    employee_code: Optional[str] = Field(
        None, description="Employee ID code (e.g. EMP-001)"
    )
    status: ExpenseStatus
    approved_by: Optional[UUID] = Field(
        None, description="User ID who approved/rejected"
    )
    approved_at: Optional[datetime] = Field(
        None, description="Date when expense was approved/rejected"
    )
    rejection_reason: Optional[str] = Field(None, description="Reason for rejection")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExpenseDetailResponse(ExpenseResponse):
    """Extended expense response with employee details"""

    employee: Optional[dict] = Field(
        None, description="Employee details who submitted the expense"
    )
    approver: Optional[dict] = Field(
        None, description="Approver user details if approved/rejected"
    )

    model_config = ConfigDict(from_attributes=True)


class ExpenseListResponse(BaseModel):
    """Response schema for expense list"""

    expenses: list[ExpenseResponse]
    total: int
    total_amount: Decimal = Field(
        ..., description="Total amount of expenses in the list"
    )


class ExpenseSummaryResponse(BaseModel):
    """Response schema for expense summary statistics"""

    total_expenses: int = Field(..., description="Total number of expenses")
    total_amount: Decimal = Field(..., description="Total amount of all expenses")
    pending_expenses: int = Field(..., description="Total number of pending expenses")
    pending_amount: Decimal = Field(..., description="Total amount of pending expenses")
    approved_expenses: int = Field(..., description="Total number of approved expenses")
    approved_amount: Decimal = Field(
        ..., description="Total amount of approved expenses"
    )
    rejected_expenses: int = Field(..., description="Total number of rejected expenses")
    rejected_amount: Decimal = Field(
        ..., description="Total amount of rejected expenses"
    )
    reimbursed_expenses: int = Field(
        ..., description="Total number of reimbursed expenses"
    )
    reimbursed_amount: Decimal = Field(
        ..., description="Total amount of reimbursed expenses"
    )
