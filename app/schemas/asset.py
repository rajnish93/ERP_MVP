from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from app.db.models.asset import AssetType, AssetStatus, AssetCondition


class AssetBase(BaseModel):
    """Base asset schema with common fields"""

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Asset/item name (e.g., 'MacBook Pro 16')",
    )
    asset_type: AssetType = Field(..., description="Type of asset")
    serial_number: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Serial number - unique within company",
    )
    condition: AssetCondition = Field(
        default=AssetCondition.EXCELLENT, description="Physical condition of the asset"
    )


class AssetCreate(AssetBase):
    """Schema for creating a new asset"""

    status: AssetStatus = Field(
        default=AssetStatus.AVAILABLE, description="Initial status of the asset"
    )


class AssetUpdate(BaseModel):
    """Schema for updating an asset (all fields optional)"""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    asset_type: Optional[AssetType] = None
    serial_number: Optional[str] = Field(None, min_length=1, max_length=100)
    status: Optional[AssetStatus] = None
    condition: Optional[AssetCondition] = None


class AssetAssign(BaseModel):
    """Schema for assigning/unassigning an asset to/from an employee"""

    employee_id: UUID = Field(
        ...,
        description="Employee ID to assign asset to. Use this to assign or reassign.",
    )


class AssetResponse(AssetBase):
    """Schema for asset response"""

    id: UUID
    company_id: UUID
    status: AssetStatus
    assigned_to: Optional[UUID] = Field(
        None, description="Employee ID currently assigned this asset"
    )
    issue_date: Optional[datetime] = Field(
        None, description="Date when asset was issued/assigned to current employee"
    )
    employee_name: Optional[str] = Field(
        None, description="Name of the assigned employee"
    )
    employee_code: Optional[str] = Field(
        None, description="Employee code of the assigned employee"
    )
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssetListResponse(BaseModel):
    """Response schema for asset list"""

    assets: list[AssetResponse]
    total: int


class AssetDetailResponse(AssetResponse):
    """Extended asset response with employee details"""

    employee: Optional[dict] = Field(
        None, description="Employee details if asset is assigned"
    )

    model_config = ConfigDict(from_attributes=True)
