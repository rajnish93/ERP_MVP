import logging
from typing import Optional
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import or_, select

from app.core.deps import SessionDep, CurrentCompanyId, CurrentUser
from app.core.error_handlers import handle_db_operation
from app.db.models.asset import Asset, AssetStatus
from app.db.models.employee import Employee
from app.db.models.user import User, UserRole
from app.core.dependencies import require_role
from app.schemas.asset import (
    AssetCreate,
    AssetUpdate,
    AssetAssign,
    AssetResponse,
    AssetListResponse,
    AssetDetailResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    asset_data: AssetCreate,
    db: SessionDep,
    company_id: CurrentCompanyId,
    _current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.HR)),
):
    """
    Create a new asset/device for the current company.
    
    **Access**: Admin and HR only
    
    **Company Isolation**: Assets are automatically assigned to the current user's company.
    
    **Request**:
    - name: Asset/item name
    - asset_type: Type of asset (laptop, monitor, etc.)
    - serial_number: Serial number (must be unique within company)
    - condition: Physical condition (excellent, good, fair, poor)
    - status: Initial status (defaults to 'available')
    """
    # Check if serial_number is unique within company
    stmt = select(Asset).where(
        Asset.serial_number == asset_data.serial_number,
        Asset.company_id == company_id
    )
    existing_asset = (await db.execute(stmt)).scalars().first()
    
    if existing_asset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset with serial number '{asset_data.serial_number}' already exists in your company"
        )
    
    # Create new asset
    new_asset = Asset(
        company_id=company_id,  # Company isolation
        name=asset_data.name,
        asset_type=asset_data.asset_type,
        serial_number=asset_data.serial_number,
        status=asset_data.status,
        condition=asset_data.condition,
        assigned_to=None,  # Initially unassigned
        issue_date=None,
    )
    async with handle_db_operation(db, "create asset"):
        db.add(new_asset)
        await db.commit()
        await db.refresh(new_asset)
    
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
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: CurrentUser,
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
    # Base query - company isolated
    stmt = select(Asset).where(Asset.company_id == company_id)
    
    # Apply filters
    if status_filter:
        stmt = stmt.where(Asset.status == status_filter)
    
    if asset_type:
        stmt = stmt.where(Asset.asset_type == asset_type)
    
    if assigned is not None:
        if assigned:
            stmt = stmt.where(Asset.assigned_to.isnot(None))
        else:
            stmt = stmt.where(Asset.assigned_to.is_(None))
    
    if search:
        search_term = f"%{search}%"
        stmt = stmt.where(
            or_(
                Asset.name.ilike(search_term),
                Asset.serial_number.ilike(search_term)
            )
        )
    
    # Employees can only see assets assigned to them
    if current_user.role == UserRole.EMPLOYEE:
        # Get employee record for current user
        emp_stmt = select(Employee).where(
            Employee.user_id == current_user.id,
            Employee.company_id == company_id
        )
        employee = (await db.execute(emp_stmt)).scalars().first()
        
        if employee:
            stmt = stmt.where(Asset.assigned_to == employee.id)
        else:
            # Employee without employee record sees nothing
            return AssetListResponse(assets=[], total=0)
    
    # Eager load employee relationship for name display
    from sqlalchemy.orm import selectinload
    stmt = stmt.options(selectinload(Asset.employee))
    
    assets = (await db.execute(stmt.order_by(Asset.created_at.desc()))).scalars().all()
    
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
                employee_name=asset.employee.name,
                employee_code=asset.employee.employee_id,
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
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: CurrentUser,
):
    """
    Get asset details by ID.
    
    **Access**: All authenticated users (Employees can only view assets assigned to them)
    """
    stmt = select(Asset).where(
        Asset.id == asset_id,
        Asset.company_id == company_id
    )
    asset = (await db.execute(stmt)).scalars().first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Employees can only see assets assigned to them
    if current_user.role == UserRole.EMPLOYEE:
        stmt = select(Employee).where(
            Employee.user_id == current_user.id,
            Employee.company_id == company_id
        )
        employee = (await db.execute(stmt)).scalars().first()
        
        if not employee or asset.assigned_to != employee.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only view assets assigned to you."
            )
    
    # Get employee details if assigned
    employee_data = None
    if asset.assigned_to:
        stmt = select(Employee).where(Employee.id == asset.assigned_to)
        assigned_employee = (await db.execute(stmt)).scalars().first()
        if assigned_employee:
            employee_data = {
                "id": str(assigned_employee.id),
                "name": assigned_employee.name,
                "department": assigned_employee.department,
                "role": assigned_employee.role,
                "employee_id": assigned_employee.employee_id,
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
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.HR)),
):
    """
    Update asset details.
    
    **Access**: Admin and HR only
    
    **Note**: To assign/unassign assets, use the /assign endpoint.
    """
    stmt = select(Asset).where(
        Asset.id == asset_id,
        Asset.company_id == company_id
    )
    asset = (await db.execute(stmt)).scalars().first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Check if serial_number is unique (if being updated)
    if asset_data.serial_number and asset_data.serial_number != asset.serial_number:
        stmt = select(Asset).where(
            Asset.serial_number == asset_data.serial_number,
            Asset.company_id == company_id,
            Asset.id != asset_id
        )
        existing_asset = (await db.execute(stmt)).scalars().first()
        
        if existing_asset:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Asset with serial number '{asset_data.serial_number}' already exists in your company"
            )
    
    # Update fields
    update_data = asset_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(asset, field, value)
    
    async with handle_db_operation(db, "update asset"):
        await db.commit()
        await db.refresh(asset)
    
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
    db: SessionDep,
    company_id: CurrentCompanyId,
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
    stmt = select(Asset).where(
        Asset.id == asset_id,
        Asset.company_id == company_id
    )
    asset = (await db.execute(stmt)).scalars().first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Verify employee exists and belongs to same company
    stmt = select(Employee).where(
        Employee.id == assign_data.employee_id,
        Employee.company_id == company_id
    )
    employee = (await db.execute(stmt)).scalars().first()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found in your company"
        )
    
    # Check if asset is being reassigned from another employee
    if asset.assigned_to and asset.assigned_to != assign_data.employee_id:
        # Log the reassignment for audit trail
        logger.warning(
            f"Asset {asset.id} (serial: {asset.serial_number}) reassigned from employee "
            f"{asset.assigned_to} to {assign_data.employee_id} by user {current_user.id}"
        )
    
    # Assign asset to employee
    asset.assigned_to = assign_data.employee_id
    asset.status = AssetStatus.ASSIGNED
    asset.issue_date = datetime.now(timezone.utc)
    
    async with handle_db_operation(db, "assign asset"):
        await db.commit()
        await db.refresh(asset)
    
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
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.HR)),
):
    """
    Unassign an asset from an employee.
    
    **Access**: Admin and HR only
    
    **Note**: Automatically sets status to 'available' and clears issue_date.
    """
    stmt = select(Asset).where(
        Asset.id == asset_id,
        Asset.company_id == company_id
    )
    asset = (await db.execute(stmt)).scalars().first()
    
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
    
    async with handle_db_operation(db, "unassign asset"):
        await db.commit()
        await db.refresh(asset)
    
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
    db: SessionDep,
    company_id: CurrentCompanyId,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Delete an asset.
    
    **Access**: Admin only
    
    **Note**: Only unassigned assets can be deleted. Assign assets to 'retired' status instead of deleting.
    """
    stmt = select(Asset).where(
        Asset.id == asset_id,
        Asset.company_id == company_id
    )
    asset = (await db.execute(stmt)).scalars().first()
    
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
    
    async with handle_db_operation(db, "delete asset"):
        await db.delete(asset)
        await db.commit()
    
    return None
