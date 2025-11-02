from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api_router
from app.core.config import settings

# Create main FastAPI app with all routes under /api/v1
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="FastAPI application with Docker and Nginx",
    docs_url=f"{settings.API_V1_STR}/docs",  # Only Swagger at /api/v1/docs
    redoc_url=None,  # Disable ReDoc
    openapi_url=f"{settings.API_V1_STR}/openapi.json",  # Required for Swagger docs to work
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API router under /api/v1 prefix (includes items endpoints)
app.include_router(api_router, prefix=settings.API_V1_STR)


# Health check endpoint (keep at root for Docker health checks)
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

