# End-to-End Test Coverage Documentation

## Overview
The `app/e2e_test.py` script provides a comprehensive automated regression test suite for the ERP backend. It covers **20 distinct steps**, verifying core workflows, CRUD operations, and security controls (RBAC & Tenant Isolation).

## Execution Instructions
The test runs inside the Docker container to ensure direct access to the API network.

### 1. Prerequisite
Ensure `httpx` is installed in the container (required only once):
```bash
docker-compose exec app pip install httpx
```

### 2. Running the Test
Execute the script using the system python interpreter:
```bash
uv pip install httpx requests python-dotenv && python3 app/e2e_test.py
```

---

## Detailed Test Scenarios

### ✅ Core User Journey
1.  **Company Signup**: Creates a new tenant and verifies auto-generated slug.
2.  **Admin Login**: Authenticates using the `email|slug` format required for multi-tenant support.
3.  **Create Employee**: Adds a new employee record to the system.
4.  **Create Asset**: Adds a new asset (MacBook Pro) to the inventory.
5.  **Assign Asset**: Links the asset to the employee and updates status to `assigned`.
6.  **Invite Employee**: Creates a user account linked to the employee record.
7.  **Employee Login**: Verifies the invited user can log in successfully.

### ✅ Expense Workflow
8.  **Submit Expense**: Employee submits a new expense claim.
9.  **Verify Status**: Ensures initial status is `pending`.
10. **Approve Expense**: Admin approves the pending expense.
11. **Unassign Asset**: Admin unassigns an asset; verifies status returns to `available`.
12. **Update Asset**: Admin updates asset details (uses `PATCH` method).
13. **Delete Asset**: Admin verifies hard deletion of an asset.
14. **Update Employee**: Admin updates employee department (uses `PUT` method).
15. **Delete Employee**: Admin verifies soft deletion (`is_active=False`) of an employee.

### ✅ Advanced Workflows
16. **Expense Rejection Flow**:
    *   Submit expense -> Admin rejects it.
    *   Verify status `rejected`.
17. **Expense Reimbursement Flow**:
    *   Submit -> Approve -> Reimburse.
    *   Verify status `reimbursed`.

### ✅ Security & Access Control
18. **RBAC Verification**:
    *   **Scenario**: Employee attempts to Create Asset -> **Blocked (403)**.
    *   **Scenario**: Employee attempts to Approve Expense -> **Blocked (403)**.
19. **Tenant Isolation**:
    *   **Scenario**: Admin from "Company B" attempts to access "Company A" employee.
    *   **Result**: **404 Not Found** (Data is isolated).
20. **Final Verification**: Confirms all extended tests passed successfully.
