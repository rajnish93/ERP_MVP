from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from app.db.models.user import User, UserRole
from app.db.models.employee import Employee
from app.core.security import get_password_hash
from app.core.deps import SessionDep, CurrentUser, CurrentCompanyId
from app.core.error_handlers import handle_db_operation
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()


@router.post("/create", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: SessionDep,
    current_user: CurrentUser,
):
    """
    Invite an employee to the portal - creates a user account and links to employee record.
    
    **Access**: Admin only
    
    **Company Isolation**: Users are automatically assigned to the current user's company.
    
    **Flow**: This endpoint is used to invite employees to the portal:
    - If employee_id is provided: Links the new user account to an existing employee record
    - If employee_id is not provided: Creates a new employee record for the user
    
    **Request**:
    - email: User email (must be unique within the company)
    - password: User password (min 8 characters)
    - full_name: User full name
    - role: User role (hr, employee) - Admin role cannot be assigned via this endpoint
    - employee_id: (Optional) Link to existing employee record by employee UUID
    - department: (Optional) Department name (only used if creating new employee, defaults to "General")
    - job_role: (Optional) Job role/title (only used if creating new employee, defaults to capitalized user role)
    - joining_date: (Optional) Employee joining date (only used if creating new employee, defaults to current date)
    
    **Response**: Created user details
    """
    # Only Admin can create users
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin users can create new users"
        )
    
    # Prevent creating Admin users via this endpoint (only during company signup)
    if user_data.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role can only be assigned during company signup"
        )
    
    # Check if user with email already exists in the current company
    stmt = select(User).where(
        User.email == user_data.email,
        User.company_id == current_user.company_id
    )
    existing_user = (await db.execute(stmt)).scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered in your company"
        )
    
    # Hash password
    hashed_password = get_password_hash(user_data.password)
    
    # If employee_id is provided, link to existing employee
    if user_data.employee_id:
        # Verify employee exists and belongs to same company
        stmt = select(Employee).where(
            Employee.id == user_data.employee_id,
            Employee.company_id == current_user.company_id
        )
        existing_employee = (await db.execute(stmt)).scalars().first()
        
        if not existing_employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found in your company"
            )
        
        # Check if employee already has a user account
        if existing_employee.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee already has a user account"
            )
    
    # Create new user (automatically assigned to current user's company)
    new_user = User(
        company_id=current_user.company_id,  # Company isolation - same company
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()  # Flush to get the new_user.id without committing
    
    # Link to existing employee or create new employee record
    if user_data.employee_id:
        # Link user to existing employee
        existing_employee.user_id = new_user.id
    else:
        # Create new employee record for the user
        department = user_data.department or "General"
        job_role = user_data.job_role or user_data.role.value.capitalize()
        joining_date = user_data.joining_date or datetime.now(timezone.utc)
        
        new_employee = Employee(
            company_id=current_user.company_id,
            user_id=new_user.id,
            name=user_data.full_name,
            department=department,
            role=job_role,
            joining_date=joining_date,
            is_active=True,
        )
    
    # Commit transaction with automatic error handling
    async with handle_db_operation(db, "create user"):
        if not user_data.employee_id:
            db.add(new_employee)
        await db.commit()
        await db.refresh(new_user)
    
    return UserResponse(
        id=new_user.id,
        company_id=new_user.company_id,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        is_active=new_user.is_active,
        created_at=new_user.created_at,
    )


@router.get("/", response_model=list[UserResponse])
async def get_company_users_endpoint(
    db: SessionDep,
    company_id: CurrentCompanyId,
    _current_user: CurrentUser,
):
    """
    Get all users for the current company (workspace).
    
    **Access**: All authenticated users
    
    **Company Isolation**: Users can only see users from their own company.
    """
    stmt = select(User).where(User.company_id == company_id)
    company_users = (await db.execute(stmt)).scalars().all()
    return [
        UserResponse(
            id=user.id,
            company_id=user.company_id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        )
        for user in company_users
    ]


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser):
    """
    Get current authenticated user information.
    
    Requires valid JWT token in Authorization header.
    """
    return UserResponse(
        id=current_user.id,
        company_id=current_user.company_id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )


@router.put("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: UUID,
    db: SessionDep,
    current_user: CurrentUser,
    company_id: CurrentCompanyId,
):
    """
    Deactivate a user in the current company.
    
    **Access**: Admin only
    
    **Company Isolation**: Can only deactivate users from the same company.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin users can deactivate users"
        )
    
    # Find user - must be in same company
    stmt = select(User).where(
        User.id == user_id,
        User.company_id == company_id
    )
    user = (await db.execute(stmt)).scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your company"
        )
    
    # Prevent deactivating yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself"
        )
    
    # Deactivate user
    user.is_active = False
    
    async with handle_db_operation(db, "deactivate user"):
        await db.commit()
        await db.refresh(user)
    
    return UserResponse(
        id=user.id,
        company_id=user.company_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )
