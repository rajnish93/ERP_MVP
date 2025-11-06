from fastapi import APIRouter
from app.api.v1.endpoints import auth, companies, users, password_reset, employees, assets, expenses

api_router = APIRouter()
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(password_reset.router, prefix="/auth", tags=["authentication"])
api_router.include_router(employees.router, prefix="/employees", tags=["employees"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(expenses.router, prefix="/expenses", tags=["expenses"])

