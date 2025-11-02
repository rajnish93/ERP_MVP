from fastapi import APIRouter, Depends, HTTPException, status

from app.models.company import Company, PlanType, companies_db
from app.models.user import User, UserRole, users_db
from app.core.security import get_password_hash
from app.schemas.company import CompanyCreate, CompanyResponse, CompanySignupResponse
import app.models.company as company_model
import app.models.user as user_model

router = APIRouter()


@router.post("/signup", response_model=CompanySignupResponse, status_code=status.HTTP_201_CREATED)
async def company_signup(company_data: CompanyCreate):
    """
    Company signup endpoint - creates a new company (tenant) and initial Admin user.
    
    This is the entry point for multi-tenant SaaS. When a company signs up:
    1. A new company record is created
    2. An Admin user is automatically created for that company
    3. The Admin can then create HR and Employee users
    
    **Request**:
    - Company details: name, email, plan_type
    - Admin user details: admin_name, admin_email, admin_password
    
    **Response**: Company details and Admin user details
    
    **Next Steps**:
    - Admin logs in using admin_email and admin_password
    - Admin can create users via /api/v1/users/create endpoint
    """
    # Check if company email already exists
    existing_company = next((c for c in companies_db if c.email == company_data.email), None)
    if existing_company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company email already registered"
        )
    
    # Check if admin email already exists
    existing_user = next((u for u in users_db if u.email == company_data.admin_email), None)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin email already registered"
        )
    
    # Create new company
    new_company = Company(
        id=company_model.next_company_id,
        name=company_data.name,
        email=company_data.email,
        plan_type=company_data.plan_type,
        is_active=True,
    )
    companies_db.append(new_company)
    company_id = company_model.next_company_id
    company_model.next_company_id += 1
    
    # Create initial Admin user for this company
    hashed_password = get_password_hash(company_data.admin_password)
    admin_user = User(
        id=user_model.next_user_id,
        company_id=company_id,
        email=company_data.admin_email,
        hashed_password=hashed_password,
        full_name=company_data.admin_name,
        role=UserRole.ADMIN,  # First user is always Admin
        is_active=True,
    )
    users_db.append(admin_user)
    user_model.next_user_id += 1
    
    return CompanySignupResponse(
        company=CompanyResponse(**new_company.to_dict()),
        admin_user=admin_user.to_dict(),
        message="Company registered successfully. Admin user created."
    )

