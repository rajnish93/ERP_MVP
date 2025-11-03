# Test Data Generation Script

This script generates comprehensive test data for the ERP system using Faker to create realistic test scenarios.

## Features

The script creates:

1. **5 Companies** with different plan types (FREE, PRO, ENTERPRISE)
2. **Admin Users** - One per company (no employee records)
3. **HR Users** - For first 3 companies (with employee records)
4. **Employees** - Distributed across companies (some with user accounts, some without)
5. **Employee Users** - Employees who have been invited to the portal

## Usage

### Prerequisites

Make sure you have:
- Database running and accessible
- Dependencies installed: `pip install -r requirements.txt`
- Database migrations applied: `alembic upgrade head`

### Run the Script

```bash
# From project root
python scripts/create_test_data.py

# Or using Python module syntax
python -m scripts.create_test_data
```

## Test Scenarios Covered

### Scenario 1: Company Signup
- Creates company and Admin user (no employee record)
- Tests: Admin can operate without employee record

### Scenario 2: Admin Creates Employees
- Creates employee records without user accounts
- Tests: Employees can exist without login credentials

### Scenario 3: Admin Invites HR
- Creates HR users with employee records
- Tests: HR role assignment and employee linkage

### Scenario 4: Admin Invites Employees
- Links existing employees to new user accounts
- Tests: Employee invitation flow

### Scenario 5: Direct User + Employee Creation
- Creates users with employee records simultaneously
- Tests: Direct onboarding flow

## Generated Data

- **Companies**: 5 (mix of FREE, PRO, ENTERPRISE plans)
- **Users**: ~15+ (5 Admins, 3 HR, ~7+ Employees)
- **Employees**: ~14+ (mix of with/without user accounts)
- **Departments**: Engineering, Sales, Marketing, HR, Finance, Operations, IT, Product, Legal, Design

## Default Passwords

- **Admin users**: `admin123`
- **HR users**: `hr123`
- **Employee users**: `password123`

## Notes

- Uses Faker with seed=42 for reproducible data
- All data is realistic and randomized using Faker
- Email addresses are generated from company domains
- Employee IDs follow pattern: `{COMPANY_PREFIX}-{NUMBER}`
- Phone numbers are fake but realistic format

## Clean Up

To remove test data, you can:
1. Drop and recreate the database
2. Manually delete via admin interface
3. Use database cleanup scripts (if available)
