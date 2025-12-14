from contextvars import ContextVar
from typing import Optional
from uuid import UUID

_company_id_ctx: ContextVar[Optional[UUID]] = ContextVar("company_id", default=None)


def get_company_id() -> Optional[UUID]:
    return _company_id_ctx.get()


def set_company_id(company_id: UUID) -> None:
    _company_id_ctx.set(company_id)


def reset_company_id() -> None:
    _company_id_ctx.set(None)
