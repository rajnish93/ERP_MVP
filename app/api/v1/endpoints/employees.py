from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.models.employee import Employee, employees_db
from app.models.user import User, UserRole, users_db
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
    company_id: int = Depends(get_current_company_id),
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
    user = next((u for u in users_db if u.id == employee_data.user_id), None)
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
    existing_employee = next(
        (e for e in employees_db if e.user_id == employee_data.user_id and e.company_id == company_id),
        None
    )
    if existing_employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee record already exists for this user"
        )
    
    # Check if employee_id is unique within company (if provided)
    if employee_data.employee_id:
        existing_emp_id = next(
            (e for e in employees_db if e.employee_id == employee_data.employee_id and e.company_id == company_id),
            None
        )
        if existing_emp_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee ID '{employee_data.employee_id}' already exists in your company"
            )
    
    # Create new employee
    import app.models.employee as employee_model
    
    new_employee = Employee(
        id=employee_model.next_employee_id,
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
    employees_db.append(new_employee)
    employee_model.next_employee_id += 1
    
    return EmployeeResponse(**new_employee.to_dict())


@router.get("/", response_model=EmployeeListResponse)
async def get_employees(
    company_id: int = Depends(get_current_company_id),
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
    # Filter by company (tenant isolation)
    company_employees = [e for e in employees_db if e.company_id == company_id]
    
    # Apply filters
    filtered_employees = company_employees
    
    if department:
        filtered_employees = [e for e in filtered_employees if e.department.lower() == department.lower()]
    
    if role:
        filtered_employees = [e for e in filtered_employees if e.role.lower() == role.lower()]
    
    if is_active is not None:
        filtered_employees = [e for e in filtered_employees if e.is_active == is_active]
    
    if search:
        search_lower = search.lower()
        filtered_employees = [
            e for e in filtered_employees
            if search_lower in e.name.lower() or
            (e.employee_id and search_lower in e.employee_id.lower())
        ]
    
    return EmployeeListResponse(
        employees=[EmployeeResponse(**e.to_dict()) for e in filtered_employees],
        total=len(filtered_employees)
    )


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: int,
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a specific employee by ID.
    
    **Access**: All authenticated users
    
    **Tenant Isolation**: Can only access employees from the same company.
    """
    employee = next(
        (e for e in employees_db if e.id == employee_id and e.company_id == company_id),
        None
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found in your company"
        )
    
    return EmployeeResponse(**employee.to_dict())


@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: int,
    employee_data: EmployeeUpdate,
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.HR)),
):
    """
    Update an existing employee.
    
    **Access**: Admin and HR only
    
    **Tenant Isolation**: Can only update employees from the same company.
    
    **Request**: All fields are optional - only provided fields will be updated.
    """
    employee = next(
        (e for e in employees_db if e.id == employee_id and e.company_id == company_id),
        None
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found in your company"
        )
    
    # Check if employee_id is unique within company (if being updated)
    if employee_data.employee_id and employee_data.employee_id != employee.employee_id:
        existing_emp_id = next(
            (e for e in employees_db 
             if e.employee_id == employee_data.employee_id 
             and e.company_id == company_id 
             and e.id != employee_id),
            None
        )
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
    
    employee.updated_at = datetime.utcnow()
    
    return EmployeeResponse(**employee.to_dict())


@router.delete("/{employee_id}", status_code=status.HTTP_200_OK)
async def delete_employee(
    employee_id: int,
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Delete (soft delete) an employee record.
    
    **Access**: Admin only
    
    **Tenant Isolation**: Can only delete employees from the same company.
    
    **Note**: This performs a soft delete (sets is_active=False) rather than
    removing the record completely.
    """
    employee = next(
        (e for e in employees_db if e.id == employee_id and e.company_id == company_id),
        None
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found in your company"
        )
    
    # Soft delete
    employee.is_active = False
    employee.updated_at = datetime.utcnow()
    
    return {"message": "Employee deleted successfully", "employee_id": employee_id}

