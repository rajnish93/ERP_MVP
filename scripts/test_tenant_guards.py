import urllib.request
import urllib.parse
import sys
import asyncio
from typing import Optional
from sqlalchemy import select
from pathlib import Path

# Add parent directory to path to import app modules if not already there
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.db.models.company import Company  # noqa: E402

BASE_URL = "http://localhost/api/v1"

# Known admin credentials from create_test_data
ADMIN_EMAIL = "admin2@millerhenderson.com"
ADMIN_PASSWORD = "admin123"

def make_request(url, data=None, headers=None):
    if data:
        data = urllib.parse.urlencode(data).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    
    try:
        with urllib.request.urlopen(req) as response:
            return response.getcode(), response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8')
    except urllib.error.URLError as e:
        print(f"❌ Connection error: {e}")
        return None, None

async def get_workspace_slug_for_email(email: str) -> Optional[str]:
    """Fetch the workspace slug for the given user email"""
    async with AsyncSessionLocal() as db:
        from app.db.models.user import User
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalars().first()
        if user:
            # Get the company slug
            company_stmt = select(Company.slug).where(Company.id == user.company_id)
            company_result = await db.execute(company_stmt)
            return company_result.scalar_one_or_none()
        return None

def test_login_missing_header():
    print("Testing Login Missing Workspace...")
    code, body = make_request(
        f"{BASE_URL}/auth/token",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "grant_type": "password"}
    )
    if code == 422:
        print("✅ Correctly rejected missing workspace (422)")
    else:
        print(f"❌ Failed: Expected 422, got {code}")
        print(body)

def test_login_wrong_workspace():
    print("\nTesting Login Wrong Workspace...")
    code, body = make_request(
        f"{BASE_URL}/auth/token",
        headers={"X-Workspace": "nonexistent-workspace-slug"},
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "grant_type": "password"}
    )
    # Should be 404 because workspace not found
    if code == 404:
        print("✅ Correctly rejected wrong workspace (404)")
    else:
        print(f"❌ Failed: Expected 404, got {code}")
        print(body)


def test_login_success(workspace_slug: str):
    print("\nTesting Login Success (Correct Credentials + Correct Workspace)...")
    if not workspace_slug:
        print("⚠️  Skipping success test: Could not find user in database.")
        return

    code, body = make_request(
        f"{BASE_URL}/auth/token",
        headers={"X-Workspace": workspace_slug},
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "grant_type": "password"}
    )
    if code == 200:
        print("✅ Login Successful! (200 OK)")
        print(f"   Workspace slug used: {workspace_slug}")
    else:
        print(f"❌ Failed: Expected 200, got {code}")
        print(body)

def test_swagger_fallback(workspace_slug: str):
    print("\nTesting Swagger Fallback (Slug in Username, No Header)...")
    
    # Construct username with pipe separator
    swagger_username = f"{ADMIN_EMAIL}|{workspace_slug}"
    
    code, body = make_request(
        f"{BASE_URL}/auth/token",
        # NO HEADERS sent here
        data={"username": swagger_username, "password": ADMIN_PASSWORD, "grant_type": "password"}
    )
    if code == 200:
        print("✅ Swagger Fallback Successful! (200 OK)")
    else:
        print(f"❌ Failed: Expected 200, got {code}")
        print(body)

async def main():
    if len(sys.argv) > 1:
        print("Running tests...")
    
    # 1. Negative Test: Missing Workspace
    test_login_missing_header()
    
    # 2. Negative Test: Wrong Workspace
    test_login_wrong_workspace()
    
    # 3. Positive Test: Correct Workspace
    # Need to fetch correct slug first
    print("\nFetching valid workspace slug from database...")
    workspace_slug = await get_workspace_slug_for_email(ADMIN_EMAIL)
    
    if workspace_slug:
        test_login_success(workspace_slug)
        
        # 4. Swagger Fallback Test
        test_swagger_fallback(workspace_slug)
    else:
        print("❌ Critical: Could not find admin user to run positive tests.")

if __name__ == "__main__":
    asyncio.run(main())
