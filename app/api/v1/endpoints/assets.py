from typing import Optional
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.db.models.asset import Asset, AssetStatus
from app.db.models.employee import Employee
from app.db.models.user import User, UserRole
from app.core.dependencies import get_current_active_user, get_current_company_id, require_role
from app.schemas.asset import (
    AssetCreate,
    AssetUpdate,
    AssetAssign,
    AssetResponse,
    AssetListResponse,
    AssetDetailResponse,
)

router = APIRouter()


@router.post("/", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    asset_data: AssetCreate,
    db: Session = Depends(get_db),
    company_id: UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.HR)),
):
    """
    Create a new asset/device for the current company.
    
    **Access**: Admin and HR only
    
    **Tenant Isolation**: Assets are automatically assigned to the current user's company.
    
    **Request**:
    - name: Asset/item name
    - asset_type: Type of asset (laptop, monitor, etc.)
    - serial_number: Serial number (must be unique within company)
    - condition: Physical condition (excellent, good, fair, poor)
    - status: Initial status (defaults to 'available')
    """
    # Check if serial_number is unique within company
    existing_asset = db.query(Asset).filter(
        Asset.serial_number == asset_data.serial_number,
        Asset.company_id == company_id
    ).first()
    
    if existing_asset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset with serial number '{asset_data.serial_number}' already exists in your company"
        )
    
    # Create new asset
    new_asset = Asset(
        company_id=company_id,  # Tenant isolation
        name=asset_data.name,
        asset_type=asset_data.asset_type,
        serial_number=asset_data.serial_number,
        status=asset_data.status,
        condition=asset_data.condition,
        assigned_to=None,  # Initially unassigned
        issue_date=None,
    )
    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)
    
    return AssetResponse(
        id=new_asset.id,
        company_id=new_asset.company_id,
        name=new_asset.name,
        asset_type=new_asset.asset_type,
        serial_number=new_asset.serial_number,
        status=new_asset.status,
        condition=new_asset.condition,
        assigned_to=new_asset.assigned_to,
        issue_date=new_asset.issue_date,
        created_at=new_asset.created_at,
        updated_at=new_asset.updated_at,
    )


@router.get("/", response_model=AssetListResponse)
async def get_assets(
    db: Session = Depends(get_db),
    company_id: UUID = Depends(get_current_company_id),
    current_user: User = Depends(get_current_active_user),
    status_filter: Optional[AssetStatus] = Query(None, alias="status", description="Filter by asset status"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type"),
    assigned: Optional[bool] = Query(None, description="Filter by assignment status (true=assigned, false=unassigned)"),
    search: Optional[str] = Query(None, description="Search by name or serial number"),
):
    """
    List all assets for the current company.
    
    **Access**: All authenticated users (HR/Admin can see all, Employees see assigned assets)
    
    **Filters**:
    - status: Filter by asset status
    - asset_type: Filter by asset type
    - assigned: Filter by assignment status
    - search: Search by name or serial number
    """
    # Base query - tenant isolated
    query = db.query(Asset).filter(Asset.company_id == company_id)
    
    # Apply filters
    if status_filter:
        query = query.filter(Asset.status == status_filter)
    
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
    
    if assigned is not None:
        if assigned:
            query = query.filter(Asset.assigned_to.isnot(None))
        else:
            query = query.filter(Asset.assigned_to.is_(None))
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Asset.name.ilike(search_term),
                Asset.serial_number.ilike(search_term)
            )
        )
    
    # Employees can only see assets assigned to them
    if current_user.role == UserRole.EMPLOYEE:
        # Get employee record for current user
        employee = db.query(Employee).filter(
            Employee.user_id == current_user.id,
            Employee.company_id == company_id
        ).first()
        
        if employee:
            query = query.filter(Asset.assigned_to == employee.id)
        else:
            # Employee without employee record sees nothing
            return AssetListResponse(assets=[], total=0)
    
    assets = query.order_by(Asset.created_at.desc()).all()
    
    return AssetListResponse(
        assets=[
            AssetResponse(
                id=asset.id,
                company_id=asset.company_id,
                name=asset.name,
                asset_type=asset.asset_type,
                serial_number=asset.serial_number,
                status=asset.status,
                condition=asset.condition,
                assigned_to=asset.assigned_to,
                issue_date=asset.issue_date,
                created_at=asset.created_at,
                updated_at=asset.updated_at,
            )
            for asset in assets
        ],
        total=len(assets),
    )


@router.get("/{asset_id}", response_model=AssetDetailResponse)
async def get_asset(
    asset_id: UUID,
    db: Session = Depends(get_db),
    company_id: UUID = Depends(get_current_company_id),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get asset details by ID.
    
    **Access**: All authenticated users (Employees can only view assets assigned to them)
    """
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.company_id == company_id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Employees can only see assets assigned to them
    if current_user.role == UserRole.EMPLOYEE:
        employee = db.query(Employee).filter(
            Employee.user_id == current_user.id,
            Employee.company_id == company_id
        ).first()
        
        if not employee or asset.assigned_to != employee.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only view assets assigned to you."
            )
    
    # Get employee details if assigned
    employee_data = None
    if asset.assigned_to:
        employee = db.query(Employee).filter(Employee.id == asset.assigned_to).first()
        if employee:
            employee_data = {
                "id": str(employee.id),
                "name": employee.name,
                "department": employee.department,
                "role": employee.role,
                "employee_id": employee.employee_id,
            }
    
    return AssetDetailResponse(
        id=asset.id,
        company_id=asset.company_id,
        name=asset.name,
        asset_type=asset.asset_type,
        serial_number=asset.serial_number,
        status=asset.status,
        condition=asset.condition,
        assigned_to=asset.assigned_to,
        issue_date=asset.issue_date,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        employee=employee_data,
    )


@router.patch("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: UUID,
    asset_data: AssetUpdate,
    db: Session = Depends(get_db),
    company_id: UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.HR)),
):
    """
    Update asset details.
    
    **Access**: Admin and HR only
    
    **Note**: To assign/unassign assets, use the /assign endpoint.
    """
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.company_id == company_id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Check if serial_number is unique (if being updated)
    if asset_data.serial_number and asset_data.serial_number != asset.serial_number:
        existing_asset = db.query(Asset).filter(
            Asset.serial_number == asset_data.serial_number,
            Asset.company_id == company_id,
            Asset.id != asset_id
        ).first()
        
        if existing_asset:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Asset with serial number '{asset_data.serial_number}' already exists in your company"
            )
    
    # Update fields
    update_data = asset_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(asset, field, value)
    
    db.commit()
    db.refresh(asset)
    
    return AssetResponse(
        id=asset.id,
        company_id=asset.company_id,
        name=asset.name,
        asset_type=asset.asset_type,
        serial_number=asset.serial_number,
        status=asset.status,
        condition=asset.condition,
        assigned_to=asset.assigned_to,
        issue_date=asset.issue_date,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


@router.post("/{asset_id}/assign", response_model=AssetResponse)
async def assign_asset(
    asset_id: UUID,
    assign_data: AssetAssign,
    db: Session = Depends(get_db),
    company_id: UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.HR)),
):
    """
    Assign an asset to an employee.
    
    **Access**: Admin and HR only
    
    **Request**:
    - employee_id: Employee ID to assign asset to
    
    **Note**: If asset is already assigned to another employee, it will be reassigned.
    Automatically sets status to 'assigned' and issue_date to current date.
    """
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.company_id == company_id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Verify employee exists and belongs to same company
    employee = db.query(Employee).filter(
        Employee.id == assign_data.employee_id,
        Employee.company_id == company_id
    ).first()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found in your company"
        )
    
    # Assign asset to employee
    asset.assigned_to = assign_data.employee_id
    asset.status = AssetStatus.ASSIGNED
    asset.issue_date = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(asset)
    
    return AssetResponse(
        id=asset.id,
        company_id=asset.company_id,
        name=asset.name,
        asset_type=asset.asset_type,
        serial_number=asset.serial_number,
        status=asset.status,
        condition=asset.condition,
        assigned_to=asset.assigned_to,
        issue_date=asset.issue_date,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


@router.post("/{asset_id}/unassign", response_model=AssetResponse)
async def unassign_asset(
    asset_id: UUID,
    db: Session = Depends(get_db),
    company_id: UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.HR)),
):
    """
    Unassign an asset from an employee.
    
    **Access**: Admin and HR only
    
    **Note**: Automatically sets status to 'available' and clears issue_date.
    """
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.company_id == company_id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    if not asset.assigned_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset is not currently assigned to any employee"
        )
    
    # Unassign asset
    asset.assigned_to = None
    asset.status = AssetStatus.AVAILABLE
    asset.issue_date = None
    
    db.commit()
    db.refresh(asset)
    
    return AssetResponse(
        id=asset.id,
        company_id=asset.company_id,
        name=asset.name,
        asset_type=asset.asset_type,
        serial_number=asset.serial_number,
        status=asset.status,
        condition=asset.condition,
        assigned_to=asset.assigned_to,
        issue_date=asset.issue_date,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: UUID,
    db: Session = Depends(get_db),
    company_id: UUID = Depends(get_current_company_id),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Delete an asset.
    
    **Access**: Admin only
    
    **Note**: Only unassigned assets can be deleted. Assign assets to 'retired' status instead of deleting.
    """
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.company_id == company_id
    ).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    if asset.assigned_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete asset that is assigned to an employee. Unassign it first."
        )
    
    db.delete(asset)
    db.commit()
    
    return None

