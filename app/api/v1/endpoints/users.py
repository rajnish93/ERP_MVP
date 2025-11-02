from fastapi import APIRouter, Depends, HTTPException, status

from app.models.user import User, UserRole, users_db
from app.core.security import get_password_hash
from app.core.dependencies import get_current_active_user, require_role, get_current_company_id, get_company_users
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()


@router.post("/create", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new user for the current company (tenant).
    
    **Access**: Admin only
    
    **Tenant Isolation**: Users are automatically assigned to the current user's company.
    Only Admin users can create new users for their company.
    
    **Request**:
    - email: User email (must be unique globally)
    - password: User password (min 8 characters)
    - full_name: User full name
    - role: User role (hr, employee) - Admin role cannot be assigned via this endpoint
    
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
    
    # Check if user with email already exists globally
    existing_user = next((u for u in users_db if u.email == user_data.email), None)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    hashed_password = get_password_hash(user_data.password)
    
    # Create new user (automatically assigned to current user's company)
    import app.models.user as user_model
    
    new_user = User(
        id=user_model.next_user_id,
        company_id=current_user.company_id,  # Tenant isolation - same company
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=True,
    )
    users_db.append(new_user)
    user_model.next_user_id += 1
    
    return UserResponse(**new_user.to_dict())


@router.get("/", response_model=list[UserResponse])
async def get_company_users_endpoint(
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all users for the current company (tenant).
    
    **Access**: All authenticated users
    
    **Tenant Isolation**: Users can only see users from their own company.
    """
    company_users = get_company_users(company_id)
    return [UserResponse(**user.to_dict()) for user in company_users]


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Get current authenticated user information.
    
    Requires valid JWT token in Authorization header.
    """
    return UserResponse(**current_user.to_dict())


@router.put("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    company_id: int = Depends(get_current_company_id),
):
    """
    Deactivate a user in the current company.
    
    **Access**: Admin only
    
    **Tenant Isolation**: Can only deactivate users from the same company.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin users can deactivate users"
        )
    
    # Find user - must be in same company
    user = next(
        (u for u in users_db if u.id == user_id and u.company_id == company_id),
        None
    )
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
    
    user.is_active = False
    return UserResponse(**user.to_dict())

