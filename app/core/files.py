import os
import shutil
import uuid
from typing import Optional
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings

# Allowed mime types for security
ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "application/pdf"]
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

class FileService:
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        # Create upload directory if it doesn't exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def save_file(self, file: UploadFile) -> dict:
        """
        Save an uploaded file to disk.
        Returns a dict with 'url', 'filename', 'content_type'.
        """
        # 1. Validate File
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_MIME_TYPES)}"
            )
        
        # Check size
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        
        if size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB"
            )

        # 2. Generate Safe Filename
        ext = Path(file.filename).suffix.lower() if file.filename else ""
        if not ext:
             if file.content_type == "application/pdf": ext = ".pdf"
             elif file.content_type == "image/jpeg": ext = ".jpg"
             elif file.content_type == "image/png": ext = ".png"

        unique_filename = f"{uuid.uuid4()}{ext}"
        file_path = self.upload_dir / unique_filename

        # 3. Save to Disk
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not save file: {str(e)}"
            )

        # 4. Return Metadata
        file_url = f"/static/uploads/{unique_filename}"
        
        return {
            "url": file_url,
            "filename": unique_filename,
            "content_type": file.content_type,
            "original_filename": file.filename,
            "size": size
        }

    async def delete_file(self, file_url: str):
        """
        Delete a file from disk given its URL.
        """
        if not file_url:
            return

        # Extract filename from URL (assuming /static/uploads/filename)
        filename = os.path.basename(file_url)
        file_path = self.upload_dir / filename
        
        try:
            if file_path.exists():
                os.remove(file_path)
                return True
        except Exception as e:
            # We don't want to crash if delete fails, just log it
            print(f"Error acting deleting file {file_path}: {e}")
            return False
        return False

# Singleton instance
file_service = FileService(upload_dir="uploads")
