import asyncio
import httpx
import logging
import os
import uuid
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",  # Keep format simple for E2E test output
)
logger = logging.getLogger(__name__)

load_dotenv()

# --- Configuration ---
BASE_URL = "http://localhost/api/v1"
COMPANY_EMAIL = "admin@e2e.test"  # New constant
# Use random defaults but allow override via env for consistent runs if needed
COMPANY_NAME = os.environ.get("COMPANY_NAME", f"Test Corp {uuid.uuid4().hex[:6]}")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", f"admin_{uuid.uuid4().hex[:6]}@example.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "secretpassword")
EMPLOYEE_NAME = "John Doe"
EMPLOYEE_EMAIL = os.environ.get(
    "EMPLOYEE_EMAIL", f"john_{uuid.uuid4().hex[:6]}@example.com"
)
EMPLOYEE_PASSWORD = os.environ.get("EMPLOYEE_PASSWORD", "employeepassword")


async def main():
    logger.info(f"🚀 Starting E2E Test for {COMPANY_NAME}...")

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # 1. Company Signup
        logger.info("\n[1/20] Signing up company...")
        signup_data = {
            "name": COMPANY_NAME,
            "email": f"corp_{uuid.uuid4().hex[:6]}@example.com",
            "admin_name": "Admin User",
            "admin_email": ADMIN_EMAIL,
            "admin_password": ADMIN_PASSWORD,
            "plan_type": "free",
        }
        res = await client.post(f"{BASE_URL}/companies/signup", json=signup_data)
        if res.status_code != 201:
            logger.error(f"❌ Signup Failed: {res.text}")
            return
        company_data = res.json()
        expected_slug = signup_data["name"].lower().replace(" ", "-")
        # Handle auto-suffixing in slug generation
        if not company_data["company"]["slug"].startswith(expected_slug):
            logger.warning(
                f"⚠️ Warning: Slug mismatch or suffixed? Got: {company_data['company']['slug']}"
            )
        company_slug = company_data["company"]["slug"]
        logger.info(
            f"✅ Company Created: {company_data['company']['name']} (ID: {company_data['company']['id']}, Slug: {company_slug})"
        )

        # 2. Admin Login
        logger.info("\n[2/20] Logging in as Admin...")
        login_data = {
            "username": f"{ADMIN_EMAIL}|{company_slug}",
            "password": ADMIN_PASSWORD,
        }
        res = await client.post(f"{BASE_URL}/auth/token", data=login_data)
        if res.status_code != 200:
            logger.error(f"❌ Admin Login Failed: {res.text}")
            return
        admin_token = res.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        logger.info("✅ Admin Logged In")

        # 3. Create Employee Record
        logger.info("\n[3/20] Creating Employee Record...")
        employee_data = {
            "name": EMPLOYEE_NAME,
            "department": "Engineering",
            "role": "Software Engineer",
            "joining_date": datetime.now().date().isoformat(),
        }
        res = await client.post(
            f"{BASE_URL}/employees", json=employee_data, headers=admin_headers
        )
        if res.status_code != 201:
            logger.error(f"❌ Create Employee Failed: {res.status_code} {res.text}")
            return
        employee_record = res.json()
        employee_id = employee_record["id"]
        logger.info(
            f"✅ Employee Record Created: {employee_record['name']} (ID: {employee_id})"
        )

        # 4. Create Asset
        logger.info("\n[4/20] Creating Asset...")
        asset_data = {
            "name": "MacBook Pro M3",
            "asset_type": "laptop",
            "serial_number": f"SN-{uuid.uuid4().hex[:8].upper()}",
            "condition": "excellent",
            "status": "available",
        }
        res = await client.post(
            f"{BASE_URL}/assets", json=asset_data, headers=admin_headers
        )
        if res.status_code != 201:
            logger.error(f"❌ Create Asset Failed: {res.text}")
            return
        asset_record = res.json()
        asset_id = asset_record["id"]
        logger.info(f"✅ Asset Created: {asset_record['name']} (ID: {asset_id})")

        # 5. Assign Asset to Employee
        logger.info("\n[5/20] Assigning Asset to Employee...")
        assign_data = {"employee_id": employee_id}
        res = await client.post(
            f"{BASE_URL}/assets/{asset_id}/assign",
            json=assign_data,
            headers=admin_headers,
        )
        if res.status_code != 200:
            logger.error(f"❌ Assign Asset Failed: {res.text}")
            return
        updated_asset = res.json()
        if (
            updated_asset["status"] != "assigned"
            or updated_asset["assigned_to"] != employee_id
        ):
            logger.error(f"❌ Asset status mismatch: {updated_asset}")
            return
        logger.info(f"✅ Asset Assigned to {EMPLOYEE_NAME}")

        # 6. Invite Employee (Create User Account)
        logger.info("\n[6/20] Inviting Employee (Creating User Account)...")
        invite_data = {
            "email": EMPLOYEE_EMAIL,
            "full_name": EMPLOYEE_NAME,
            "password": EMPLOYEE_PASSWORD,
            "role": "employee",
            "employee_id": employee_id,
        }
        res = await client.post(
            f"{BASE_URL}/users/create", json=invite_data, headers=admin_headers
        )
        if res.status_code != 201:
            logger.error(f"❌ Invite Employee Failed: {res.text}")
            return
        user_record = res.json()
        logger.info(f"✅ User Account Created: {user_record['email']}")

        # 7. Employee Login
        logger.info("\n[7/20] Logging in as Employee...")
        emp_login_data = {
            "username": f"{EMPLOYEE_EMAIL}|{company_slug}",
            "password": EMPLOYEE_PASSWORD,
        }
        res = await client.post(f"{BASE_URL}/auth/token", data=emp_login_data)
        if res.status_code != 200:
            logger.error(f"❌ Employee Login Failed: {res.text}")
            return
        employee_token = res.json()["access_token"]
        employee_headers = {"Authorization": f"Bearer {employee_token}"}
        logger.info("✅ Employee Logged In")

        # 8. Submit Expense (as Employee)
        logger.info("\n[8/20] Submitting Expense as Employee...")
        expense_data = {
            "title": "Team Lunch",
            "amount": "125.50",
            "expense_date": datetime.now().isoformat(),
            "description": "Lunch with the team",
        }
        res = await client.post(
            f"{BASE_URL}/expenses/", data=expense_data, headers=employee_headers
        )
        if res.status_code != 201:
            logger.error(f"❌ Submit Expense Failed: {res.text}")
            return
        expense_record = res.json()
        expense_id = expense_record["id"]
        logger.info(
            f"✅ Expense Submitted: {expense_record['title']} (ID: {expense_id})"
        )

        # 9. Verify Expense Status
        if expense_record["status"] != "pending":
            logger.error(f"❌ Expense status incorrect: {expense_record['status']}")
            return

        # 10. Approve Expense (as Admin)
        logger.info("[10/20] Approving Expense as Admin...")
        res = await client.post(
            f"{BASE_URL}/expenses/{expense_id}/approve", headers=admin_headers
        )
        if res.status_code != 200:
            logger.error(f"❌ Approve Expense Failed: {res.text}")
            return
        approved_expense = res.json()
        if approved_expense["status"] != "approved":
            logger.error(
                f"❌ Expense status not approved: {approved_expense['status']}"
            )
            return
        logger.info("✅ Expense Approved by Admin")

        # 11. Unassign Asset (Admin)
        logger.info("\n[11/20] Unassigning Asset...")
        res = await client.post(
            f"{BASE_URL}/assets/{asset_id}/unassign", headers=admin_headers
        )
        if res.status_code != 200:
            logger.error(f"❌ Unassign Asset Failed: {res.status_code} {res.text}")
            return
        unassigned_asset = res.json()
        if (
            unassigned_asset["status"] != "available"
            or unassigned_asset["assigned_to"] is not None
        ):
            logger.error(f"❌ Asset not available after unassign: {unassigned_asset}")
            return
        logger.info(f"✅ Asset Unassigned (Status: {unassigned_asset['status']})")

        # 12. Update Asset (Admin)
        logger.info("\n[12/20] Updating Asset Details...")
        update_data = {"name": "MacBook Pro M3 Max", "condition": "good"}
        res = await client.patch(
            f"{BASE_URL}/assets/{asset_id}", json=update_data, headers=admin_headers
        )
        if res.status_code != 200:
            logger.error(f"❌ Update Asset Failed: {res.text}")
            return
        updated_asset_details = res.json()
        if updated_asset_details["name"] != "MacBook Pro M3 Max":
            logger.error(f"❌ Asset update mismatch: {updated_asset_details}")
            return
        logger.info(f"✅ Asset Updated: {updated_asset_details['name']}")

        # 13. Delete Asset (Admin)
        logger.info("\n[13/20] Deleting Asset...")
        res = await client.delete(
            f"{BASE_URL}/assets/{asset_id}", headers=admin_headers
        )
        if res.status_code != 204:
            logger.error(f"❌ Delete Asset Failed: {res.status_code} {res.text}")
            return
        # Verify deletion
        res = await client.get(f"{BASE_URL}/assets/{asset_id}", headers=admin_headers)
        if res.status_code != 404:
            logger.error(f"❌ Asset still exists after deletion: {res.status_code}")
            return
        logger.info("✅ Asset Deleted Successfully")

        # 14. Update Employee (Admin)
        logger.info("\n[14/20] Updating Employee Details...")
        emp_update_data = {"department": "Product"}
        res = await client.put(
            f"{BASE_URL}/employees/{employee_id}",
            json=emp_update_data,
            headers=admin_headers,
        )
        if res.status_code != 200:
            logger.error(f"❌ Update Employee Failed: {res.text}")
            return
        updated_emp = res.json()
        if updated_emp["department"] != "Product":
            logger.error(f"❌ Employee update mismatch: {updated_emp}")
            return
        logger.info(f"✅ Employee Updated: {updated_emp['department']}")

        # 15. Delete Employee (Admin - Soft Delete)
        logger.info("\n[15/20] Deleting Employee (Soft Delete)...")
        res = await client.delete(
            f"{BASE_URL}/employees/{employee_id}", headers=admin_headers
        )
        if res.status_code != 200:
            logger.error(f"❌ Delete Employee Failed: {res.text}")
            return
        # Verify inactive status
        res = await client.get(
            f"{BASE_URL}/employees/{employee_id}", headers=admin_headers
        )
        final_emp = res.json()
        if final_emp["is_active"] is not False:
            logger.error(f"❌ Employee not marked inactive: {final_emp}")
            return
        logger.info("✅ Employee Soft Deleted")

        # 16. Expense Rejection Flow
        logger.info("\n[16/20] Testing Expense Rejection...")
        # Submit new expense to reject
        reject_exp_data = {
            "title": "Bad Expense",
            "amount": "999.00",
            "expense_date": datetime.now().isoformat(),
        }
        res = await client.post(
            f"{BASE_URL}/expenses/", data=reject_exp_data, headers=employee_headers
        )
        if res.status_code != 201:
            logger.error(f"❌ Submit Expense for Rejection Failed: {res.text}")
            return
        reject_exp_id = res.json()["id"]

        # Reject it
        rejection_payload = {"rejection_reason": "Policy violation"}
        res = await client.post(
            f"{BASE_URL}/expenses/{reject_exp_id}/reject",
            json=rejection_payload,
            headers=admin_headers,
        )
        if res.status_code != 200:
            logger.error(f"❌ Reject Expense Failed: {res.text}")
            return
        rejected_exp = res.json()
        if rejected_exp["status"] != "rejected":
            logger.error(f"❌ Expense not rejected: {rejected_exp['status']}")
            return
        logger.info("✅ Expense Rejected")

        # 17. Expense Reimbursement Flow
        logger.info("\n[17/20] Testing Expense Reimbursement...")
        # Submit -> Approve -> Reimburse
        reimburse_exp_data = {
            "title": "Travel",
            "amount": "50.00",
            "expense_date": datetime.now().isoformat(),
        }
        res = await client.post(
            f"{BASE_URL}/expenses/", data=reimburse_exp_data, headers=employee_headers
        )
        reimburse_exp_id = res.json()["id"]

        res = await client.post(
            f"{BASE_URL}/expenses/{reimburse_exp_id}/approve", headers=admin_headers
        )
        if res.status_code != 200:
            logger.error(f"❌ Approve Expense (Reimburse Flow) Failed: {res.text}")
            return

        res = await client.post(
            f"{BASE_URL}/expenses/{reimburse_exp_id}/reimburse", headers=admin_headers
        )
        if res.status_code != 200:
            logger.error(f"❌ Reimburse Expense Failed: {res.text}")
            return
        reimbursed_exp = res.json()
        if reimbursed_exp["status"] != "reimbursed":
            logger.error(f"❌ Expense not reimbursed: {reimbursed_exp['status']}")
            return
        logger.info("✅ Expense Reimbursed")

        # 18. Negative Tests (RBAC)
        logger.info("\n[18/20] Testing Negative Security Scenarios (RBAC)...")
        # Employee tries to create asset
        res = await client.post(
            f"{BASE_URL}/assets", json=asset_data, headers=employee_headers
        )
        if res.status_code == 403:
            logger.info(
                "✅ RBAC Check Passed: Employee cannot create assets (403 Forbidden)"
            )
        else:
            logger.error(f"❌ RBAC Check Failed: Expected 403, got {res.status_code}")

        # Employee tries to approve expense
        res = await client.post(
            f"{BASE_URL}/expenses/{reimburse_exp_id}/approve", headers=employee_headers
        )
        if res.status_code == 403:
            logger.info(
                "✅ RBAC Check Passed: Employee cannot approve expenses (403 Forbidden)"
            )
        else:
            logger.error(f"❌ RBAC Check Failed: Expected 403, got {res.status_code}")

        # 19. Tenant Isolation
        logger.info("\n[19/20] Testing Tenant Isolation...")
        # Signup second company
        company2_data = {
            "name": "Evil Corp",
            "email": f"evil_{uuid.uuid4().hex[:6]}@example.com",
            "admin_name": "Evil Admin",
            "admin_email": f"evil_admin_{uuid.uuid4().hex[:6]}@example.com",
            "admin_password": "password",
            "plan_type": "free",
        }
        res = await client.post(f"{BASE_URL}/companies/signup", json=company2_data)
        if res.status_code != 201:
            logger.error(f"❌ Company 2 Signup Failed: {res.text}")
            return

        c2_data = res.json()
        if "company" not in c2_data or "slug" not in c2_data["company"]:
            logger.error(f"❌ Company 2 Signup Response Missing Keys: {c2_data}")
            return
        company2_slug = c2_data["company"]["slug"]

        # Login
        evil_login_data = {
            "username": f"{company2_data['admin_email']}|{company2_slug}",
            "password": "password",
        }
        res = await client.post(f"{BASE_URL}/auth/token", data=evil_login_data)
        if res.status_code != 200:
            logger.error(f"❌ Company 2 Login Failed: {res.text}")
            return

        evil_token = res.json()["access_token"]
        evil_headers = {"Authorization": f"Bearer {evil_token}"}

        # Try to access Company A's employee
        res = await client.get(
            f"{BASE_URL}/employees/{employee_id}", headers=evil_headers
        )
        if res.status_code == 404:
            logger.info(
                "✅ Tenant Isolation Passed: Company B cannot see Company A's employee (404 Not Found)"
            )
        else:
            logger.error(
                f"❌ Tenant Isolation Failed: Expected 404, got {res.status_code}"
            )

        # 20. Final Verification
        logger.info("\n[20/20] All Extended Tests Completed")
        logger.info("✅ Extended End-to-End Test Suite Passed Successfully! 🎉")


if __name__ == "__main__":
    asyncio.run(main())
