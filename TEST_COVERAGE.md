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
docker-compose exec app /usr/local/bin/python3 app/e2e_test.py
```

---

## Detailed Test Scenarios

### ✅ Core User Journey
1.  **Company Signup**: Creates a new tenant and verifies auto-generated slug (e.g., `test-corp-123456`).
2.  **Admin Login**: Authenticates using the `email|slug` format required for multi-tenant support.
3.  **Create Employee**: Adds a new employee record to the system.
4.  **Create Asset**: Adds a new asset (MacBook Pro) to the inventory.
5.  **Assign Asset**: links the asset to the employee and updates status to `assigned`.
6.  **Invite User**: Creates a user account linked to the employee record.
7.  **Employee Login**: Verifies the invited user can log in successfully.

### ✅ Expense Workflow
8.  **Submit Expense**: Employee submits a new expense claim.
9.  **Approving Expense**: Admin approves the pending expense.
10. **Expense Rejection**: Admin rejects a policy-violating expense (verified status `rejected`).
11. **Expense Reimbursement**: Admin reimburses an approved expense (verified status `reimbursed`).

### ✅ Asset Management & CRUD
12. **Asset Unassignment**: Admin unassigns an asset; verifies status returns to `available` and assignment is cleared.
13. **Update Asset**: Admin updates asset details (uses `PATCH` method).
14. **Update Employee**: Admin updates employee department (uses `PUT` method).
15. **Delete Asset**: Admin verifies hard deletion of an asset.
16. **Delete Employee**: Admin verifies soft deletion (is_active=False) of an employee.

### ✅ Security & Access Control
17. **RBAC Verification**:
    *   **Scenario**: Employee attempts to Create Asset.
    *   **Result**: 403 Forbidden (Blocked).
    *   **Scenario**: Employee attempts to Approve Expense.
    *   **Result**: 403 Forbidden (Blocked).
18. **Tenant Isolation**:
    *   **Scenario**: Admin from "Company B" attempts to access "Company A" employee.
    *   **Result**: 404 Not Found (Data is isolated).
