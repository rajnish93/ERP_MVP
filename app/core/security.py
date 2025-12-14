from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.config import settings
from app.db.models.password_reset import PasswordResetToken

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Password reset token storage (in-memory, replace with Redis/database in production)



def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Truncates password to 72 bytes to match bcrypt's limit and ensure
    consistent verification (passwords are truncated during hashing).
    """
    # Truncate to 72 bytes to match hashing behavior
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
        plain_password = password_bytes.decode('utf-8', errors='ignore')
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Bcrypt has a 72-byte limit for passwords. This function truncates
    passwords longer than 72 bytes to ensure compatibility.
    """
    # Truncate to 72 bytes (not characters) to respect bcrypt's limit
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
        password = password_bytes.decode('utf-8', errors='ignore')
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_password_reset_token() -> str:
    """Generate a secure random token for password reset"""
    return secrets.token_urlsafe(32)


async def create_password_reset_token(db: AsyncSession, email: str, company_id: UUID) -> str:
    """Create and store a password reset token"""
    token = generate_password_reset_token()
    expires_at = datetime.utcnow() + timedelta(minutes=15)  # 15 minute expiry
    
    db_token = PasswordResetToken(
        token=token,
        email=email,
        company_id=company_id,
        expires_at=expires_at
    )
    db.add(db_token)
    await db.commit()
    return token


async def verify_password_reset_token(db: AsyncSession, token: str) -> Optional[dict]:
    """Verify and return password reset token data if valid"""
    stmt = select(PasswordResetToken).where(PasswordResetToken.token == token)
    result = await db.execute(stmt)
    db_token = result.scalars().first()
    
    if not db_token:
        return None
    
    # Check expiry (ensure unaware datetime comparisons work appropriately, usually DB returns timezone-aware)
    # Using specific timezone logic if needed, but for now assuming UTC consistency
    if db_token.expires_at.replace(tzinfo=None) < datetime.utcnow():
        # Token expired, remove it
        await invalidate_password_reset_token(db, token)
        return None
    
    return {
        "email": db_token.email,
        "company_id": db_token.company_id,
        "token": db_token.token
    }


async def invalidate_password_reset_token(db: AsyncSession, token: str):
    """Remove a password reset token after use"""
    stmt = delete(PasswordResetToken).where(PasswordResetToken.token == token)
    await db.execute(stmt)
    await db.commit()

