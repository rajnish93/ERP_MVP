import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Tuple
from uuid import UUID

from fastapi import UploadFile, HTTPException, status
from sqlalchemy import select, or_, func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.files import file_service
from app.core.error_handlers import handle_db_operation
from app.db.models.expense import Expense, ExpenseStatus
from app.db.models.employee import Employee
from app.db.models.user import User, UserRole
from app.schemas.expense import ExpenseSummaryResponse


logger = logging.getLogger(__name__)


class ExpenseService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_employee_for_user(
        self, user_id: UUID, company_id: UUID
    ) -> Optional[Employee]:
        stmt = select(Employee).where(
            Employee.user_id == user_id, Employee.company_id == company_id
        )
        return (await self.db.execute(stmt)).scalars().first()

    async def create_expense(
        self,
        company_id: UUID,
        current_user: User,
        title: str,
        amount: Decimal,
        expense_date: datetime,
        description: Optional[str] = None,
        employee_id: Optional[UUID] = None,
        file: Optional[UploadFile] = None,
    ) -> Expense:
        """
        Create a new expense, handling employee validation and file uploads.
        """
        # Get requester's employee record
        requester_employee = await self._get_employee_for_user(
            current_user.id, company_id
        )

        # Validate Employee Context
        if not requester_employee:
            if current_user.role == UserRole.EMPLOYEE:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Employee record not found. Please contact HR to create your employee profile.",
                )
            # Admin/HR without employee record MUST provide employee_id
            if not employee_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You do not have an employee profile. Please select an employee to submit this expense for.",
                )

        # Determine target employee
        target_employee_id = employee_id if employee_id else requester_employee.id

        # Permission Checks
        if employee_id:
            # Employee role cannot submit for others
            if (
                requester_employee
                and employee_id != requester_employee.id
                and current_user.role == UserRole.EMPLOYEE
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only submit expenses for yourself",
                )

            # Verify target employee exists and is active in company
            if not requester_employee or employee_id != requester_employee.id:
                stmt = select(Employee).where(
                    Employee.id == target_employee_id,
                    Employee.company_id == company_id,
                    Employee.is_active.is_(True),
                )
                target = (await self.db.execute(stmt)).scalars().first()
                if not target:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Target employee not found or inactive in company",
                    )

        # Handle File Upload
        receipt_url = None
        if file:
            upload_result = await file_service.save_file(file)
            receipt_url = upload_result["url"]

        # Create Record
        new_expense = Expense(
            company_id=company_id,
            employee_id=target_employee_id,
            title=title,
            amount=amount,
            description=description,
            expense_date=expense_date,
            status=ExpenseStatus.PENDING,
            receipt_url=receipt_url,
        )

        try:
            async with handle_db_operation(self.db, "create expense"):
                self.db.add(new_expense)
                await self.db.commit()
                await self.db.refresh(new_expense)
        except Exception:
            # Cleanup file on DB failure
            if receipt_url:
                await file_service.delete_file(receipt_url)
            raise

        return new_expense

    async def update_expense(
        self,
        company_id: UUID,
        current_user: User,
        expense_id: UUID,
        title: Optional[str] = None,
        amount: Optional[Decimal] = None,
        expense_date: Optional[datetime] = None,
        description: Optional[str] = None,
        file: Optional[UploadFile] = None,
        clear_receipt: bool = False,
    ) -> Expense:
        stmt = select(Expense).where(
            Expense.id == expense_id, Expense.company_id == company_id
        )
        expense = (await self.db.execute(stmt)).scalars().first()

        if not expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found"
            )

        # Permission & Status Checks
        if current_user.role == UserRole.EMPLOYEE:
            employee = await self._get_employee_for_user(current_user.id, company_id)
            if not employee or expense.employee_id != employee.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied. You can only update your own expenses.",
                )
            if expense.status != ExpenseStatus.PENDING:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot update expense with status '{expense.status.value}'. Only pending expenses can be updated.",
                )
        else:
            # HR/Admin restrictions
            if expense.status in [ExpenseStatus.REIMBURSED, ExpenseStatus.APPROVED]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot update expense with status '{expense.status.value}'. Expenses are locked after approval.",
                )

        # File Handling
        files_to_delete = []
        new_receipt_url = None

        if clear_receipt and expense.receipt_url:
            files_to_delete.append(expense.receipt_url)
            expense.receipt_url = None

        if file:
            if expense.receipt_url:
                files_to_delete.append(expense.receipt_url)

            upload_result = await file_service.save_file(file)
            new_receipt_url = upload_result["url"]
            expense.receipt_url = new_receipt_url

        # Update Fields
        if title is not None:
            expense.title = title
        if amount is not None:
            expense.amount = amount
        if expense_date is not None:
            expense.expense_date = expense_date
        if description is not None:
            expense.description = description

        try:
            async with handle_db_operation(self.db, "update expense"):
                await self.db.commit()
                await self.db.refresh(expense)

            # Post-commit cleanup
            for old_url in files_to_delete:
                await file_service.delete_file(old_url)

        except Exception:
            if new_receipt_url:
                await file_service.delete_file(new_receipt_url)
            raise

        return expense

    async def approve_expense(
        self, company_id: UUID, user_id: UUID, expense_id: UUID
    ) -> Expense:
        stmt = select(Expense).where(
            Expense.id == expense_id, Expense.company_id == company_id
        )
        expense = (await self.db.execute(stmt)).scalars().first()

        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")

        if expense.status != ExpenseStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot approve expense with status '{expense.status.value}'. Only pending expenses can be approved.",
            )

        expense.status = ExpenseStatus.APPROVED
        expense.approved_by = user_id
        expense.approved_at = datetime.now(timezone.utc)
        expense.rejection_reason = None

        async with handle_db_operation(self.db, "approve expense"):
            await self.db.commit()
            await self.db.refresh(expense)

        return expense

    async def reject_expense(
        self, company_id: UUID, user_id: UUID, expense_id: UUID, reason: str
    ) -> Expense:
        stmt = select(Expense).where(
            Expense.id == expense_id, Expense.company_id == company_id
        )
        expense = (await self.db.execute(stmt)).scalars().first()

        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")

        if expense.status != ExpenseStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot reject expense with status '{expense.status.value}'. Only pending expenses can be rejected.",
            )

        expense.status = ExpenseStatus.REJECTED
        expense.approved_by = user_id
        expense.approved_at = datetime.now(timezone.utc)
        expense.rejection_reason = reason

        async with handle_db_operation(self.db, "reject expense"):
            await self.db.commit()
            await self.db.refresh(expense)

        return expense

    async def reimburse_expense(
        self, company_id: UUID, user_id: UUID, expense_id: UUID
    ) -> Expense:
        stmt = select(Expense).where(
            Expense.id == expense_id, Expense.company_id == company_id
        )
        expense = (await self.db.execute(stmt)).scalars().first()

        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")

        if expense.status != ExpenseStatus.APPROVED:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot reimburse expense with status '{expense.status.value}'. Only approved expenses can be reimbursed.",
            )

        expense.status = ExpenseStatus.REIMBURSED

        async with handle_db_operation(self.db, "reimburse expense"):
            await self.db.commit()
            await self.db.refresh(expense)

        return expense

    async def get_summary(
        self, company_id: UUID, current_user: User
    ) -> ExpenseSummaryResponse:
        """
        Optimized summary generation using single query aggregation where possible.
        """
        conditions = [Expense.company_id == company_id]

        # Access Control
        if current_user.role == UserRole.EMPLOYEE:
            employee = await self._get_employee_for_user(current_user.id, company_id)
            if not employee:
                # Return empty zero-ed summary
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

        # Aggregation Query
        # We group by status to get counts and sums in one go
        stmt = (
            select(
                Expense.status,
                sql_func.count(Expense.id).label("count"),
                sql_func.sum(Expense.amount).label("total"),
            )
            .where(*conditions)
            .group_by(Expense.status)
        )

        results = (await self.db.execute(stmt)).all()

        # Map results to response
        summary_data = {
            "total_expenses": 0,
            "total_amount": Decimal("0.00"),
            "pending_expenses": 0,
            "pending_amount": Decimal("0.00"),
            "approved_expenses": 0,
            "approved_amount": Decimal("0.00"),
            "rejected_expenses": 0,
            "rejected_amount": Decimal("0.00"),
            "reimbursed_expenses": 0,
            "reimbursed_amount": Decimal("0.00"),
        }

        for status_val, count, total in results:
            total = total or Decimal("0.00")
            summary_data["total_expenses"] += count
            summary_data["total_amount"] += total

            if status_val == ExpenseStatus.PENDING:
                summary_data["pending_expenses"] = count
                summary_data["pending_amount"] = total
            elif status_val == ExpenseStatus.APPROVED:
                summary_data["approved_expenses"] = count
                summary_data["approved_amount"] = total
            elif status_val == ExpenseStatus.REJECTED:
                summary_data["rejected_expenses"] = count
                summary_data["rejected_amount"] = total
            elif status_val == ExpenseStatus.REIMBURSED:
                summary_data["reimbursed_expenses"] = count
                summary_data["reimbursed_amount"] = total

        return ExpenseSummaryResponse(**summary_data)

    async def delete_expense(
        self, company_id: UUID, current_user: User, expense_id: UUID
    ):
        stmt = select(Expense).where(
            Expense.id == expense_id, Expense.company_id == company_id
        )
        expense = (await self.db.execute(stmt)).scalars().first()

        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")

        # Permission Checks
        if current_user.role == UserRole.EMPLOYEE:
            employee = await self._get_employee_for_user(current_user.id, company_id)
            if not employee or expense.employee_id != employee.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied. You can only delete your own expenses.",
                )
            # Employees can only delete PENDING
            if expense.status != ExpenseStatus.PENDING:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot delete expense with status '{expense.status.value}'. Only pending expenses can be deleted.",
                )

        # Cleanup file
        if expense.receipt_url:
            await file_service.delete_file(expense.receipt_url)

        async with handle_db_operation(self.db, "delete expense"):
            await self.db.delete(expense)
            await self.db.commit()

    async def get_expense_by_id(
        self, company_id: UUID, current_user: User, expense_id: UUID
    ) -> Expense:
        stmt = (
            select(Expense)
            .options(selectinload(Expense.employee), selectinload(Expense.approver))
            .where(Expense.id == expense_id, Expense.company_id == company_id)
        )
        expense = (await self.db.execute(stmt)).scalars().first()

        if not expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found"
            )

        # Access Control
        if current_user.role == UserRole.EMPLOYEE:
            employee = await self._get_employee_for_user(current_user.id, company_id)
            if not employee or expense.employee_id != employee.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied. You can only view your own expenses.",
                )

        return expense

    async def get_expenses(
        self,
        company_id: UUID,
        current_user: User,
        status_filter: Optional[ExpenseStatus] = None,
        employee_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Expense], int, Decimal]:
        """
        Get expenses with filtering and pagination.
        Returns (expenses, total_count, total_amount)
        """
        conditions = [Expense.company_id == company_id]

        # Access Control
        if current_user.role == UserRole.EMPLOYEE:
            employee = await self._get_employee_for_user(current_user.id, company_id)
            if not employee:
                return [], 0, Decimal("0.00")
            conditions.append(Expense.employee_id == employee.id)
        elif employee_id:
            conditions.append(Expense.employee_id == employee_id)

        # Filters
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
                    Expense.description.ilike(search_term),
                )
            )

        # Counts
        count_stmt = select(sql_func.count(Expense.id)).where(*conditions)
        total = (await self.db.execute(count_stmt)).scalar() or 0

        sum_stmt = select(sql_func.sum(Expense.amount)).where(*conditions)
        total_amount = (await self.db.execute(sum_stmt)).scalar() or Decimal("0.00")

        # Query
        stmt = (
            select(Expense)
            .options(selectinload(Expense.employee), selectinload(Expense.approver))
            .where(*conditions)
            .order_by(Expense.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        expenses = (await self.db.execute(stmt)).scalars().all()

        return expenses, total, total_amount
