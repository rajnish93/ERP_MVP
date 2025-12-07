from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import or_, select

from app.core.deps import SessionDep, CurrentCompanyId, CurrentUser
from app.db.models.employee import Employee
from app.db.models.user import User, UserRole
from app.core.dependencies import require_role
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
    EmployeeListResponse,
)

router = APIRouter()


@router.post("/", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    employee_data: EmployeeCreate,
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.HR)),
):
    """
    Create a new employee for the current company.
    
    **Access**: Admin and HR only
    
    **Company Isolation**: Employees are automatically assigned to the current user's company.
    
    **Request**:
    - user_id: (Optional) User account ID to link employee to. If provided, must exist and belong to same company.
               Employees can be created without user accounts (for employees not yet onboarded).
    - name: Employee full name
    - department: Department name
    - role: Job role/title
    - joining_date: Employee joining date
    - employee_id: Optional employee ID/code
    - phone: Optional phone number
    
    **Note**: All users must have employee records, but employees can exist without user accounts.
    """
    # If user_id is provided, verify user exists and belongs to same company
    if employee_data.user_id:
        stmt = select(User).where(User.id == employee_data.user_id)
        user = (await db.execute(stmt)).scalars().first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.company_id != company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not belong to your company"
            )
        
        # Check if employee already exists for this user
        stmt = select(Employee).where(
            Employee.user_id == employee_data.user_id,
            Employee.company_id == company_id
        )
        existing_employee = (await db.execute(stmt)).scalars().first()
        if existing_employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee record already exists for this user"
            )
    
    # Check if employee_id is unique within company (if provided)
    if employee_data.employee_id:
        stmt = select(Employee).where(
            Employee.employee_id == employee_data.employee_id,
            Employee.company_id == company_id
        )
        existing_emp_id = (await db.execute(stmt)).scalars().first()
        if existing_emp_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee ID '{employee_data.employee_id}' already exists in your company"
            )
    
    # Create new employee (user_id is optional)
    new_employee = Employee(
        company_id=company_id,  # Company isolation
        user_id=employee_data.user_id,  # Can be None if employee doesn't have user account yet
        name=employee_data.name,
        department=employee_data.department,
        role=employee_data.role,
        joining_date=employee_data.joining_date,
        employee_id=employee_data.employee_id,
        phone=employee_data.phone,
        is_active=True,
    )
    db.add(new_employee)
    try:
        await db.commit()
        await db.refresh(new_employee)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create employee: {str(e)}"
        )
    
    return EmployeeResponse(
        id=new_employee.id,
        company_id=new_employee.company_id,
        user_id=new_employee.user_id,
        name=new_employee.name,
        department=new_employee.department,
        role=new_employee.role,
        joining_date=new_employee.joining_date,
        employee_id=new_employee.employee_id,
        phone=new_employee.phone,
        is_active=new_employee.is_active,
        created_at=new_employee.created_at,
        updated_at=new_employee.updated_at,
    )


@router.get("/", response_model=EmployeeListResponse)
async def get_employees(
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: CurrentUser,
    department: Optional[str] = Query(None, description="Filter by department"),
    role: Optional[str] = Query(None, description="Filter by job role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name or employee_id"),
):
    """
    Get all employees for the current company with optional filtering.
    
    **Access**: All authenticated users (but HR/Admin see more details)
    
    **Company Isolation**: Only returns employees from the current user's company.
    
    **Query Parameters**:
    - department: Filter by department name
    - role: Filter by job role/title
    - is_active: Filter by active status (true/false)
    - search: Search by employee name or employee_id
    """
    # Base query - filter by company (company isolation)
    stmt = select(Employee).where(Employee.company_id == company_id)
    
    # Apply filters
    if department:
        stmt = stmt.where(Employee.department.ilike(f"%{department}%"))
    
    if role:
        stmt = stmt.where(Employee.role.ilike(f"%{role}%"))
    
    if is_active is not None:
        stmt = stmt.where(Employee.is_active == is_active)
    
    if search:
        search_filter = or_(
            Employee.name.ilike(f"%{search}%"),
            Employee.employee_id.ilike(f"%{search}%")
        )
        stmt = stmt.where(search_filter)
    
    employees = (await db.execute(stmt)).scalars().all()
    
    return EmployeeListResponse(
        employees=[
            EmployeeResponse(
                id=emp.id,
                company_id=emp.company_id,
                user_id=emp.user_id,
                name=emp.name,
                department=emp.department,
                role=emp.role,
                joining_date=emp.joining_date,
                employee_id=emp.employee_id,
                phone=emp.phone,
                is_active=emp.is_active,
                created_at=emp.created_at,
                updated_at=emp.updated_at,
            )
            for emp in employees
        ],
        total=len(employees)
    )


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: UUID,
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: CurrentUser,
):
    """
    Get a specific employee by ID.
    
    **Access**: All authenticated users
    
    **Company Isolation**: Can only access employees from the same company.
    """
    stmt = select(Employee).where(
        Employee.id == employee_id,
        Employee.company_id == company_id
    )
    employee = (await db.execute(stmt)).scalars().first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found in your company"
        )
    
    return EmployeeResponse(
        id=employee.id,
        company_id=employee.company_id,
        user_id=employee.user_id,
        name=employee.name,
        department=employee.department,
        role=employee.role,
        joining_date=employee.joining_date,
        employee_id=employee.employee_id,
        phone=employee.phone,
        is_active=employee.is_active,
        created_at=employee.created_at,
        updated_at=employee.updated_at,
    )


@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: UUID,
    employee_data: EmployeeUpdate,
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.HR)),
):
    """
    Update an existing employee.
    
    **Access**: Admin and HR only
    
    **Company Isolation**: Can only update employees from the same company.
    
    **Request**: All fields are optional - only provided fields will be updated.
    """
    stmt = select(Employee).where(
        Employee.id == employee_id,
        Employee.company_id == company_id
    )
    employee = (await db.execute(stmt)).scalars().first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found in your company"
        )
    
    # Check if employee_id is unique within company (if being updated)
    if employee_data.employee_id and employee_data.employee_id != employee.employee_id:
        stmt = select(Employee).where(
            Employee.employee_id == employee_data.employee_id,
            Employee.company_id == company_id,
            Employee.id != employee_id
        )
        existing_emp_id = (await db.execute(stmt)).scalars().first()
        if existing_emp_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee ID '{employee_data.employee_id}' already exists in your company"
            )
    
    # Update fields (only if provided)
    if employee_data.name is not None:
        employee.name = employee_data.name
    if employee_data.department is not None:
        employee.department = employee_data.department
    if employee_data.role is not None:
        employee.role = employee_data.role
    if employee_data.joining_date is not None:
        employee.joining_date = employee_data.joining_date
    if employee_data.employee_id is not None:
        employee.employee_id = employee_data.employee_id
    if employee_data.phone is not None:
        employee.phone = employee_data.phone
    if employee_data.user_id is not None:
        # If updating user_id, verify the user exists and belongs to same company
        if employee_data.user_id != employee.user_id:
            stmt = select(User).where(User.id == employee_data.user_id)
            user = (await db.execute(stmt)).scalars().first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            if user.company_id != company_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User does not belong to your company"
                )
            # Check if another employee already has this user_id
            stmt = select(Employee).where(
                Employee.user_id == employee_data.user_id,
                Employee.company_id == company_id,
                Employee.id != employee_id
            )
            existing_employee_with_user = (await db.execute(stmt)).scalars().first()
            if existing_employee_with_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Another employee already has this user account"
                )
        employee.user_id = employee_data.user_id
    if employee_data.is_active is not None:
        employee.is_active = employee_data.is_active
    
    try:
        await db.commit()
        await db.refresh(employee)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update employee: {str(e)}"
        )
    
    return EmployeeResponse(
        id=employee.id,
        company_id=employee.company_id,
        user_id=employee.user_id,
        name=employee.name,
        department=employee.department,
        role=employee.role,
        joining_date=employee.joining_date,
        employee_id=employee.employee_id,
        phone=employee.phone,
        is_active=employee.is_active,
        created_at=employee.created_at,
        updated_at=employee.updated_at,
    )


@router.delete("/{employee_id}", status_code=status.HTTP_200_OK)
async def delete_employee(
    employee_id: UUID,
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Delete (soft delete) an employee record.
    
    **Access**: Admin only
    
    **Company Isolation**: Can only delete employees from the same company.
    
    **Note**: This performs a soft delete (sets is_active=False) rather than
    removing the record completely.
    """
    stmt = select(Employee).where(
        Employee.id == employee_id,
        Employee.company_id == company_id
    )
    employee = (await db.execute(stmt)).scalars().first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found in your company"
        )
    
    # Soft delete
    employee.is_active = False
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete employee: {str(e)}"
        )
    
    return {"message": "Employee deleted successfully", "employee_id": employee_id}
