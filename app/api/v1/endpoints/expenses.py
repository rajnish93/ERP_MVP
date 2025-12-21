import logging
from typing import Optional, Annotated
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from fastapi import (
    APIRouter,
    Depends,
    status,
    Query,
    Form,
    File,
    UploadFile,
)

from app.core.deps import SessionDep, CurrentUser, CurrentCompanyId
from app.core.dependencies import require_role
from app.db.models.user import User, UserRole
from app.db.models.expense import ExpenseStatus
from app.services.expense_service import ExpenseService
from app.schemas.expense import (
    ExpenseRejection,
    ExpenseResponse,
    ExpenseDetailResponse,
    ExpenseListResponse,
    ExpenseSummaryResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: CurrentUser,
    # Form fields
    title: Annotated[str, Form(min_length=1, max_length=200)],
    amount: Annotated[Decimal, Form(gt=0)],
    expense_date: Annotated[datetime, Form()],
    description: Annotated[Optional[str], Form()] = None,
    employee_id: Annotated[Optional[UUID], Form()] = None,
    # File upload
    file: Annotated[Optional[UploadFile], File()] = None,
):
    """
    Submit a new expense with optional receipt file.
    """
    service = ExpenseService(db)
    return await service.create_expense(
        company_id=company_id,
        current_user=current_user,
        title=title,
        amount=amount,
        expense_date=expense_date,
        description=description,
        employee_id=employee_id,
        file=file,
    )


@router.get("/summary", response_model=ExpenseSummaryResponse)
async def get_expense_summary(
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: CurrentUser,
):
    """
    Get expense summary statistics.
    """
    service = ExpenseService(db)
    return await service.get_summary(company_id, current_user)


@router.get("/", response_model=ExpenseListResponse)
async def get_expenses(
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: CurrentUser,
    status_filter: Annotated[
        Optional[ExpenseStatus],
        Query(alias="status", description="Filter by expense status"),
    ] = None,
    employee_id: Annotated[
        Optional[UUID], Query(description="Filter by employee ID")
    ] = None,
    start_date: Annotated[
        Optional[datetime], Query(description="Filter by expense date (start)")
    ] = None,
    end_date: Annotated[
        Optional[datetime], Query(description="Filter by expense date (end)")
    ] = None,
    min_amount: Annotated[
        Optional[Decimal], Query(description="Minimum amount filter")
    ] = None,
    max_amount: Annotated[
        Optional[Decimal], Query(description="Maximum amount filter")
    ] = None,
    search: Annotated[
        Optional[str], Query(description="Search by title or description")
    ] = None,
    skip: Annotated[int, Query(ge=0, description="Skip N items")] = 0,
    limit: Annotated[
        int, Query(ge=1, le=1000, description="Limit items per page")
    ] = 100,
):
    """
    List expenses with filters.
    """
    service = ExpenseService(db)
    expenses, total, total_amount = await service.get_expenses(
        company_id=company_id,
        current_user=current_user,
        status_filter=status_filter,
        employee_id=employee_id,
        start_date=start_date,
        end_date=end_date,
        min_amount=min_amount,
        max_amount=max_amount,
        search=search,
        skip=skip,
        limit=limit,
    )

    return ExpenseListResponse(
        expenses=[ExpenseResponse.model_validate(expense) for expense in expenses],
        total=total,
        total_amount=total_amount,
    )


@router.get("/{expense_id}", response_model=ExpenseDetailResponse)
async def get_expense(
    expense_id: UUID,
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: CurrentUser,
):
    """
    Get expense details by ID.
    """
    service = ExpenseService(db)
    expense = await service.get_expense_by_id(company_id, current_user, expense_id)

    # Manual mapping for detail response to ensure relationships are serialized correctly
    employee_data = None
    if expense.employee:
        employee_data = {
            "id": str(expense.employee.id),
            "name": expense.employee.name,
            "department": expense.employee.department,
            "role": expense.employee.role,
            "employee_id": expense.employee.employee_id,
        }

    approver_data = None
    if expense.approver:
        approver_data = {
            "id": str(expense.approver.id),
            "full_name": expense.approver.full_name,
            "email": expense.approver.email,
            "role": expense.approver.role.value,
        }

    response = ExpenseResponse.model_validate(expense)
    return ExpenseDetailResponse(
        **response.model_dump(), employee=employee_data, approver=approver_data
    )


@router.patch("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: UUID,
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: CurrentUser,
    # Form fields (all optional for patch)
    title: Annotated[Optional[str], Form(min_length=1, max_length=200)] = None,
    amount: Annotated[Optional[Decimal], Form(gt=0)] = None,
    expense_date: Annotated[Optional[datetime], Form()] = None,
    description: Annotated[Optional[str], Form()] = None,
    # File handling
    file: Annotated[Optional[UploadFile], File()] = None,
    clear_receipt: Annotated[bool, Form()] = False,
):
    """
    Update an expense.
    """
    service = ExpenseService(db)
    return await service.update_expense(
        company_id=company_id,
        current_user=current_user,
        expense_id=expense_id,
        title=title,
        amount=amount,
        expense_date=expense_date,
        description=description,
        file=file,
        clear_receipt=clear_receipt,
    )


@router.post("/{expense_id}/approve", response_model=ExpenseResponse)
async def approve_expense(
    expense_id: UUID,
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.HR))],
):
    """
    Approve an expense.
    """
    service = ExpenseService(db)
    return await service.approve_expense(company_id, current_user.id, expense_id)


@router.post("/{expense_id}/reject", response_model=ExpenseResponse)
async def reject_expense(
    expense_id: UUID,
    rejection_data: ExpenseRejection,
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.HR))],
):
    """
    Reject an expense.
    """
    service = ExpenseService(db)
    return await service.reject_expense(
        company_id, current_user.id, expense_id, rejection_data.rejection_reason
    )


@router.post("/{expense_id}/reimburse", response_model=ExpenseResponse)
async def reimburse_expense(
    expense_id: UUID,
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.HR))],
):
    """
    Reimburse an expense.
    """
    service = ExpenseService(db)
    return await service.reimburse_expense(company_id, current_user.id, expense_id)


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: UUID,
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: CurrentUser,
):
    """
    Delete an expense.
    """
    service = ExpenseService(db)
    await service.delete_expense(company_id, current_user, expense_id)
