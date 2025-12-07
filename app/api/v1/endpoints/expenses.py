from typing import Optional
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import or_, func as sql_func, select

from app.core.deps import SessionDep, CurrentUser, CurrentCompanyId
from app.core.error_handlers import handle_db_operation
from app.db.models.expense import Expense, ExpenseStatus
from app.db.models.employee import Employee
from app.db.models.user import User, UserRole
from app.core.dependencies import require_role
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseRejection,
    ExpenseResponse,
    ExpenseDetailResponse,
    ExpenseListResponse,
    ExpenseSummaryResponse,
)

router = APIRouter()


@router.post("/", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    expense_data: ExpenseCreate,
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: CurrentUser,
):
    """
    Submit a new expense for reimbursement.
    
    **Access**: All authenticated users (must have employee record)
    
    **Workflow**: Expense is created with status="pending" and requires HR/Admin approval.
    
    **Request**:
    - title: Expense title
    - amount: Expense amount (must be positive)
    - description: Optional detailed description
    - expense_date: Date when expense was incurred
    - receipt_url: Optional URL/path to receipt file
    """
    # Get employee record for current user
    stmt = select(Employee).where(
        Employee.user_id == current_user.id,
        Employee.company_id == company_id
    )
    employee = (await db.execute(stmt)).scalars().first()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee record not found. Please contact HR to create your employee profile."
        )
    
    # Use employee_id from request or current user's employee record
    employee_id = expense_data.employee_id if expense_data.employee_id else employee.id
    
    # Verify employee belongs to same company
    if employee_id != employee.id:
        # Only HR/Admin can submit expenses for other employees
        if current_user.role == UserRole.EMPLOYEE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only submit expenses for yourself"
            )
        
        stmt = select(Employee).where(
            Employee.id == employee_id,
            Employee.company_id == company_id
        )
        employee_check = (await db.execute(stmt)).scalars().first()
        if not employee_check:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot submit expense for employee from another company"
            )
    
    # Create new expense with pending status
    new_expense = Expense(
        company_id=company_id,
        employee_id=employee_id,
        title=expense_data.title,
        amount=expense_data.amount,
        description=expense_data.description,
        expense_date=expense_data.expense_date,
        status=ExpenseStatus.PENDING,
        receipt_url=expense_data.receipt_url,
        approved_by=None,
        approved_at=None,
        rejection_reason=None,
    )
    async with handle_db_operation(db, "create expense"):
        await db.add(new_expense)
        await db.commit()
        await db.refresh(new_expense)
    
    return ExpenseResponse(
        id=new_expense.id,
        company_id=new_expense.company_id,
        employee_id=new_expense.employee_id,
        title=new_expense.title,
        amount=new_expense.amount,
        description=new_expense.description,
        expense_date=new_expense.expense_date,
        status=new_expense.status,
        receipt_url=new_expense.receipt_url,
        approved_by=new_expense.approved_by,
        approved_at=new_expense.approved_at,
        rejection_reason=new_expense.rejection_reason,
        created_at=new_expense.created_at,
        updated_at=new_expense.updated_at,
    )


@router.get("/summary", response_model=ExpenseSummaryResponse)
async def get_expense_summary(
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: CurrentUser,
):
    """
    Get expense summary statistics (total expenses and pending expenses).
    
    **Access**: 
    - Employees: Can only see their own expense statistics
    - HR/Admin: Can see all expense statistics for their company
    
    **Returns**:
    - Total expenses count and amount
    - Pending expenses count and amount
    - Approved expenses count and amount
    - Rejected expenses count and amount
    - Reimbursed expenses count and amount
    """
    # Base conditions - company isolated
    conditions = [Expense.company_id == company_id]
    
    # Employees can only see their own expenses
    if current_user.role == UserRole.EMPLOYEE:
        stmt = select(Employee).where(
            Employee.user_id == current_user.id,
            Employee.company_id == company_id
        )
        employee = (await db.execute(stmt)).scalars().first()
        
        if not employee:
            return ExpenseSummaryResponse(
                total_expenses=0,
                total_amount=Decimal("0.00"),
                pending_expenses=0,
                pending_amount=Decimal("0.00"),
                approved_expenses=0,
                approved_amount=Decimal("0.00"),
                rejected_expenses=0,
                rejected_amount=Decimal("0.00"),
                reimbursed_expenses=0,
                reimbursed_amount=Decimal("0.00"),
            )
        
        conditions.append(Expense.employee_id == employee.id)
    
    # Helper to get stats
    async def get_stats(extra_conds=None):
        where_conds = conditions + (extra_conds or [])
        count_stmt = select(sql_func.count(Expense.id)).where(*where_conds)
        sum_stmt = select(sql_func.sum(Expense.amount)).where(*where_conds)
        
        count = (await db.execute(count_stmt)).scalar() or 0
        amount = (await db.execute(sum_stmt)).scalar() or Decimal("0.00")
        return count, amount

    # Get total expenses count and amount
    total_expenses, total_amount = await get_stats()
    
    # Get pending expenses count and amount
    pending_expenses, pending_amount = await get_stats([Expense.status == ExpenseStatus.PENDING])
    
    # Get approved expenses count and amount
    approved_expenses, approved_amount = await get_stats([Expense.status == ExpenseStatus.APPROVED])
    
    # Get rejected expenses count and amount
    rejected_expenses, rejected_amount = await get_stats([Expense.status == ExpenseStatus.REJECTED])
    
    # Get reimbursed expenses count and amount
    reimbursed_expenses, reimbursed_amount = await get_stats([Expense.status == ExpenseStatus.REIMBURSED])
    
    return ExpenseSummaryResponse(
        total_expenses=total_expenses,
        total_amount=total_amount,
        pending_expenses=pending_expenses,
        pending_amount=pending_amount,
        approved_expenses=approved_expenses,
        approved_amount=approved_amount,
        rejected_expenses=rejected_expenses,
        rejected_amount=rejected_amount,
        reimbursed_expenses=reimbursed_expenses,
        reimbursed_amount=reimbursed_amount,
    )


@router.get("/", response_model=ExpenseListResponse)
async def get_expenses(
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: CurrentUser,
    status_filter: Optional[ExpenseStatus] = Query(None, alias="status", description="Filter by expense status"),
    employee_id: Optional[UUID] = Query(None, description="Filter by employee ID"),
    start_date: Optional[datetime] = Query(None, description="Filter by expense date (start)"),
    end_date: Optional[datetime] = Query(None, description="Filter by expense date (end)"),
    min_amount: Optional[Decimal] = Query(None, description="Minimum amount filter"),
    max_amount: Optional[Decimal] = Query(None, description="Maximum amount filter"),
    search: Optional[str] = Query(None, description="Search by title or description"),
):
    """
    List expenses.
    
    **Access**: 
    - Employees: Can only see their own expenses
    - HR/Admin: Can see all expenses for their company
    
    **Filters**:
    - status: Filter by expense status
    - employee_id: Filter by employee (HR/Admin only)
    - start_date/end_date: Filter by expense date range
    - min_amount/max_amount: Filter by amount range
    - search: Search by title or description
    """
    # Base conditions - company isolated
    conditions = [Expense.company_id == company_id]
    
    # Employees can only see their own expenses
    if current_user.role == UserRole.EMPLOYEE:
        stmt = select(Employee).where(
            Employee.user_id == current_user.id,
            Employee.company_id == company_id
        )
        employee = (await db.execute(stmt)).scalars().first()
        
        if not employee:
            return ExpenseListResponse(expenses=[], total=0, total_amount=Decimal("0.00"))
        
        conditions.append(Expense.employee_id == employee.id)
    elif employee_id:
        # HR/Admin can filter by employee
        conditions.append(Expense.employee_id == employee_id)
    
    # Apply filters
    if status_filter:
        conditions.append(Expense.status == status_filter)
    
    if start_date:
        conditions.append(Expense.expense_date >= start_date)
    
    if end_date:
        conditions.append(Expense.expense_date <= end_date)
    
    if min_amount:
        conditions.append(Expense.amount >= min_amount)
    
    if max_amount:
        conditions.append(Expense.amount <= max_amount)
    
    if search:
        search_term = f"%{search}%"
        conditions.append(
            or_(
                Expense.title.ilike(search_term),
                Expense.description.ilike(search_term)
            )
        )
    
    # Get total count
    count_stmt = select(sql_func.count(Expense.id)).where(*conditions)
    total = (await db.execute(count_stmt)).scalar() or 0
    
    # Calculate total amount
    sum_stmt = select(sql_func.sum(Expense.amount)).where(*conditions)
    total_amount = (await db.execute(sum_stmt)).scalar() or Decimal("0.00")
    
    # Get expenses
    stmt = select(Expense).where(*conditions).order_by(Expense.created_at.desc())
    expenses = (await db.execute(stmt)).scalars().all()
    
    return ExpenseListResponse(
        expenses=[
            ExpenseResponse(
                id=expense.id,
                company_id=expense.company_id,
                employee_id=expense.employee_id,
                title=expense.title,
                amount=expense.amount,
                description=expense.description,
                expense_date=expense.expense_date,
                status=expense.status,
                receipt_url=expense.receipt_url,
                approved_by=expense.approved_by,
                approved_at=expense.approved_at,
                rejection_reason=expense.rejection_reason,
                created_at=expense.created_at,
                updated_at=expense.updated_at,
            )
            for expense in expenses
        ],
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
    
    **Access**: 
    - Employees: Can only view their own expenses
    - HR/Admin: Can view any expense in their company
    """
    stmt = select(Expense).where(
        Expense.id == expense_id,
        Expense.company_id == company_id
    )
    expense = (await db.execute(stmt)).scalars().first()
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    # Employees can only see their own expenses
    if current_user.role == UserRole.EMPLOYEE:
        stmt = select(Employee).where(
            Employee.user_id == current_user.id,
            Employee.company_id == company_id
        )
        employee = (await db.execute(stmt)).scalars().first()
        
        if not employee or expense.employee_id != employee.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only view your own expenses."
            )
    
    # Get employee details
    stmt = select(Employee).where(Employee.id == expense.employee_id)
    employee = (await db.execute(stmt)).scalars().first()
    employee_data = None
    if employee:
        employee_data = {
            "id": str(employee.id),
            "name": employee.name,
            "department": employee.department,
            "role": employee.role,
            "employee_id": employee.employee_id,
        }
    
    # Get approver details
    approver_data = None
    if expense.approved_by:
        stmt = select(User).where(User.id == expense.approved_by)
        approver = (await db.execute(stmt)).scalars().first()
        if approver:
            approver_data = {
                "id": str(approver.id),
                "full_name": approver.full_name,
                "email": approver.email,
                "role": approver.role.value,
            }
    
    return ExpenseDetailResponse(
        id=expense.id,
        company_id=expense.company_id,
        employee_id=expense.employee_id,
        title=expense.title,
        amount=expense.amount,
        description=expense.description,
        expense_date=expense.expense_date,
        status=expense.status,
        receipt_url=expense.receipt_url,
        approved_by=expense.approved_by,
        approved_at=expense.approved_at,
        rejection_reason=expense.rejection_reason,
        created_at=expense.created_at,
        updated_at=expense.updated_at,
        employee=employee_data,
        approver=approver_data,
    )


@router.patch("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: UUID,
    expense_data: ExpenseUpdate,
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: CurrentUser,
):
    """
    Update an expense.
    
    **Access**: Employees can only update their own pending expenses.
                  HR/Admin can update any expense.
    
    **Note**: Once approved or rejected, expenses cannot be updated by employees.
    """
    stmt = select(Expense).where(
        Expense.id == expense_id,
        Expense.company_id == company_id
    )
    expense = (await db.execute(stmt)).scalars().first()
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    # Employees can only update their own pending expenses
    if current_user.role == UserRole.EMPLOYEE:
        stmt = select(Employee).where(
            Employee.user_id == current_user.id,
            Employee.company_id == company_id
        )
        employee = (await db.execute(stmt)).scalars().first()
        
        if not employee or expense.employee_id != employee.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only update your own expenses."
            )
        
        if expense.status != ExpenseStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update expense with status '{expense.status.value}'. Only pending expenses can be updated."
            )
    
    # Update fields
    update_data = expense_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(expense, field, value)
    
    async with handle_db_operation(db, "update expense"):
        await db.commit()
        await db.refresh(expense)
    
    return ExpenseResponse(
        id=expense.id,
        company_id=expense.company_id,
        employee_id=expense.employee_id,
        title=expense.title,
        amount=expense.amount,
        description=expense.description,
        expense_date=expense.expense_date,
        status=expense.status,
        receipt_url=expense.receipt_url,
        approved_by=expense.approved_by,
        approved_at=expense.approved_at,
        rejection_reason=expense.rejection_reason,
        created_at=expense.created_at,
        updated_at=expense.updated_at,
    )


@router.post("/{expense_id}/approve", response_model=ExpenseResponse)
async def approve_expense(
    expense_id: UUID,
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.HR)),
):
    """
    Approve an expense for reimbursement.
    
    **Access**: Admin and HR only
    
    **Workflow**: Changes status from "pending" to "approved".
                 Sets approved_by and approved_at fields.
    """
    stmt = select(Expense).where(
        Expense.id == expense_id,
        Expense.company_id == company_id
    )
    expense = (await db.execute(stmt)).scalars().first()
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    if expense.status != ExpenseStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve expense with status '{expense.status.value}'. Only pending expenses can be approved."
        )
    
    # Approve expense
    expense.status = ExpenseStatus.APPROVED
    expense.approved_by = current_user.id
    expense.approved_at = datetime.now(timezone.utc)
    expense.rejection_reason = None  # Clear any previous rejection reason
    
    async with handle_db_operation(db, "approve expense"):
        await db.commit()
        await db.refresh(expense)
    
    return ExpenseResponse(
        id=expense.id,
        company_id=expense.company_id,
        employee_id=expense.employee_id,
        title=expense.title,
        amount=expense.amount,
        description=expense.description,
        expense_date=expense.expense_date,
        status=expense.status,
        receipt_url=expense.receipt_url,
        approved_by=expense.approved_by,
        approved_at=expense.approved_at,
        rejection_reason=expense.rejection_reason,
        created_at=expense.created_at,
        updated_at=expense.updated_at,
    )


@router.post("/{expense_id}/reject", response_model=ExpenseResponse)
async def reject_expense(
    expense_id: UUID,
    rejection_data: ExpenseRejection,
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.HR)),
):
    """
    Reject an expense.
    
    **Access**: Admin and HR only
    
    **Workflow**: Changes status from "pending" to "rejected".
                 Sets approved_by, approved_at, and rejection_reason fields.
    """
    stmt = select(Expense).where(
        Expense.id == expense_id,
        Expense.company_id == company_id
    )
    expense = (await db.execute(stmt)).scalars().first()
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    if expense.status != ExpenseStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject expense with status '{expense.status.value}'. Only pending expenses can be rejected."
        )
    
    # Reject expense
    expense.status = ExpenseStatus.REJECTED
    expense.approved_by = current_user.id
    expense.approved_at = datetime.now(timezone.utc)
    expense.rejection_reason = rejection_data.rejection_reason
    
    async with handle_db_operation(db, "reject expense"):
        await db.commit()
        await db.refresh(expense)
    
    return ExpenseResponse(
        id=expense.id,
        company_id=expense.company_id,
        employee_id=expense.employee_id,
        title=expense.title,
        amount=expense.amount,
        description=expense.description,
        expense_date=expense.expense_date,
        status=expense.status,
        receipt_url=expense.receipt_url,
        approved_by=expense.approved_by,
        approved_at=expense.approved_at,
        rejection_reason=expense.rejection_reason,
        created_at=expense.created_at,
        updated_at=expense.updated_at,
    )


@router.post("/{expense_id}/reimburse", response_model=ExpenseResponse)
async def reimburse_expense(
    expense_id: UUID,
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.HR)),
):
    """
    Mark an expense as reimbursed.
    
    **Access**: Admin and HR only
    
    **Workflow**: Changes status from "approved" to "reimbursed".
                 This indicates the expense has been paid/reimbursed to the employee.
    """
    stmt = select(Expense).where(
        Expense.id == expense_id,
        Expense.company_id == company_id
    )
    expense = (await db.execute(stmt)).scalars().first()
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    if expense.status != ExpenseStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reimburse expense with status '{expense.status.value}'. Only approved expenses can be reimbursed."
        )
    
    # Mark expense as reimbursed
    expense.status = ExpenseStatus.REIMBURSED
    
    async with handle_db_operation(db, "reimburse expense"):
        await db.commit()
        await db.refresh(expense)
    
    return ExpenseResponse(
        id=expense.id,
        company_id=expense.company_id,
        employee_id=expense.employee_id,
        title=expense.title,
        amount=expense.amount,
        description=expense.description,
        expense_date=expense.expense_date,
        status=expense.status,
        receipt_url=expense.receipt_url,
        approved_by=expense.approved_by,
        approved_at=expense.approved_at,
        rejection_reason=expense.rejection_reason,
        created_at=expense.created_at,
        updated_at=expense.updated_at,
    )


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: UUID,
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: CurrentUser,
):
    """
    Delete an expense.
    
    **Access**: Employees can only delete their own pending expenses.
                  HR/Admin can delete any expense.
    
    **Note**: Approved or reimbursed expenses should not be deleted (consider marking as cancelled instead).
    """
    stmt = select(Expense).where(
        Expense.id == expense_id,
        Expense.company_id == company_id
    )
    expense = (await db.execute(stmt)).scalars().first()
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    # Employees can only delete their own pending expenses
    if current_user.role == UserRole.EMPLOYEE:
        stmt = select(Employee).where(
            Employee.user_id == current_user.id,
            Employee.company_id == company_id
        )
        employee = (await db.execute(stmt)).scalars().first()
        
        if not employee or expense.employee_id != employee.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only delete your own expenses."
            )
        
        if expense.status != ExpenseStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete expense with status '{expense.status.value}'. Only pending expenses can be deleted."
            )
    else:
        # HR/Admin: Warn if deleting approved/reimbursed expense
        if expense.status in [ExpenseStatus.APPROVED, ExpenseStatus.REIMBURSED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete expense with status '{expense.status.value}'. Consider updating status instead."
            )
    
    db.delete(expense)
    async with handle_db_operation(db, "delete expense"):
        await db.commit()
    
    return None
