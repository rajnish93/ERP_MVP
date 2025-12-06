from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import SessionDep
from app.db.models.company import Company
from app.db.models.user import User, UserRole
from app.core.security import get_password_hash
from app.schemas.company import CompanyCreate, CompanyResponse, CompanySignupResponse

router = APIRouter()


@router.post("/signup", response_model=CompanySignupResponse, status_code=status.HTTP_201_CREATED)
async def company_signup(company_data: CompanyCreate, db: SessionDep):
    """
    Company signup endpoint - creates a new company (tenant) and initial Admin user.
    
    This is the entry point for multi-tenant SaaS. When a company signs up:
    1. A new company record is created
    2. An Admin user is automatically created for that company (no employee record yet)
    
    **Request**:
    - Company details: name, email, plan_type
    - Admin user details: admin_name, admin_email, admin_password
    
    **Response**: Company details and Admin user details
    
    **Flow**:
    - Company signup → Admin user created (no employee record)
    - Admin can create employee records via /api/v1/employees endpoint
    - Admin can invite employees (create user accounts) via /api/v1/users/create endpoint
    
    **Next Steps**:
    - Admin logs in using admin_email and admin_password
    - Admin creates employees and then invites them to the portal
    """
    # Check if company email already exists
    stmt = select(Company).where(Company.email == company_data.email)
    existing_company = db.execute(stmt).scalars().first()
    if existing_company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company email already registered"
        )
    
    # Check if admin email already exists
    stmt = select(User).where(User.email == company_data.admin_email)
    existing_user = db.execute(stmt).scalars().first()
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
    await db.flush()  # Flush to get the company ID without committing
    
    # Create initial Admin user for this company (no employee record yet)
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
    try:
        await db.commit()
        await db.refresh(new_company)
        await db.refresh(admin_user)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create company: {str(e)}"
        )
    
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
        message="Company registered successfully. Admin user created. You can now create employees and invite them to the portal."
    )
