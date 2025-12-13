import os
from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles

from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1 import api_router
from app.core.config import settings
from app.core.middleware import WorkspaceMiddleware

# Create main FastAPI app with all routes under /api/v1
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="FastAPI application with Docker and Nginx",
    docs_url=f"{settings.API_V1_STR}/docs",  # Only Swagger at /api/v1/docs
    redoc_url=None,  # Disable ReDoc
    openapi_url=f"{settings.API_V1_STR}/openapi.json",  # Required for Swagger docs to work
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom validation error handler for better, user-friendly error messages"""
    errors = []
    for error in exc.errors():
        # Get field path (e.g., "body -> admin_password")
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        field_name = field_path.split(" -> ")[-1] if " -> " in field_path else str(error["loc"][-1])
        
        # Default message
        msg = error["msg"]
        
        # Custom messages for specific validation errors
        if error["type"] == "string_too_short":
            if "password" in field_name.lower():
                msg = "Password must be at least 8 characters long. Please choose a stronger password."
            else:
                min_length = error.get("ctx", {}).get("min_length", "required")
                msg = f"{field_name} is too short. Minimum length is {min_length} characters."
        
        elif error["type"] == "string_too_long":
            if "password" in field_name.lower():
                msg = "Password cannot exceed 72 characters."
            else:
                max_length = error.get("ctx", {}).get("max_length", "maximum")
                msg = f"{field_name} is too long. Maximum length is {max_length} characters."
        
        elif error["type"] == "value_error":
            msg = f"Invalid value for {field_name}. {msg}"
        
        elif error["type"] == "missing":
            msg = f"{field_name} is required."
        
        errors.append({
            "field": field_name,
            "field_path": field_path,
            "message": msg,
            "type": error["type"],
            "input": error.get("input")
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": errors,
            "message": "Validation error. Please check the input data and try again.",
            "error_count": len(errors)
        }
    )

# Note: Database migrations are handled by Alembic
# Run migrations manually: alembic upgrade head
# Or use startup script to auto-migrate in Docker


# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add Workspace Middleware
app.add_middleware(WorkspaceMiddleware)

# Include API router under /api/v1 prefix
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount uploads directory to serve static files (e.g., http://localhost:8000/static/uploads/...)
# Ensure directory exists
os.makedirs("uploads", exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory="uploads"), name="uploads")



# Health check endpoint (keep at root for Docker health checks)
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

