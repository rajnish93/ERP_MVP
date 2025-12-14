#!/usr/bin/env python3
"""
Test Data Generation Script (Async)

Creates 5 companies with various employees and users to test the ERP system functionality.
Uses Faker to generate realistic test data.

Usage:
    python scripts/create_test_data.py
    or
    python -m scripts.create_test_data
"""

import asyncio
import sys
from datetime import timezone
from pathlib import Path
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from faker import Faker

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.db.models.company import Company, PlanType
from app.db.models.user import User, UserRole
from app.db.models.employee import Employee
from app.db.models.asset import Asset, AssetType, AssetStatus, AssetCondition
from app.db.models.expense import Expense, ExpenseStatus

# Initialize Faker with seed for reproducible data
fake = Faker()
fake.seed_instance(42)  # Set seed for reproducible data


def generate_phone_number(max_length=20):
    """Generate a phone number that fits within the database field limit"""
    # Generate a simple phone number in format: +1-XXX-XXX-XXXX (15 chars) or similar
    # This ensures it fits within 20 character limit
    formats = [
        f"+1-{fake.random_int(100, 999)}-{fake.random_int(100, 999)}-{fake.random_int(1000, 9999)}",  # +1-XXX-XXX-XXXX (15 chars)
        f"{fake.random_int(100, 999)}-{fake.random_int(100, 999)}-{fake.random_int(1000, 9999)}",  # XXX-XXX-XXXX (12 chars)
        f"({fake.random_int(100, 999)}) {fake.random_int(100, 999)}-{fake.random_int(1000, 9999)}",  # (XXX) XXX-XXXX (14 chars)
    ]
    phone = fake.random_element(elements=formats)
    return phone[:max_length]  # Ensure it doesn't exceed limit


async def cleanup_existing_data(db: AsyncSession):
    """Delete existing test data (assets, employees, users, companies)"""
    print("🧹 Cleaning up existing test data...")
    print("-" * 60)

    try:
        # Delete in correct order due to foreign key constraints
        # 0. Delete expenses first (child table)
        result = await db.execute(select(func.count(Expense.id)))
        expense_count = result.scalar() or 0

        if expense_count > 0:
            await db.execute(delete(Expense))
            print(f"  ✅ Deleted {expense_count} expenses")
        else:
            print("  ℹ️  No expenses to delete")

        # 1. Delete assets (they reference employees and companies)
        result = await db.execute(select(func.count(Asset.id)))
        asset_count = result.scalar() or 0

        if asset_count > 0:
            await db.execute(delete(Asset))
            print(f"  ✅ Deleted {asset_count} assets")
        else:
            print("  ℹ️  No assets to delete")

        # 2. Delete employees (they reference users and companies)
        result = await db.execute(select(func.count(Employee.id)))
        employee_count = result.scalar() or 0

        if employee_count > 0:
            await db.execute(delete(Employee))
            print(f"  ✅ Deleted {employee_count} employees")
        else:
            print("  ℹ️  No employees to delete")

        # 3. Delete users (they reference companies)
        result = await db.execute(select(func.count(User.id)))
        user_count = result.scalar() or 0

        if user_count > 0:
            await db.execute(delete(User))
            print(f"  ✅ Deleted {user_count} users")
        else:
            print("  ℹ️  No users to delete")

        # 4. Delete companies (no dependencies)
        result = await db.execute(select(func.count(Company.id)))
        company_count = result.scalar() or 0

        if company_count > 0:
            await db.execute(delete(Company))
            print(f"  ✅ Deleted {company_count} companies")
        else:
            print("  ℹ️  No companies to delete")

        await db.commit()

        if (
            asset_count > 0
            or employee_count > 0
            or user_count > 0
            or company_count > 0
            or expense_count > 0
        ):
            print(
                f"\n✅ Cleanup complete. Deleted {company_count} companies, {user_count} users, {employee_count} employees, {asset_count} assets, {expense_count} expenses"
            )
        else:
            print("\n✅ No existing data to clean up")

    except Exception as e:
        await db.rollback()
        print(f"  ⚠️  Error during cleanup: {e}")
        raise


async def create_test_data():
    """Create comprehensive test data for the ERP system"""
    async with AsyncSessionLocal() as db:
        try:
            print("🚀 Starting test data creation (Async)...")
            print("=" * 60)

            # Clean up existing data first
            await cleanup_existing_data(db)
            print()

            # Generate Companies Data using Faker
            plan_types = [
                PlanType.FREE,
                PlanType.PRO,
                PlanType.ENTERPRISE,
                PlanType.FREE,
                PlanType.ENTERPRISE,
            ]
            companies_data = []

            for i, plan_type in enumerate(plan_types):
                company_name = fake.company()
                company_domain = (
                    company_name.lower()
                    .replace(" ", "")
                    .replace(",", "")
                    .replace(".", "")
                    .replace("'", "")[:15]
                )
                admin_name = fake.name()
                admin_email = f"admin{i + 1}@{company_domain}.com"

                companies_data.append(
                    {
                        "name": company_name,
                        "email": f"contact@{company_domain}.com",
                        "plan_type": plan_type,
                        "admin": {
                            "name": admin_name,
                            "email": admin_email,
                            "password": "admin123",
                        },
                    }
                )

            created_companies = []

            # Scenario 1: Company signup - Creates Admin user (no employee)
            print("\n📦 Creating Companies and Admin Users...")
            print("-" * 60)

            for company_data in companies_data:
                # Create company
                # Generate valid slug: keep only alphanumeric and hyphens
                slug_base = re.sub(r"[^a-z0-9]+", "-", company_data["name"].lower())
                slug = slug_base.strip("-")[
                    :50
                ]  # Remove leading/trailing hyphens, limit length

                company = Company(
                    name=company_data["name"],
                    slug=slug,
                    email=company_data["email"],
                    plan_type=company_data["plan_type"],
                    is_active=True,
                )
                db.add(company)
                await db.flush()  # Flush to get ID

                # Create Admin user (no employee record)
                admin_user = User(
                    company_id=company.id,
                    email=company_data["admin"]["email"],
                    hashed_password=get_password_hash(
                        company_data["admin"]["password"]
                    ),
                    full_name=company_data["admin"]["name"],
                    role=UserRole.ADMIN,
                    is_active=True,
                )
                db.add(admin_user)
                await db.flush()

                created_companies.append({"company": company, "admin": admin_user})

                print(
                    f"✅ Created: {company.name} ({company.plan_type.value}) - Admin: {admin_user.email}"
                )

            await db.commit()
            print(f"\n✅ Created {len(created_companies)} companies with Admin users")

            # Scenario 2: Admin creates employees (without user accounts)
            print("\n👥 Creating Employees (without user accounts)...")
            print("-" * 60)

            departments = [
                "Engineering",
                "Sales",
                "Marketing",
                "HR",
                "Finance",
                "Operations",
                "IT",
                "Product",
                "Legal",
                "Design",
            ]
            job_roles = {
                "Engineering": [
                    "Software Engineer",
                    "Senior Software Engineer",
                    "DevOps Engineer",
                    "QA Engineer",
                ],
                "Sales": [
                    "Sales Representative",
                    "Sales Manager",
                    "Account Executive",
                    "Business Development",
                ],
                "Marketing": [
                    "Marketing Specialist",
                    "Marketing Manager",
                    "Content Writer",
                    "Digital Marketing",
                ],
                "HR": ["HR Coordinator", "HR Manager", "Recruiter", "HR Director"],
                "Finance": [
                    "Financial Analyst",
                    "Accountant",
                    "CFO",
                    "Financial Advisor",
                ],
                "Operations": [
                    "Operations Manager",
                    "Operations Analyst",
                    "Supply Chain Manager",
                ],
                "IT": [
                    "IT Support",
                    "Systems Administrator",
                    "Network Engineer",
                    "Security Analyst",
                ],
                "Product": ["Product Manager", "Product Designer", "Product Owner"],
                "Legal": ["Legal Counsel", "Compliance Officer", "Legal Assistant"],
                "Design": ["UI/UX Designer", "Graphic Designer", "Creative Director"],
            }

            # Generate employees per company
            employees_per_company = [2, 3, 3, 1, 2]  # Distribution across 5 companies
            all_employees = []
            employee_counter = 0

            for company_idx, num_employees in enumerate(employees_per_company):
                company = created_companies[company_idx]["company"]
                company_prefix = (
                    company.name[:2]
                    .upper()
                    .replace(" ", "")
                    .replace(",", "")
                    .replace(".", "")
                )

                for emp_num in range(num_employees):
                    employee_counter += 1
                    department = fake.random_element(elements=departments)
                    job_role = fake.random_element(elements=job_roles[department])

                    employee = Employee(
                        company_id=company.id,
                        user_id=None,  # No user account yet
                        name=fake.name(),
                        department=department,
                        role=job_role,
                        joining_date=fake.date_time_between(
                            start_date="-2y", end_date="now", tzinfo=timezone.utc
                        ),
                        employee_id=f"{company_prefix}-{employee_counter:03d}",
                        phone=generate_phone_number(),
                        is_active=fake.boolean(chance_of_getting_true=95),  # 95% active
                    )
                    db.add(employee)
                    all_employees.append(employee)
                    print(
                        f"  ✅ {company.name}: {employee.name} ({employee.department}/{employee.role}) - No user account"
                    )

            await db.commit()
            # Need to re-fetch employees to ensure they are bound to session if needed later,
            # or just use what we have if we don't access lazy relationships outside.
            # Ideally, simple objects in list are fine.
            print(f"\n✅ Created {len(all_employees)} employees without user accounts")

            # Scenario 3: Admin invites HR users
            print("\n👔 Creating HR Users (invited by Admin)...")
            print("-" * 60)

            # Create HR users for first 3 companies
            hr_users = []
            for company_idx in range(3):
                company = created_companies[company_idx]["company"]
                company_domain = company.email.split("@")[1]
                hr_name = fake.name()
                hr_email = f"hr{company_idx + 1}@{company_domain}"
                hr_role = fake.random_element(
                    elements=[
                        "HR Manager",
                        "HR Director",
                        "HR Coordinator",
                        "HR Business Partner",
                    ]
                )

                # Create HR user with employee record
                hr_user = User(
                    company_id=company.id,
                    email=hr_email,
                    hashed_password=get_password_hash("hr123"),
                    full_name=hr_name,
                    role=UserRole.HR,
                    is_active=True,
                )
                db.add(hr_user)
                await db.flush()

                # Create employee record for HR user
                hr_employee = Employee(
                    company_id=company.id,
                    user_id=hr_user.id,
                    name=hr_name,
                    department="Human Resources",
                    role=hr_role,
                    joining_date=fake.date_time_between(
                        start_date="-6m", end_date="now", tzinfo=timezone.utc
                    ),
                    is_active=True,
                )
                db.add(hr_employee)
                hr_users.append({"user": hr_user, "employee": hr_employee})

                print(
                    f"  ✅ {company.name}: HR User {hr_user.email} ({hr_role}) with employee record"
                )

            await db.commit()
            print(f"\n✅ Created {len(hr_users)} HR users with employee records")

            # Scenario 4: Admin invites employees (links to existing employee records)
            print("\n📧 Inviting Employees (linking to existing employee records)...")
            print("-" * 60)

            # To modify objects, we should make sure they are attached to session
            # Since we committed, previous objects might be detached or expired.
            # Let's re-fetch 'all_employees' to be safe.
            # Or we can just use the ID references if we knew them.
            # But here we are iterating objects.
            # The cleanest way in async session after commit is to re-execute query if we want to modify them.

            # Re-fetch all employees that don't have user_id
            stmt = select(Employee).where(Employee.user_id.is_(None))
            result = await db.execute(stmt)
            employees_without_users = list(result.scalars().all())

            num_to_invite = min(
                4, len(employees_without_users)
            )  # Invite up to 4 employees
            employees_to_invite = fake.random_elements(
                elements=employees_without_users, length=num_to_invite, unique=True
            )

            for employee in employees_to_invite:
                company = next(
                    c["company"]
                    for c in created_companies
                    if c["company"].id == employee.company_id
                )
                company_domain = company.email.split("@")[1]

                # Generate email from employee name
                first_name = employee.name.split()[0].lower()
                last_name = (
                    employee.name.split()[-1].lower()
                    if len(employee.name.split()) > 1
                    else ""
                )
                email = (
                    f"{first_name}.{last_name}@{company_domain}"
                    if last_name
                    else f"{first_name}@{company_domain}"
                )

                # Create user account
                user = User(
                    company_id=company.id,
                    email=email,
                    hashed_password=get_password_hash("password123"),
                    full_name=employee.name,
                    role=UserRole.EMPLOYEE,
                    is_active=True,
                )
                db.add(user)
                await db.flush()

                # Link employee to user
                employee.user_id = user.id
                db.add(employee)  # Ensure it's in session for update

                print(
                    f"  ✅ {company.name}: Invited {employee.name} ({email}) - Linked to employee record"
                )

            await db.commit()
            print(
                f"\n✅ Invited {len(employees_to_invite)} employees (linked to existing records)"
            )

            # Scenario 5: Create employees with user accounts directly
            print("\n🆕 Creating Employees with User Accounts (direct creation)...")
            print("-" * 60)

            # Create 3 more employees with user accounts
            company_indices = [1, 3, 4]  # Different companies
            # Use count approx
            employee_counter += 10  # Buffer

            for company_idx in company_indices:
                company = created_companies[company_idx]["company"]
                company_prefix = (
                    company.name[:2]
                    .upper()
                    .replace(" ", "")
                    .replace(",", "")
                    .replace(".", "")
                )
                company_domain = company.email.split("@")[1]

                employee_counter += 1
                name = fake.name()
                first_name = name.split()[0].lower()
                last_name = name.split()[-1].lower() if len(name.split()) > 1 else ""
                email = (
                    f"{first_name}.{last_name}@{company_domain}"
                    if last_name
                    else f"{first_name}@{company_domain}"
                )
                department = fake.random_element(elements=departments)
                job_role = fake.random_element(elements=job_roles[department])

                # Create user
                user = User(
                    company_id=company.id,
                    email=email,
                    hashed_password=get_password_hash("password123"),
                    full_name=name,
                    role=UserRole.EMPLOYEE,
                    is_active=True,
                )
                db.add(user)
                await db.flush()

                # Create employee record
                employee = Employee(
                    company_id=company.id,
                    user_id=user.id,
                    name=name,
                    department=department,
                    role=job_role,
                    joining_date=fake.date_time_between(
                        start_date="-3m", end_date="now", tzinfo=timezone.utc
                    ),
                    employee_id=f"{company_prefix}-{employee_counter:03d}",
                    phone=generate_phone_number(),
                    is_active=True,
                )
                db.add(employee)
                print(
                    f"  ✅ {company.name}: {email} ({department}/{job_role}) with employee record"
                )

            await db.commit()
            print(f"\n✅ Created {len(company_indices)} employees with user accounts")

            # Scenario 6: Create assets for each company
            print("\n💻 Creating Assets (5 assets per company)...")
            print("-" * 60)

            # Asset templates with realistic names and types
            asset_templates = [
                {"name": "MacBook Pro 16", "type": AssetType.LAPTOP},
                {"name": "Dell XPS 15", "type": AssetType.LAPTOP},
                {"name": 'LG UltraWide 34" Monitor', "type": AssetType.MONITOR},
                {"name": "Logitech MX Master 3", "type": AssetType.MOUSE},
                {"name": "Keychron K2 Keyboard", "type": AssetType.KEYBOARD},
            ]

            for company_idx, company_data in enumerate(created_companies):
                company = company_data["company"]

                for asset_template in asset_templates:
                    # Generate serial number
                    serial_prefix = (
                        company.name[:3]
                        .upper()
                        .replace(" ", "")
                        .replace(",", "")
                        .replace(".", "")
                    )
                    serial_number = f"{serial_prefix}-{fake.bothify(text='####-????', letters='ABCDEFGHJKLMNPRSTUVWXYZ')}"

                    # Random condition
                    condition = fake.random_element(
                        elements=[
                            AssetCondition.EXCELLENT,
                            AssetCondition.GOOD,
                            AssetCondition.GOOD,
                            AssetCondition.FAIR,
                            AssetCondition.FAIR,
                        ]
                    )

                    asset = Asset(
                        company_id=company.id,
                        name=asset_template["name"],
                        asset_type=asset_template["type"],
                        serial_number=serial_number,
                        status=AssetStatus.AVAILABLE,  # Initially available
                        condition=condition,
                        assigned_to=None,
                        issue_date=None,
                    )
                    db.add(asset)
                    # We won't keep asset object for later assignment logic in this flow to mimic realistic querying
                    # But for now let's just commit per batch or all at once? All at once is fine.
                    # But we need to query them later.

                    print(
                        f"  ✅ {company.name}: {asset.name} (S/N: {serial_number}) - {condition.value}"
                    )

            await db.commit()
            print("\n✅ Created assets across companies")

            # Scenario 7: Assign assets to employees
            print("\n📦 Assigning Assets to Employees...")
            print("-" * 60)

            # Get all employees and assets
            result = await db.execute(select(Employee))
            all_employees_list = result.scalars().all()

            result = await db.execute(select(Asset))
            all_assets_list = result.scalars().all()

            assigned_assets = []

            # Assign 2-3 assets per company to random employees
            for company_idx, company_data in enumerate(created_companies):
                company = company_data["company"]
                company_assets = [
                    a for a in all_assets_list if a.company_id == company.id
                ]
                company_employees = [
                    e for e in all_employees_list if e.company_id == company.id
                ]

                if not company_employees:
                    print(f"  ⚠️  {company.name}: No employees to assign assets to")
                    continue

                # Assign 2-3 random assets from this company
                num_to_assign = min(3, len(company_assets))
                assets_to_assign = fake.random_elements(
                    elements=company_assets, length=num_to_assign, unique=True
                )

                for asset in assets_to_assign:
                    # Pick a random employee from this company
                    employee = fake.random_element(elements=company_employees)

                    # Assign asset
                    asset.assigned_to = employee.id
                    asset.status = AssetStatus.ASSIGNED
                    asset.issue_date = fake.date_time_between(
                        start_date="-6m", end_date="now", tzinfo=timezone.utc
                    )

                    db.add(asset)  # Mark for update
                    assigned_assets.append(asset)

                    print(
                        f"  ✅ {company.name}: {asset.name} → {employee.name} (assigned)"
                    )

            await db.commit()
            print(f"\n✅ Assigned {len(assigned_assets)} assets to employees")

            # Scenario 8: Unassign some assets
            print("\n📤 Unassigning Some Assets...")
            print("-" * 60)

            # Unassign 1-2 assets per company
            unassigned_count = 0
            for company_idx, company_data in enumerate(created_companies):
                company = company_data["company"]
                # We need to find assets assigned in the previous step
                # We can reuse 'assigned_assets' list, but filter by company
                company_assigned_assets = [
                    a for a in assigned_assets if a.company_id == company.id
                ]

                if company_assigned_assets:
                    # Unassign 1 random asset
                    num_to_unassign = min(1, len(company_assigned_assets))
                    assets_to_unassign = fake.random_elements(
                        elements=company_assigned_assets,
                        length=num_to_unassign,
                        unique=True,
                    )

                    for asset in assets_to_unassign:
                        # Get employee name for log
                        employee_name = next(
                            (
                                e.name
                                for e in all_employees_list
                                if e.id == asset.assigned_to
                            ),
                            "Unknown",
                        )

                        asset.assigned_to = None
                        asset.status = AssetStatus.AVAILABLE
                        asset.issue_date = None

                        db.add(asset)
                        unassigned_count += 1

                        print(
                            f"  ✅ {company.name}: {asset.name} ← {employee_name} (unassigned)"
                        )

            await db.commit()
            print(f"\n✅ Unassigned {unassigned_count} assets")

            # Scenario 9: Create Expenses
            print("\n💸 Creating Expenses...")
            print("-" * 60)

            expense_categories = [
                "Travel",
                "Office Supplies",
                "Software License",
                "Meals",
                "Training",
                "Hardware",
            ]

            all_expenses = []

            for company_idx, company_data in enumerate(created_companies):
                company = company_data["company"]
                # We need company_employees again. Since we have all_employees_list which are attached to session (re-fetched in Scenario 7)
                # we can use that.
                company_employees = [
                    e for e in all_employees_list if e.company_id == company.id
                ]

                if not company_employees:
                    continue

                # Generate 5-10 expenses per company
                num_expenses = fake.random_int(min=5, max=10)

                for _ in range(num_expenses):
                    employee = fake.random_element(elements=company_employees)
                    category = fake.random_element(elements=expense_categories)
                    status = fake.random_element(elements=list(ExpenseStatus))

                    amount = round(fake.random.uniform(10.0, 500.0), 2)
                    date = fake.date_time_between(
                        start_date="-3m", end_date="now", tzinfo=timezone.utc
                    )

                    # If approved/rejected, set approver (admin)
                    approved_by = None
                    approved_at = None
                    rejection_reason = None

                    if status in [
                        ExpenseStatus.APPROVED,
                        ExpenseStatus.REJECTED,
                        ExpenseStatus.REIMBURSED,
                    ]:
                        admin_user = company_data["admin"]
                        approved_by = admin_user.id
                        approved_at = fake.date_time_between(
                            start_date=date, end_date="now", tzinfo=timezone.utc
                        )

                        if status == ExpenseStatus.REJECTED:
                            rejection_reason = fake.sentence()

                    expense = Expense(
                        company_id=company.id,
                        employee_id=employee.id,
                        title=f"{category} - {fake.catch_phrase()}",
                        amount=amount,
                        description=fake.text(),
                        expense_date=date,
                        status=status,
                        approved_by=approved_by,
                        approved_at=approved_at,
                        rejection_reason=rejection_reason,
                    )
                    db.add(expense)
                    all_expenses.append(expense)
                    print(
                        f"  ✅ {company.name}: {expense.title} (${amount}) - {status.value}"
                    )

            await db.commit()
            print(f"\n✅ Created {len(all_expenses)} expenses")

            # Summary
            print("\n" + "=" * 60)
            print("📊 TEST DATA SUMMARY")
            print("=" * 60)

            result = await db.execute(select(func.count(Company.id)))
            total_companies = result.scalar()

            result = await db.execute(select(func.count(User.id)))
            total_users = result.scalar()

            result = await db.execute(select(func.count(Employee.id)))
            total_employees = result.scalar()

            result = await db.execute(
                select(func.count(Employee.id)).where(Employee.user_id.isnot(None))
            )
            employees_with_users = result.scalar()

            employees_without_users = total_employees - employees_with_users

            print(f"\n✅ Companies: {total_companies}")

            result = await db.execute(
                select(func.count(Company.id)).where(Company.plan_type == PlanType.FREE)
            )
            print(f"  - FREE plan: {result.scalar()}")

            result = await db.execute(
                select(func.count(Company.id)).where(Company.plan_type == PlanType.PRO)
            )
            print(f"  - PRO plan: {result.scalar()}")

            result = await db.execute(
                select(func.count(Company.id)).where(
                    Company.plan_type == PlanType.ENTERPRISE
                )
            )
            print(f"  - ENTERPRISE plan: {result.scalar()}")

            print(f"\n✅ Users: {total_users}")

            result = await db.execute(
                select(func.count(User.id)).where(User.role == UserRole.ADMIN)
            )
            print(f"  - Admin: {result.scalar()}")

            result = await db.execute(
                select(func.count(User.id)).where(User.role == UserRole.HR)
            )
            print(f"  - HR: {result.scalar()}")

            result = await db.execute(
                select(func.count(User.id)).where(User.role == UserRole.EMPLOYEE)
            )
            print(f"  - Employee: {result.scalar()}")

            print(f"\n✅ Employees: {total_employees}")
            print(f"  - With user accounts: {employees_with_users}")
            print(f"  - Without user accounts: {employees_without_users}")

            result = await db.execute(select(func.count(Asset.id)))
            total_assets = result.scalar()

            result = await db.execute(
                select(func.count(Asset.id)).where(Asset.assigned_to.isnot(None))
            )
            assigned_assets_count = result.scalar()

            available_assets_count = total_assets - assigned_assets_count

            print(f"\n✅ Assets: {total_assets}")
            print(f"  - Assigned: {assigned_assets_count}")
            print(f"  - Available: {available_assets_count}")

            result = await db.execute(select(func.count(Expense.id)))
            total_expenses = result.scalar()

            print(f"\n✅ Expenses: {total_expenses}")
            # Breakdown by status
            result = await db.execute(select(Expense.status).distinct())
            expense_statuses = result.scalars().all()
            for status in expense_statuses:
                result = await db.execute(
                    select(func.count(Expense.id)).where(Expense.status == status)
                )
                count = result.scalar()
                print(f"    - {status.value}: {count}")

            # Asset breakdown by type
            result = await db.execute(select(Asset.asset_type).distinct())
            asset_types = result.scalars().all()
            for asset_type in asset_types:
                result = await db.execute(
                    select(func.count(Asset.id)).where(Asset.asset_type == asset_type)
                )
                count = result.scalar()
                print(f"    - {asset_type.value}: {count}")

            print("\n" + "=" * 60)
            print("🎉 Test data creation completed successfully!")
            print("=" * 60)

            print("\n📝 Test Login Credentials:")
            print("-" * 60)
            for idx in range(len(created_companies)):
                company = created_companies[idx]["company"]
                admin = created_companies[idx]["admin"]
                print(f"\n{company.name} ({company.plan_type.value}):")
                print(f"  Admin: {admin.email} / admin123")
                print(f"  Slug: {company.slug}")

                # Show HR users for this company
                hr_user_list = [
                    hr for hr in hr_users if hr["user"].company_id == company.id
                ]
                for hr in hr_user_list:
                    hr_user = hr["user"]
                    print(f"  HR: {hr_user.email} / hr123")

                # Show some employee users for this company
                # Fetch fresh from DB to be sure
                stmt = (
                    select(Employee)
                    .where(
                        Employee.company_id == company.id, Employee.user_id.isnot(None)
                    )
                    .limit(3)
                )
                result = await db.execute(stmt)
                company_employees_with_users = result.scalars().all()

                if company_employees_with_users:
                    print("  Employees with accounts:")
                    for emp in company_employees_with_users:
                        stmt_user = select(User).where(User.id == emp.user_id)
                        result_user = await db.execute(stmt_user)
                        user = result_user.scalars().first()
                        if user:
                            print(f"    - {user.email} / password123")

            print("\n✅ Script completed successfully!")

        except Exception as e:
            await db.rollback()
            print(f"\n❌ Error creating test data: {e}")
            import traceback

            traceback.print_exc()
            raise


if __name__ == "__main__":
    asyncio.run(create_test_data())
