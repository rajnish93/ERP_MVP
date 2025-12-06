from typing import Annotated
from uuid import UUID
from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_current_company_id
from app.db.models.user import User

SessionDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]
CurrentCompanyId = Annotated[UUID, Depends(get_current_company_id)]
OAuth2Form = Annotated[OAuth2PasswordRequestForm, Depends()]

