import re
import logging
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.deps import SessionDep
from app.db.models.company import Company
from app.db.models.user import User, UserRole
from app.core.security import get_password_hash
from app.schemas.company import CompanyCreate, CompanyResponse, CompanySignupResponse

router = APIRouter()
logger = logging.getLogger(__name__)


def generate_company_slug(name: str) -> str:
    """
    Generate a URL-friendly slug from company name.
    Converts to lowercase, replaces non-alphanumeric chars with hyphens,
    removes leading/trailing hyphens, and limits to 50 characters.
    """
    slug_base = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    if not slug_base:
        return "workspace"
    return slug_base[:50]


@router.post("/signup", response_model=CompanySignupResponse, status_code=status.HTTP_201_CREATED)
async def company_signup(company_data: CompanyCreate, db: SessionDep):
    """
    Company signup endpoint - creates a new company (workspace) and initial Admin user.
    
    This is the entry point for multi-workspace SaaS. When a company signs up:
    1. A new company record is created
    2. An Admin user is automatically created for that company (no employee record yet)
    
    **Request**:
    - Company details: name, email, plan_type, slug (optional - auto-generated from name if not provided)
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
    existing_company = (await db.execute(stmt)).scalars().first()
    if existing_company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company email already registered"
        )
    
    # Note: Email uniqueness is enforced per-company in the database
    # (composite constraint on company_id + email)
    # We don't check global uniqueness here to allow same email across companies
    
    # Generate or validate slug for the company
    if company_data.slug:
        # Validate format and length
        if len(company_data.slug) > 50:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Slug must be 50 characters or less."
            )
        if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', company_data.slug):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Slug must contain only lowercase letters, numbers, and hyphens. Cannot start or end with a hyphen."
            )
        slug = company_data.slug
    else:
        # Auto-generate slug from company name
        slug = generate_company_slug(company_data.name)

    # Ensure slug uniqueness (Loop check helps reduce collisions but doesn't prevent race conditions completely)
    original_slug = slug
    counter = 1
    while True:
        stmt = select(Company).where(Company.slug == slug)
        existing_company = (await db.execute(stmt)).scalars().first()
        if not existing_company:
            break
        slug = f"{original_slug[: max(0, 50 - (len(str(counter)) + 1))]}-{counter}"
        counter += 1

    # Create new company
    new_company = Company(
        name=company_data.name,
        slug=slug,
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
    except IntegrityError:
        await db.rollback()
        # Handle concurrency collision for slug or email
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Company with this slug or email already exists. Please try again."
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create company: {str(e)}"
        )
    
    logger.info(f"New company signed up: {new_company.name} ({new_company.slug})")
    
    return CompanySignupResponse(
        company=CompanyResponse(
            id=new_company.id,
            name=new_company.name,
            email=new_company.email,
            slug=new_company.slug,
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
