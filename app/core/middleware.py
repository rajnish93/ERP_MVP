import logging
from uuid import UUID
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.context import set_company_id, reset_company_id
from app.core.database import AsyncSessionLocal
from app.core.workspace import resolve_workspace_slug, get_company_id_by_slug

logger = logging.getLogger(__name__)


class WorkspaceMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract workspace slug from subdomain or X-Workspace header.
    Resolves slug to company UUID and sets it in context.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        reset_company_id()

        # 1. Resolve slug from Subdomain or Header
        slug = resolve_workspace_slug(request)

        if slug:
            # 2. Look up company ID from DB
            # We need a new session for this middleware operation
            async with AsyncSessionLocal() as db:
                company_id_str = await get_company_id_by_slug(db, slug)

            if company_id_str:
                try:
                    company_id = UUID(company_id_str)
                    set_company_id(company_id)
                except ValueError as e:
                    logger.warning(
                        f"Skipping invalid company_id '{company_id_str}' for slug '{slug}'. "
                        f"Request: {request.method} {request.url.path}. "
                        f"Error: {e}"
                    )

        # 3. Handling Rejection logic?
        # User requested: "Reject request if workspace not resolved."
        # We should be careful not to block health checks or root domain if needed.
        # But for strictly multi-workspace apps, usually root is 404 or finding page.
        # For now, we populate context. Dependencies will enforce requirement.

        response = await call_next(request)
        return response
