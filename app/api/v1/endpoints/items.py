from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.dependencies import get_current_active_user, get_current_company_id
from app.models.user import User

router = APIRouter()


class Item(BaseModel):
    id: int
    company_id: int  # Tenant isolation
    name: str
    description: str = None
    price: float


class ItemCreate(BaseModel):
    name: str
    description: str = None
    price: float


# In-memory storage for demo purposes (tenant-aware)
items_db = []
next_id = 1


@router.get("/", response_model=List[Item])
async def get_items(
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all items for the current company (tenant).
    
    **Tenant Isolation**: Users can only see items from their own company.
    """
    company_items = [item for item in items_db if item.get("company_id") == company_id]
    return company_items


@router.get("/{item_id}", response_model=Item)
async def get_item(
    item_id: int,
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a specific item by ID (tenant-aware).
    
    **Tenant Isolation**: Users can only access items from their own company.
    """
    item = next(
        (item for item in items_db if item["id"] == item_id and item.get("company_id") == company_id),
        None
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in your company"
        )
    return item


@router.post("/", response_model=Item, status_code=status.HTTP_201_CREATED)
async def create_item(
    item: ItemCreate,
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new item for the current company (tenant).
    
    **Tenant Isolation**: Items are automatically assigned to the current user's company.
    """
    global next_id
    new_item = {
        "id": next_id,
        "company_id": company_id,  # Tenant isolation
        "name": item.name,
        "description": item.description,
        "price": item.price,
    }
    items_db.append(new_item)
    next_id += 1
    return new_item


@router.put("/{item_id}", response_model=Item)
async def update_item(
    item_id: int,
    item: ItemCreate,
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update an existing item (tenant-aware).
    
    **Tenant Isolation**: Users can only update items from their own company.
    """
    existing_item = next(
        (i for i in items_db if i["id"] == item_id and i.get("company_id") == company_id),
        None
    )
    if not existing_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in your company"
        )
    
    existing_item.update({
        "name": item.name,
        "description": item.description,
        "price": item.price,
    })
    return existing_item


@router.delete("/{item_id}", status_code=status.HTTP_200_OK)
async def delete_item(
    item_id: int,
    company_id: int = Depends(get_current_company_id),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete an item (tenant-aware).
    
    **Tenant Isolation**: Users can only delete items from their own company.
    """
    global items_db
    item = next(
        (i for i in items_db if i["id"] == item_id and i.get("company_id") == company_id),
        None
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in your company"
        )
    items_db = [i for i in items_db if not (i["id"] == item_id and i.get("company_id") == company_id)]
    return {"message": "Item deleted successfully"}

