from typing import Optional
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.db.models.employee import Employee
from app.db.models.user import User, UserRole
from app.core.dependencies import get_current_active_user, get_current_company_id, require_role
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
    db: Session = Depends(get_db),
    company_id: UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.HR)),
):
    """
    Create a new employee for the current company.
    
    **Access**: Admin and HR only
    
    **Tenant Isolation**: Employees are automatically assigned to the current user's company.
    The user_id must belong to the same company.
    
    **Request**:
    - user_id: User account ID (must exist and belong to same company)
    - name: Employee full name
    - department: Department name
    - role: Job role/title
    - joining_date: Employee joining date
    - employee_id: Optional employee ID/code
    - phone: Optional phone number
    """
    # Verify user exists and belongs to same company
    user = db.query(User).filter(User.id == employee_data.user_id).first()
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
    existing_employee = db.query(Employee).filter(
        Employee.user_id == employee_data.user_id,
        Employee.company_id == company_id
    ).first()
    if existing_employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee record already exists for this user"
        )
    
    # Check if employee_id is unique within company (if provided)
    if employee_data.employee_id:
        existing_emp_id = db.query(Employee).filter(
            Employee.employee_id == employee_data.employee_id,
            Employee.company_id == company_id
        ).first()
        if existing_emp_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee ID '{employee_data.employee_id}' already exists in your company"
            )
    
    # Create new employee
    new_employee = Employee(
        company_id=company_id,  # Tenant isolation
        user_id=employee_data.user_id,
        name=employee_data.name,
        department=employee_data.department,
        role=employee_data.role,
        joining_date=employee_data.joining_date,
        employee_id=employee_data.employee_id,
        phone=employee_data.phone,
        is_active=True,
    )
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)
    
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
    db: Session = Depends(get_db),
    company_id: UUID = Depends(get_current_company_id),
    current_user: User = Depends(get_current_active_user),
    department: Optional[str] = Query(None, description="Filter by department"),
    role: Optional[str] = Query(None, description="Filter by job role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name or employee_id"),
):
    """
    Get all employees for the current company with optional filtering.
    
    **Access**: All authenticated users (but HR/Admin see more details)
    
    **Tenant Isolation**: Only returns employees from the current user's company.
    
    **Query Parameters**:
    - department: Filter by department name
    - role: Filter by job role/title
    - is_active: Filter by active status (true/false)
    - search: Search by employee name or employee_id
    """
    # Base query - filter by company (tenant isolation)
    query = db.query(Employee).filter(Employee.company_id == company_id)
    
    # Apply filters
    if department:
        query = query.filter(Employee.department.ilike(f"%{department}%"))
    
    if role:
        query = query.filter(Employee.role.ilike(f"%{role}%"))
    
    if is_active is not None:
        query = query.filter(Employee.is_active == is_active)
    
    if search:
        search_filter = or_(
            Employee.name.ilike(f"%{search}%"),
            Employee.employee_id.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    employees = query.all()
    
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
    db: Session = Depends(get_db),
    company_id: UUID = Depends(get_current_company_id),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a specific employee by ID.
    
    **Access**: All authenticated users
    
    **Tenant Isolation**: Can only access employees from the same company.
    """
    employee = db.query(Employee).filter(
        Employee.id == employee_id,
        Employee.company_id == company_id
    ).first()
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
    db: Session = Depends(get_db),
    company_id: UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.HR)),
):
    """
    Update an existing employee.
    
    **Access**: Admin and HR only
    
    **Tenant Isolation**: Can only update employees from the same company.
    
    **Request**: All fields are optional - only provided fields will be updated.
    """
    employee = db.query(Employee).filter(
        Employee.id == employee_id,
        Employee.company_id == company_id
    ).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found in your company"
        )
    
    # Check if employee_id is unique within company (if being updated)
    if employee_data.employee_id and employee_data.employee_id != employee.employee_id:
        existing_emp_id = db.query(Employee).filter(
            Employee.employee_id == employee_data.employee_id,
            Employee.company_id == company_id,
            Employee.id != employee_id
        ).first()
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
    if employee_data.is_active is not None:
        employee.is_active = employee_data.is_active
    
    db.commit()
    db.refresh(employee)
    
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
    db: Session = Depends(get_db),
    company_id: UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Delete (soft delete) an employee record.
    
    **Access**: Admin only
    
    **Tenant Isolation**: Can only delete employees from the same company.
    
    **Note**: This performs a soft delete (sets is_active=False) rather than
    removing the record completely.
    """
    employee = db.query(Employee).filter(
        Employee.id == employee_id,
        Employee.company_id == company_id
    ).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found in your company"
        )
    
    # Soft delete
    employee.is_active = False
    db.commit()
    
    return {"message": "Employee deleted successfully", "employee_id": employee_id}
