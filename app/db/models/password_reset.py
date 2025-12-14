from datetime import datetime, timezone
from uuid import UUID
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    token: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, index=True, nullable=False)
    company_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    # Optional: Link to user if we wanted foreign key constraints, 
    # but email+company_id is sufficient as implemented in endpoints
    # user_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"))
