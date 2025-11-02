from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets

from app.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Password reset token storage (in-memory, replace with Redis/database in production)
password_reset_tokens: dict[str, dict] = {}  # token -> {email, expires_at, company_id}


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


def create_password_reset_token(email: str, company_id: int) -> str:
    """Create and store a password reset token"""
    token = generate_password_reset_token()
    expires_at = datetime.utcnow() + timedelta(minutes=15)  # 15 minute expiry
    password_reset_tokens[token] = {
        "email": email,
        "company_id": company_id,
        "expires_at": expires_at
    }
    return token


def verify_password_reset_token(token: str) -> Optional[dict]:
    """Verify and return password reset token data if valid"""
    token_data = password_reset_tokens.get(token)
    if not token_data:
        return None
    
    if datetime.utcnow() > token_data["expires_at"]:
        # Token expired, remove it
        password_reset_tokens.pop(token, None)
        return None
    
    return token_data


def invalidate_password_reset_token(token: str):
    """Remove a password reset token after use"""
    password_reset_tokens.pop(token, None)

