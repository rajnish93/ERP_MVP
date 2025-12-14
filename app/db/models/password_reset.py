from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.database import UUIDMixin, TimestampMixin, CompanyMixin

class PasswordResetToken(Base, UUIDMixin, TimestampMixin, CompanyMixin):
    __tablename__ = "password_reset_tokens"

    token: Mapped[str] = mapped_column(String, unique=True)
    email: Mapped[str] = mapped_column(String, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
