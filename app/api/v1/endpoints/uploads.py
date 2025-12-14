from typing import Annotated
from fastapi import APIRouter, UploadFile, File, status
from app.core.files import file_service
from app.core.deps import CurrentUser

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_file(
    _current_user: CurrentUser,
    file: Annotated[UploadFile, File()],
):
    """
    Upload a file (Image/PDF).
    Returns the file URL to be used in other resources (e.g., Expenses).
    """
    result = await file_service.save_file(file)
    return result
