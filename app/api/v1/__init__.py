from fastapi import APIRouter
from app.api.v1.endpoints import items, auth, companies, users, password_reset

api_router = APIRouter()
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(password_reset.router, prefix="/auth", tags=["authentication"])
api_router.include_router(items.router, prefix="/items", tags=["items"])

