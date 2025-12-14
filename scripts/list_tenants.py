import asyncio
import sys
from pathlib import Path
from sqlalchemy import select

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.db.models.company import Company


async def list_workspace():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Company))
        companies = result.scalars().all()

        print("\n" + "=" * 80)
        print(f"{'COMPANY NAME':<30} | {'SLUG':<20} | {'ADMIN EMAIL'}")
        print("=" * 80)

        for c in companies:
            # Infer admin email pattern - safely extract domain
            if "@" in c.email:
                domain = c.email.rsplit("@", 1)[1]  # Use rsplit for safety
            else:
                domain = "(invalid-email)"  # Safe fallback for malformed emails

            print(f"{c.name:<30} | {c.slug:<20} | admin@{domain}")

        print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(list_workspace())
