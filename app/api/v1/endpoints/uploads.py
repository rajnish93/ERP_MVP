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


@router.get("/{filename}", status_code=status.HTTP_200_OK)
async def get_file(
    filename: str,
    _current_user: CurrentUser,
):
    """
    Get a file secure.
    Only authenticated users can access.
    """
    from fastapi.responses import FileResponse
    from app.core.config import settings

    # import os (removed in favor of pathlib)
    from pathlib import Path
    from fastapi import HTTPException

    # Use pathlib for path traversal protection
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    requested_file = (upload_dir / filename).resolve()

    # 1. Normalize and resolve both paths
    # 2. Check if the resolved file is relative to the upload directory
    if not requested_file.is_relative_to(upload_dir):
        # This catches ".." attempts that go outside the dir
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    if not requested_file.exists() or not requested_file.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    return FileResponse(requested_file)
