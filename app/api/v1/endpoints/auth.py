from datetime import timedelta
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.config import settings
from app.core.security import verify_password, create_access_token
from app.core.deps import SessionDep, OAuth2Form
from app.db.models.user import User
from app.schemas.user import Token

router = APIRouter()




@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2Form,
    db: SessionDep
):
    """
    OAuth2 Password Flow token endpoint.
    
    This is FastAPI's built-in OAuth2 with Password Flow. It uses form data
    (application/x-www-form-urlencoded) as per OAuth2 specification.
    
    **Note**: In OAuth2 Password Flow, the username field is used for email.
    
    **Request format**:
    - Content-Type: `application/x-www-form-urlencoded`
    - Fields: `username` (your email), `password`, `grant_type=password` (optional)
    
    **Response**: JWT access token in Bearer token format.
    
    **Usage in Swagger UI**:
    1. Click "Authorize" button at top
    2. Enter email as "username" and password
    3. Click "Authorize" to get token
    
    **Usage with curl**:
    ```bash
    curl -X POST "http://localhost/api/v1/auth/token" \\
      -H "Content-Type: application/x-www-form-urlencoded" \\
      -d "username=user@example.com&password=secret123"
    ```
    """
    # OAuth2PasswordRequestForm uses 'username' field, but we store email
    # Find user by email (email is passed as username in OAuth2 Password Flow)
    stmt = select(User).where(User.email == form_data.username)
    user = db.execute(stmt).scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create JWT access token with user information (includes company_id for tenant isolation)
    # Convert UUIDs to strings for JWT serialization
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.email,  # Subject (email) - standard JWT claim
            "user_id": str(user.id),  # Convert UUID to string for JWT
            "company_id": str(user.company_id),  # Convert UUID to string for JWT - critical for tenant isolation
            "role": user.role.value
        },
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}
