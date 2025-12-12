from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
# from app.core.dependencies import get_current_user
from app.core.files import file_service
# from app.schemas.user import User

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    # current_user:  = Depends(get_current_user),
):
    """
    Upload a file (Image/PDF).
    Returns the file URL to be used in other resources (e.g., Expenses).
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file sent")
        
    result = await file_service.save_file(file)
    return result
