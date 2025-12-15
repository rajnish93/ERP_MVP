import urllib.request
import urllib.parse
import sys
import asyncio
from pathlib import Path

# Add parent directory to path
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.db.models.company import Company  # noqa: E402
from sqlalchemy import select  # noqa: E402

BASE_URL = "http://localhost/api/v1"


def make_request(url, data=None, headers=None):
    if data:
        data = urllib.parse.urlencode(data).encode("utf-8")

    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")

    if headers:
        for k, v in headers.items():
            req.add_header(k, v)

    try:
        with urllib.request.urlopen(req) as response:
            return response.getcode(), response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")
    except urllib.error.URLError as e:
        print(f"❌ Connection error: {e}")
        return None, None


async def get_test_credentials():
    """Get test workspace slug and matching admin email"""
    async with AsyncSessionLocal() as db:
        # Get a company
        result = await db.execute(select(Company).limit(1))
        company = result.scalars().first()

        if not company:
            return None, None, None

        # Infer admin email from domain (pattern from create_test_data)
        domain = company.email.split("@")[1]
        admin_email = f"admin1@{domain}"

        # Check if this is actually one of the test companies
        # Based on create_test_data pattern: adminX@domain
        # For "Miller, Henderson and Johnson", it's admin2@millerhenderson.com
        # But we use the FIRST company, so we'll use admin1

        return company.slug, admin_email, "admin123"


def test_header_routing(slug: str, email: str, password: str):
    print(f"\n🔍 Testing X-Workspace Header Routing (slug: {slug})...")
    code, body = make_request(
        f"{BASE_URL}/auth/token",
        headers={"X-Workspace": slug},
        data={"username": email, "password": password, "grant_type": "password"},
    )
    if code == 200:
        print("✅ Login with X-Workspace header successful! (200 OK)")
        return True
    else:
        print(f"❌ Failed: Expected 200, got {code}")
        print(
            f"   Response: {body[:200] if body is not None else 'None (connection error)'}"
        )
        return False


def test_swagger_fallback(slug: str, email: str, password: str):
    print("\n🔍 Testing Swagger Fallback (email|slug)...")
    code, body = make_request(
        f"{BASE_URL}/auth/token",
        data={
            "username": f"{email}|{slug}",
            "password": password,
            "grant_type": "password",
        },
    )
    if code == 200:
        print("✅ Swagger fallback login successful! (200 OK)")
        return True
    else:
        print(f"❌ Failed: Expected 200, got {code}")
        print(
            f"   Response: {body[:200] if body is not None else 'None (connection error)'}"
        )
        return False


def test_invalid_workspace():
    print("\n🔍 Testing Invalid Workspace...")
    code, body = make_request(
        f"{BASE_URL}/auth/token",
        headers={"X-Workspace": "nonexistent-workspace"},
        data={
            "username": "test@example.com",
            "password": "test123",
            "grant_type": "password",
        },
    )
    if code == 404:
        print("✅ Correctly rejected invalid workspace (404 NOT FOUND)")
        return True
    else:
        print(f"❌ Failed: Expected 404, got {code}")
        print(
            f"   Response: {body[:200] if body is not None else 'None (connection error)'}"
        )
        return False


def test_missing_workspace():
    print("\n🔍 Testing Missing Workspace...")
    code, body = make_request(
        f"{BASE_URL}/auth/token",
        data={
            "username": "test@example.com",
            "password": "test123",
            "grant_type": "password",
        },
    )
    if code == 422:
        print("✅ Correctly rejected missing workspace (422 UNPROCESSABLE)")
        return True
    else:
        print(f"❌ Failed: Expected 422, got {code}")
        print(
            f"   Response: {body[:200] if body is not None else 'None (connection error)'}"
        )
        return False


async def main():
    print("\n" + "=" * 80)
    print("🧪 SLUG-BASED ROUTING TESTS")
    print("=" * 80)

    # Get test data
    slug, email, password = await get_test_credentials()
    if not slug:
        print("❌ No test data found. Run create_test_data.py first.")
        return

    print("\n📋 Test Configuration:")
    print(f"   Workspace: {slug}")
    print(f"   Email: {email}")

    results = []

    # Run tests
    results.append(("Header Routing", test_header_routing(slug, email, password)))
    results.append(("Swagger Fallback", test_swagger_fallback(slug, email, password)))
    results.append(("Invalid Workspace", test_invalid_workspace()))
    results.append(("Missing Workspace", test_missing_workspace()))

    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\n  Total: {passed}/{total} tests passed")
    print("=" * 80 + "\n")

    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Check output above for details.")


if __name__ == "__main__":
    asyncio.run(main())
