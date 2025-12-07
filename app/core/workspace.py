import re
from typing import Optional
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.company import Company

# Regex to validate slug format (alphanumeric, hyphens)
SLUG_REGEX = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')

def extract_subdomain(host: str) -> Optional[str]:
    """
    Extract subdomain from hostname.
    Handles localhost, IPs, and configured domain.
    
    Examples:
    - test.localhost -> test
    - test.app.com -> test
    - localhost -> None
    - 127.0.0.1 -> None
    """
    if not host:
        return None
        
    # Remove port if present
    hostname = host.split(":")[0].lower()
    
    # Skip IP addresses
    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", hostname):
        return None
        
    # Skip plain localhost
    if hostname == "localhost":
        return None
    
    # Split by dots
    parts = hostname.split(".")
    
    # Logic: If we have parts, and it's not just a top-level domain or localhost
    # Simple heuristic: take the first part if there are at least 2 parts (e.g. sub.localhost)
    # or 3 parts for standard domains (sub.domain.com)
    # But wait, 'localhost' is 1 part. 'test.localhost' is 2 parts.
    # 'app.com' is 2 parts. 'test.app.com' is 3 parts.
    
    # Let's assume for MVP:
    # If ends with 'localhost', requires 2 parts.
    if hostname.endswith(".localhost"):
        if len(parts) >= 2:
            return parts[0]
        return None
        
    # For user config "DOMAIN" (e.g. app.com)
    # If using lvh.me or similar
    if len(parts) >= 3: # e.g. workspace.lvh.me
        return parts[0]
        
    # Fallback for 'test.localhost' case handled above.
    
    return None

def resolve_workspace_slug(request: Request) -> Optional[str]:
    """
    Resolve workspace slug from Request.
    Priority:
    1. Subdomain (UI/Browser)
    2. X-Workspace Header (API/Tools)
    """
    host = request.headers.get("host", "")
    subdomain = extract_subdomain(host)
    
    if subdomain:
        return subdomain
        
    # Fallback to header
    header_slug = request.headers.get("X-Workspace")
    if header_slug:
        return header_slug.lower()
        
    return None

async def get_company_id_by_slug(db: AsyncSession, slug: str) -> Optional[str]:
    """Fetch company UUID by slug"""
    query = select(Company.id).where(Company.slug == slug)
    result = await db.execute(query)
    company_id = result.scalar_one_or_none()
    return str(company_id) if company_id else None
