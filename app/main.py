import os
import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1 import api_router
from app.core.config import settings
from app.core.middleware import WorkspaceMiddleware
from app.core.rate_limit import limiter, RateLimitExceeded, _rate_limit_exceeded_handler

# Create main FastAPI app with all routes under /api/v1
# conditionally hide docs in production
docs_url = (
    f"{settings.API_V1_STR}/docs"
    if settings.ENVIRONMENT.lower() != "production"
    else None
)
openapi_url = (
    f"{settings.API_V1_STR}/openapi.json"
    if settings.ENVIRONMENT.lower() != "production"
    else None
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="FastAPI application with Docker and Nginx",
    docs_url=docs_url,
    redoc_url=None,  # Disable ReDoc always (or make conditional too)
    openapi_url=openapi_url,
)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom validation error handler for better, user-friendly error messages"""
    errors = []
    for error in exc.errors():
        # Get field path (e.g., "body -> admin_password")
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        field_name = (
            field_path.split(" -> ")[-1]
            if " -> " in field_path
            else str(error["loc"][-1])
        )

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

        error_detail = {
            "field": field_name,
            "field_path": field_path,
            "message": msg,
            "type": error["type"],
        }

        # Only include input in non-production environments to avoid leaking sensitive data
        if settings.ENVIRONMENT.lower() != "production":
            error_detail["input"] = error.get("input")

        errors.append(error_detail)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": errors,
            "message": "Validation error. Please check the input data and try again.",
            "error_count": len(errors),
        },
    )


# Note: Database migrations are handled by Alembic
# Run migrations manually: alembic upgrade head
# Or use startup script to auto-migrate in Docker


# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_origin_regex=settings.BACKEND_CORS_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add Workspace Middleware
app.add_middleware(WorkspaceMiddleware)

# Add Trusted Host Middleware (Security)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# Include API router under /api/v1 prefix
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount uploads directory to serve static files REMOVED for security
# Files are now served via authenticated endpoint /api/v1/uploads/{filename}
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
# app.mount("/static/uploads", StaticFiles(directory="uploads"), name="uploads")


# Health check endpoint (keep at root for Docker health checks)
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
