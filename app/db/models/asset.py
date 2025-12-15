from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
import uuid

from app.core.database import Base, UUIDMixin, TimestampMixin, CompanyMixin
from app.core.types import EnumType

if TYPE_CHECKING:
    from app.db.models.company import Company
    from app.db.models.employee import Employee


class AssetType(str, enum.Enum):
    """Asset/Device types"""

    LAPTOP = "laptop"
    MONITOR = "monitor"
    MOUSE = "mouse"
    KEYBOARD = "keyboard"
    PHONE = "phone"
    TABLET = "tablet"
    OTHER = "other"


class AssetStatus(str, enum.Enum):
    """Asset status"""

    AVAILABLE = "available"
    ASSIGNED = "assigned"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"


class AssetCondition(str, enum.Enum):
    """Asset condition"""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class Asset(Base, UUIDMixin, TimestampMixin, CompanyMixin):
    """
    Asset/Device model - tracks devices issued to employees

    Assets belong to a company and can be assigned to employees.
    Each asset has a status, condition, and assignment history.
    """

    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('available', 'assigned', 'maintenance', 'retired')",
            name="ck_assets_status",
        ),
        CheckConstraint(
            "condition IN ('excellent', 'good', 'fair', 'poor')",
            name="ck_assets_condition",
        ),
        UniqueConstraint(
            "company_id", "serial_number", name="uq_assets_company_serial"
        ),
    )

    name: Mapped[str] = mapped_column(
        String(200),
        index=True,
        comment="Asset/item name (e.g., 'MacBook Pro 16')",
    )
    asset_type: Mapped[AssetType] = mapped_column(
        EnumType(AssetType, length=50),
        comment="Type of asset (laptop, monitor, etc.)",
    )
    serial_number: Mapped[str] = mapped_column(
        String(100),
        index=True,
        comment="Serial number - unique within company",
    )
    status: Mapped[AssetStatus] = mapped_column(
        EnumType(AssetStatus, length=50),
        default=AssetStatus.AVAILABLE,
        server_default=AssetStatus.AVAILABLE.value,
        index=True,
        comment="Current status of the asset",
    )
    condition: Mapped[AssetCondition] = mapped_column(
        EnumType(AssetCondition, length=50),
        default=AssetCondition.EXCELLENT,
        server_default=AssetCondition.EXCELLENT.value,
        comment="Physical condition of the asset",
    )
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL", name="fk_assets_employee"),
        nullable=True,
        index=True,
        comment="Employee currently assigned this asset. NULL if unassigned.",
    )
    issue_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date when asset was issued/assigned to current employee",
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="assets")
    employee: Mapped[Optional["Employee"]] = relationship(
        "Employee", back_populates="assets"
    )

    def __repr__(self) -> str:
        """String representation of Asset"""
        assigned_status = (
            f"assigned_to={self.assigned_to}" if self.assigned_to else "unassigned"
        )
        return f"<Asset(id={self.id}, name={self.name}, status={self.status.value}, {assigned_status})>"
