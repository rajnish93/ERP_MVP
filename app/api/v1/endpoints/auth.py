from typing import Annotated
from datetime import timedelta
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Header, Request
from sqlalchemy import select

from app.core.workspace import resolve_workspace_slug, get_company_id_by_slug
from app.core.config import settings
from app.core.security import verify_password, create_access_token
from app.core.deps import SessionDep, OAuth2Form
from app.db.models.user import User
from app.schemas.user import Token

router = APIRouter()


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2Form,
    db: SessionDep,
    x_workspace: Annotated[
        str | None,
        Header(alias="X-Workspace", description="Workspace slug (e.g. test, xyz)"),
    ] = None,
    request: Request = None,
):
    """
    OAuth2 Password Flow token endpoint.

    **Multi-tenancy**:
    - Resolves workspace from Subdomain (UI) or `X-Workspace` header (API).
    - User is authenticated against the specific company context.
    - **Workspace slug** (e.g., `test`, `xyz`) is used instead of UUID.

    **Request format**:
    - Subdomain: `test.localhost` (Preferred for UI)
    - Header: `X-Workspace: test` (For API/Tools)
    - OR Username: `email|workspace-slug` (Fallback for Swagger)

    **Response**: JWT access token in Bearer token format.
    """
    # Resolve workspace slug
    slug = x_workspace
    email = form_data.username

    # Fallback: Check if username contains pipe separator for Swagger support
    if not slug and "|" in form_data.username:
        parts = form_data.username.split("|")
        if len(parts) == 2:
            email = parts[0].strip()
            slug = parts[1].strip()

    # If still no slug, try to resolve from request (subdomain)
    if not slug and request:
        slug = resolve_workspace_slug(request)

    if not slug:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing Workspace. Provide 'X-Workspace' header, use subdomain, or use 'email|workspace-slug' format in username.",
        )

    # Look up company_id from slug
    company_id_str = await get_company_id_by_slug(db, slug)
    if not company_id_str:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{slug}' not found",
        )

    try:
        company_id = UUID(company_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid workspace configuration",
        )

    # OAuth2PasswordRequestForm uses 'username' field, but we store email
    # Find user by email AND company_id (multi-tenancy)
    stmt = select(User).where(User.email == email, User.company_id == company_id)
    user = (await db.execute(stmt)).scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )

    # Create JWT access token with user information (includes company_id for company isolation)
    # Convert UUIDs to strings for JWT serialization
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.email,  # Subject (email) - standard JWT claim
            "user_id": str(user.id),  # Convert UUID to string for JWT
            "company_id": str(
                user.company_id
            ),  # Convert UUID to string for JWT - critical for company isolation
            "role": user.role.value,
        },
        expires_delta=access_token_expires,
    )

    return {"access_token": access_token, "token_type": "bearer"}
