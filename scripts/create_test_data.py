#!/usr/bin/env python3
"""
Test Data Generation Script

Creates 5 companies with various employees and users to test the ERP system functionality.
Uses Faker to generate realistic test data.

Usage:
    python scripts/create_test_data.py
    or
    python -m scripts.create_test_data
"""

import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from faker import Faker

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.db.models.company import Company, PlanType
from app.db.models.user import User, UserRole
from app.db.models.employee import Employee

# Initialize Faker with seed for reproducible data
fake = Faker()
fake.seed_instance(42)  # Set seed for reproducible data


def generate_phone_number(max_length=20):
    """Generate a phone number that fits within the database field limit"""
    # Generate a simple phone number in format: +1-XXX-XXX-XXXX (15 chars) or similar
    # This ensures it fits within 20 character limit
    formats = [
        f"+1-{fake.random_int(100, 999)}-{fake.random_int(100, 999)}-{fake.random_int(1000, 9999)}",  # +1-XXX-XXX-XXXX (15 chars)
        f"{fake.random_int(100, 999)}-{fake.random_int(100, 999)}-{fake.random_int(1000, 9999)}",     # XXX-XXX-XXXX (12 chars)
        f"({fake.random_int(100, 999)}) {fake.random_int(100, 999)}-{fake.random_int(1000, 9999)}",   # (XXX) XXX-XXXX (14 chars)
    ]
    phone = fake.random_element(elements=formats)
    return phone[:max_length]  # Ensure it doesn't exceed limit


def cleanup_existing_data(db: Session):
    """Delete existing test data (employees, users, companies)"""
    print("🧹 Cleaning up existing test data...")
    print("-" * 60)
    
    try:
        # Delete in correct order due to foreign key constraints
        # 1. Delete employees first (they reference users and companies)
        employee_count = db.query(Employee).count()
        if employee_count > 0:
            db.query(Employee).delete(synchronize_session=False)
            print(f"  ✅ Deleted {employee_count} employees")
        else:
            print("  ℹ️  No employees to delete")
        
        # 2. Delete users (they reference companies)
        user_count = db.query(User).count()
        if user_count > 0:
            db.query(User).delete(synchronize_session=False)
            print(f"  ✅ Deleted {user_count} users")
        else:
            print("  ℹ️  No users to delete")
        
        # 3. Delete companies (no dependencies)
        company_count = db.query(Company).count()
        if company_count > 0:
            db.query(Company).delete(synchronize_session=False)
            print(f"  ✅ Deleted {company_count} companies")
        else:
            print("  ℹ️  No companies to delete")
        
        db.commit()
        
        if employee_count > 0 or user_count > 0 or company_count > 0:
            print(f"\n✅ Cleanup complete. Deleted {company_count} companies, {user_count} users, {employee_count} employees")
        else:
            print("\n✅ No existing data to clean up")
        
    except Exception as e:
        db.rollback()
        print(f"  ⚠️  Error during cleanup: {e}")
        raise


def create_test_data():
    """Create comprehensive test data for the ERP system"""
    db: Session = SessionLocal()
    
    try:
        print("🚀 Starting test data creation...")
        print("=" * 60)
        
        # Clean up existing data first
        cleanup_existing_data(db)
        print()
        
        # Generate Companies Data using Faker
        plan_types = [PlanType.FREE, PlanType.PRO, PlanType.ENTERPRISE, PlanType.FREE, PlanType.ENTERPRISE]
        companies_data = []
        
        for i, plan_type in enumerate(plan_types):
            company_name = fake.company()
            company_domain = company_name.lower().replace(" ", "").replace(",", "").replace(".", "").replace("'", "")[:15]
            admin_name = fake.name()
            admin_email = f"admin{i+1}@{company_domain}.com"
            
            companies_data.append({
                "name": company_name,
                "email": f"contact@{company_domain}.com",
                "plan_type": plan_type,
                "admin": {
                    "name": admin_name,
                    "email": admin_email,
                    "password": "admin123"
                }
            })
        
        created_companies = []
        
        # Scenario 1: Company signup - Creates Admin user (no employee)
        print("\n📦 Creating Companies and Admin Users...")
        print("-" * 60)
        
        for company_data in companies_data:
            # Create company
            company = Company(
                name=company_data["name"],
                email=company_data["email"],
                plan_type=company_data["plan_type"],
                is_active=True
            )
            db.add(company)
            db.flush()
            
            # Create Admin user (no employee record)
            admin_user = User(
                company_id=company.id,
                email=company_data["admin"]["email"],
                hashed_password=get_password_hash(company_data["admin"]["password"]),
                full_name=company_data["admin"]["name"],
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin_user)
            db.flush()
            
            created_companies.append({
                "company": company,
                "admin": admin_user
            })
            
            print(f"✅ Created: {company.name} ({company.plan_type.value}) - Admin: {admin_user.email}")
        
        db.commit()
        print(f"\n✅ Created {len(created_companies)} companies with Admin users")
        
        # Scenario 2: Admin creates employees (without user accounts)
        print("\n👥 Creating Employees (without user accounts)...")
        print("-" * 60)
        
        departments = ["Engineering", "Sales", "Marketing", "HR", "Finance", "Operations", "IT", "Product", "Legal", "Design"]
        job_roles = {
            "Engineering": ["Software Engineer", "Senior Software Engineer", "DevOps Engineer", "QA Engineer"],
            "Sales": ["Sales Representative", "Sales Manager", "Account Executive", "Business Development"],
            "Marketing": ["Marketing Specialist", "Marketing Manager", "Content Writer", "Digital Marketing"],
            "HR": ["HR Coordinator", "HR Manager", "Recruiter", "HR Director"],
            "Finance": ["Financial Analyst", "Accountant", "CFO", "Financial Advisor"],
            "Operations": ["Operations Manager", "Operations Analyst", "Supply Chain Manager"],
            "IT": ["IT Support", "Systems Administrator", "Network Engineer", "Security Analyst"],
            "Product": ["Product Manager", "Product Designer", "Product Owner"],
            "Legal": ["Legal Counsel", "Compliance Officer", "Legal Assistant"],
            "Design": ["UI/UX Designer", "Graphic Designer", "Creative Director"]
        }
        
        # Generate employees per company
        employees_per_company = [2, 3, 3, 1, 2]  # Distribution across 5 companies
        all_employees = []
        employee_counter = 0
        
        for company_idx, num_employees in enumerate(employees_per_company):
            company = created_companies[company_idx]["company"]
            company_prefix = company.name[:2].upper().replace(" ", "").replace(",", "").replace(".", "")
            
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
                    joining_date=fake.date_time_between(start_date="-2y", end_date="now", tzinfo=timezone.utc),
                    employee_id=f"{company_prefix}-{employee_counter:03d}",
                    phone=generate_phone_number(),
                    is_active=fake.boolean(chance_of_getting_true=95)  # 95% active
                )
                db.add(employee)
                all_employees.append(employee)
                print(f"  ✅ {company.name}: {employee.name} ({employee.department}/{employee.role}) - No user account")
        
        db.commit()
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
            hr_email = f"hr{company_idx+1}@{company_domain}"
            hr_role = fake.random_element(elements=["HR Manager", "HR Director", "HR Coordinator", "HR Business Partner"])
            
            # Create HR user with employee record
            hr_user = User(
                company_id=company.id,
                email=hr_email,
                hashed_password=get_password_hash("hr123"),
                full_name=hr_name,
                role=UserRole.HR,
                is_active=True
            )
            db.add(hr_user)
            db.flush()
            
            # Create employee record for HR user
            hr_employee = Employee(
                company_id=company.id,
                user_id=hr_user.id,
                name=hr_name,
                department="Human Resources",
                role=hr_role,
                joining_date=fake.date_time_between(start_date="-6m", end_date="now", tzinfo=timezone.utc),
                is_active=True
            )
            db.add(hr_employee)
            hr_users.append({"user": hr_user, "employee": hr_employee})
            
            print(f"  ✅ {company.name}: HR User {hr_user.email} ({hr_role}) with employee record")
        
        db.commit()
        print(f"\n✅ Created {len(hr_users)} HR users with employee records")
        
        # Scenario 4: Admin invites employees (links to existing employee records)
        print("\n📧 Inviting Employees (linking to existing employee records)...")
        print("-" * 60)
        
        # Select some employees to invite (those without user accounts)
        employees_without_users = [emp for emp in all_employees if emp.user_id is None]
        num_to_invite = min(4, len(employees_without_users))  # Invite up to 4 employees
        employees_to_invite = fake.random_elements(elements=employees_without_users, length=num_to_invite, unique=True)
        
        for employee in employees_to_invite:
            company = next(c["company"] for c in created_companies if c["company"].id == employee.company_id)
            company_domain = company.email.split("@")[1]
            
            # Generate email from employee name
            first_name = employee.name.split()[0].lower()
            last_name = employee.name.split()[-1].lower() if len(employee.name.split()) > 1 else ""
            email = f"{first_name}.{last_name}@{company_domain}" if last_name else f"{first_name}@{company_domain}"
            
            # Create user account
            user = User(
                company_id=company.id,
                email=email,
                hashed_password=get_password_hash("password123"),
                full_name=employee.name,
                role=UserRole.EMPLOYEE,
                is_active=True
            )
            db.add(user)
            db.flush()
            
            # Link employee to user
            employee.user_id = user.id
            
            print(f"  ✅ {company.name}: Invited {employee.name} ({email}) - Linked to employee record")
        
        db.commit()
        print(f"\n✅ Invited {len(employees_to_invite)} employees (linked to existing records)")
        
        # Scenario 5: Create employees with user accounts directly
        print("\n🆕 Creating Employees with User Accounts (direct creation)...")
        print("-" * 60)
        
        # Create 3 more employees with user accounts
        company_indices = [1, 3, 4]  # Different companies
        employee_counter = len(all_employees)
        
        for company_idx in company_indices:
            company = created_companies[company_idx]["company"]
            company_prefix = company.name[:2].upper().replace(" ", "").replace(",", "").replace(".", "")
            company_domain = company.email.split("@")[1]
            
            employee_counter += 1
            name = fake.name()
            first_name = name.split()[0].lower()
            last_name = name.split()[-1].lower() if len(name.split()) > 1 else ""
            email = f"{first_name}.{last_name}@{company_domain}" if last_name else f"{first_name}@{company_domain}"
            department = fake.random_element(elements=departments)
            job_role = fake.random_element(elements=job_roles[department])
            
            # Create user
            user = User(
                company_id=company.id,
                email=email,
                hashed_password=get_password_hash("password123"),
                full_name=name,
                role=UserRole.EMPLOYEE,
                is_active=True
            )
            db.add(user)
            db.flush()
            
            # Create employee record
            employee = Employee(
                company_id=company.id,
                user_id=user.id,
                name=name,
                department=department,
                role=job_role,
                joining_date=fake.date_time_between(start_date="-3m", end_date="now", tzinfo=timezone.utc),
                employee_id=f"{company_prefix}-{employee_counter:03d}",
                phone=generate_phone_number(),
                is_active=True
            )
            db.add(employee)
            all_employees.append(employee)
            
            print(f"  ✅ {company.name}: {email} ({department}/{job_role}) with employee record")
        
        db.commit()
        print(f"\n✅ Created {len(company_indices)} employees with user accounts")
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST DATA SUMMARY")
        print("=" * 60)
        
        total_companies = db.query(Company).count()
        total_users = db.query(User).count()
        total_employees = db.query(Employee).count()
        employees_with_users = db.query(Employee).filter(Employee.user_id.isnot(None)).count()
        employees_without_users = total_employees - employees_with_users
        
        print(f"\n✅ Companies: {total_companies}")
        print(f"  - FREE plan: {db.query(Company).filter(Company.plan_type == PlanType.FREE).count()}")
        print(f"  - PRO plan: {db.query(Company).filter(Company.plan_type == PlanType.PRO).count()}")
        print(f"  - ENTERPRISE plan: {db.query(Company).filter(Company.plan_type == PlanType.ENTERPRISE).count()}")
        
        print(f"\n✅ Users: {total_users}")
        print(f"  - Admin: {db.query(User).filter(User.role == UserRole.ADMIN).count()}")
        print(f"  - HR: {db.query(User).filter(User.role == UserRole.HR).count()}")
        print(f"  - Employee: {db.query(User).filter(User.role == UserRole.EMPLOYEE).count()}")
        
        print(f"\n✅ Employees: {total_employees}")
        print(f"  - With user accounts: {employees_with_users}")
        print(f"  - Without user accounts: {employees_without_users}")
        
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
            
            # Show HR users for this company
            hr_user_list = [hr for hr in hr_users if hr["user"].company_id == company.id]
            for hr in hr_user_list:
                hr_user = hr["user"]
                print(f"  HR: {hr_user.email} / hr123")
            
            # Show some employee users for this company
            company_employees_with_users = [emp for emp in all_employees 
                                           if emp.company_id == company.id and emp.user_id is not None]
            if company_employees_with_users:
                print(f"  Employees with accounts:")
                for emp in company_employees_with_users[:3]:  # Show first 3
                    user = db.query(User).filter(User.id == emp.user_id).first()
                    if user:
                        print(f"    - {user.email} / password123")
        
        print("\n✅ Script completed successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error creating test data: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_test_data()

