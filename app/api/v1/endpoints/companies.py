from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.company import Company, PlanType
from app.db.models.user import User, UserRole
from app.core.security import get_password_hash
from app.schemas.company import CompanyCreate, CompanyResponse, CompanySignupResponse

router = APIRouter()


@router.post("/signup", response_model=CompanySignupResponse, status_code=status.HTTP_201_CREATED)
async def company_signup(company_data: CompanyCreate, db: Session = Depends(get_db)):
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
    existing_company = db.query(Company).filter(Company.email == company_data.email).first()
    if existing_company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company email already registered"
        )
    
    # Check if admin email already exists
    existing_user = db.query(User).filter(User.email == company_data.admin_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin email already registered"
        )
    
    # Create new company
    new_company = Company(
        name=company_data.name,
        email=company_data.email,
        plan_type=company_data.plan_type,
        is_active=True,
    )
    db.add(new_company)
    db.flush()  # Flush to get the company ID without committing
    
    # Create initial Admin user for this company
    hashed_password = get_password_hash(company_data.admin_password)
    admin_user = User(
        company_id=new_company.id,
        email=company_data.admin_email,
        hashed_password=hashed_password,
        full_name=company_data.admin_name,
        role=UserRole.ADMIN,  # First user is always Admin
        is_active=True,
    )
    db.add(admin_user)
    db.commit()
    db.refresh(new_company)
    db.refresh(admin_user)
    
    return CompanySignupResponse(
        company=CompanyResponse(
            id=new_company.id,
            name=new_company.name,
            email=new_company.email,
            plan_type=new_company.plan_type,
            is_active=new_company.is_active,
            created_at=new_company.created_at,
        ),
        admin_user={
            "id": admin_user.id,
            "company_id": admin_user.company_id,
            "email": admin_user.email,
            "full_name": admin_user.full_name,
            "role": admin_user.role.value,
            "is_active": admin_user.is_active,
            "created_at": admin_user.created_at.isoformat() if admin_user.created_at else None,
        },
        message="Company registered successfully. Admin user created."
    )
