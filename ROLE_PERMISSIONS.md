# Role-Based Permissions & Capabilities

This document outlines what each role can do in the ERP system.

## Roles Overview

The system has three roles with hierarchical permissions:

1. **Admin** - Full system access
2. **HR** - Human resources and operational access
3. **Employee** - Limited access to own data

---

## Admin Role

### Full System Access
Admins have complete control over the system and can perform all operations.

### User Management
- ✅ **Create users** - Invite employees to the portal (`POST /api/v1/users/create`)
- ✅ **View all users** - See all users in the company (`GET /api/v1/users/`)
- ✅ **Deactivate users** - Deactivate user accounts (`PUT /api/v1/users/{user_id}/deactivate`)
- ✅ **Cannot deactivate self** - Protection against self-deactivation

### Employee Management
- ✅ **Create employees** - Add new employee records (`POST /api/v1/employees`)
- ✅ **View all employees** - See all employees in the company (`GET /api/v1/employees`)
- ✅ **Update employees** - Edit employee details (`PUT /api/v1/employees/{employee_id}`)
- ✅ **Delete employees** - Soft delete employees (`DELETE /api/v1/employees/{employee_id}`)
- ✅ **Filter employees** - Use all filter options (department, role, status, search)

### Expense Management
- ✅ **View all expenses** - See all expenses across the company (`GET /api/v1/expenses`)
- ✅ **Submit expenses** - Can submit expenses for any employee (`POST /api/v1/expenses`)
- ✅ **Approve expenses** - Approve pending expenses (`POST /api/v1/expenses/{expense_id}/approve`)
- ✅ **Reject expenses** - Reject expenses with reason (`POST /api/v1/expenses/{expense_id}/reject`)
- ✅ **Reimburse expenses** - Mark expenses as reimbursed (`POST /api/v1/expenses/{expense_id}/reimburse`)
- ✅ **Update expenses** - Update any expense (`PATCH /api/v1/expenses/{expense_id}`)
- ✅ **Delete expenses** - Delete any expense (`DELETE /api/v1/expenses/{expense_id}`)
- ✅ **Filter expenses** - Use all filter options (status, employee, date range, amount, search)

### Asset Management
- ✅ **Create assets** - Add new assets/devices (`POST /api/v1/assets`)
- ✅ **View all assets** - See all assets in the company (`GET /api/v1/assets`)
- ✅ **Update assets** - Edit asset details (`PATCH /api/v1/assets/{asset_id}`)
- ✅ **Assign assets** - Assign assets to employees (`POST /api/v1/assets/{asset_id}/assign`)
- ✅ **Unassign assets** - Unassign assets from employees (`POST /api/v1/assets/{asset_id}/unassign`)
- ✅ **Delete assets** - Delete unassigned assets (`DELETE /api/v1/assets/{asset_id}`)
- ✅ **Filter assets** - Use all filter options (status, type, assignment, search)

### Company Management
- ✅ **View company info** - Access company information
- ✅ **Company signup** - Create new companies (via signup endpoint)

### Authentication
- ✅ **Login** - Access the system (`POST /api/v1/auth/token`)
- ✅ **Password reset** - Reset own password (`POST /api/v1/auth/reset-password`)
- ✅ **View own profile** - See own user information (`GET /api/v1/users/me`)

---

## HR Role

### Human Resources & Operational Access
HR has access to most operational features but cannot manage users.

### User Management
- ❌ **Cannot create users** - Only Admin can create users
- ✅ **View all users** - See all users in the company (`GET /api/v1/users/`)
- ❌ **Cannot deactivate users** - Only Admin can deactivate users

### Employee Management
- ✅ **Create employees** - Add new employee records (`POST /api/v1/employees`)
- ✅ **View all employees** - See all employees in the company (`GET /api/v1/employees`)
- ✅ **Update employees** - Edit employee details (`PUT /api/v1/employees/{employee_id}`)
- ❌ **Cannot delete employees** - Only Admin can delete employees
- ✅ **Filter employees** - Use all filter options (department, role, status, search)

### Expense Management
- ✅ **View all expenses** - See all expenses across the company (`GET /api/v1/expenses`)
- ✅ **Submit expenses** - Can submit expenses for any employee (`POST /api/v1/expenses`)
- ✅ **Approve expenses** - Approve pending expenses (`POST /api/v1/expenses/{expense_id}/approve`)
- ✅ **Reject expenses** - Reject expenses with reason (`POST /api/v1/expenses/{expense_id}/reject`)
- ✅ **Reimburse expenses** - Mark expenses as reimbursed (`POST /api/v1/expenses/{expense_id}/reimburse`)
- ✅ **Update expenses** - Update any expense (`PATCH /api/v1/expenses/{expense_id}`)
- ✅ **Delete expenses** - Delete any expense (`DELETE /api/v1/expenses/{expense_id}`)
- ✅ **Filter expenses** - Use all filter options (status, employee, date range, amount, search)

### Asset Management
- ✅ **Create assets** - Add new assets/devices (`POST /api/v1/assets`)
- ✅ **View all assets** - See all assets in the company (`GET /api/v1/assets`)
- ✅ **Update assets** - Edit asset details (`PATCH /api/v1/assets/{asset_id}`)
- ✅ **Assign assets** - Assign assets to employees (`POST /api/v1/assets/{asset_id}/assign`)
- ✅ **Unassign assets** - Unassign assets from employees (`POST /api/v1/assets/{asset_id}/unassign`)
- ❌ **Cannot delete assets** - Only Admin can delete assets
- ✅ **Filter assets** - Use all filter options (status, type, assignment, search)

### Authentication
- ✅ **Login** - Access the system (`POST /api/v1/auth/token`)
- ✅ **Password reset** - Reset own password (`POST /api/v1/auth/reset-password`)
- ✅ **View own profile** - See own user information (`GET /api/v1/users/me`)

---

## Employee Role

### Limited Access to Own Data
Employees have restricted access and can only manage their own data.

### User Management
- ❌ **Cannot create users** - Only Admin can create users
- ✅ **View all users** - See all users in the company (`GET /api/v1/users/`)
- ❌ **Cannot deactivate users** - Only Admin can deactivate users

### Employee Management
- ❌ **Cannot create employees** - Only Admin/HR can create employees
- ✅ **View all employees** - See all employees in the company (`GET /api/v1/employees`)
- ❌ **Cannot update employees** - Only Admin/HR can update employees
- ❌ **Cannot delete employees** - Only Admin can delete employees
- ✅ **Filter employees** - Can use filter options (department, role, status, search)

### Expense Management
- ✅ **View own expenses only** - Can only see their own expenses (`GET /api/v1/expenses`)
- ✅ **Submit expenses** - Submit expenses for themselves (`POST /api/v1/expenses`)
- ❌ **Cannot approve expenses** - Only Admin/HR can approve
- ❌ **Cannot reject expenses** - Only Admin/HR can reject
- ✅ **Update own pending expenses** - Can only update their own pending expenses (`PATCH /api/v1/expenses/{expense_id}`)
- ✅ **Delete own pending expenses** - Can only delete their own pending expenses (`DELETE /api/v1/expenses/{expense_id}`)
- ⚠️ **Limited filtering** - Can filter but only sees own expenses

**Expense Restrictions:**
- Can only edit/delete expenses with status `pending`
- Cannot modify approved, rejected, or reimbursed expenses
- Cannot submit expenses for other employees
- ⚠️ **Requires user account** - Must have a user account (be invited by Admin) to submit expenses
- ⚠️ **Requires employee record** - Employee record must be linked to user account (`user_id` must be set)

**Note:** If an employee doesn't have a user account yet, HR/Admin can submit expenses on their behalf by specifying the `employee_id` in the expense creation request.

### Asset Management
- ❌ **Cannot create assets** - Only Admin/HR can create assets
- ✅ **View assigned assets only** - Can only see assets assigned to them (`GET /api/v1/assets`)
- ❌ **Cannot update assets** - Only Admin/HR can update assets
- ❌ **Cannot assign assets** - Only Admin/HR can assign assets
- ❌ **Cannot unassign assets** - Only Admin/HR can unassign assets
- ❌ **Cannot delete assets** - Only Admin can delete assets
- ⚠️ **No filtering** - Can only see assigned assets

### Authentication
- ✅ **Login** - Access the system (`POST /api/v1/auth/token`)
- ✅ **Password reset** - Reset own password (`POST /api/v1/auth/reset-password`)
- ✅ **View own profile** - See own user information (`GET /api/v1/users/me`)

---

## Permission Matrix

| Feature | Admin | HR | Employee |
|---------|:----:|:--:|:--------:|

| **User Management** | | | |
| Create Users | ✅ | ❌ | ❌ |
| View All Users | ✅ | ✅ | ✅ |
| Deactivate Users | ✅ | ❌ | ❌ |
| **Employee Management** | | | |
| Create Employees | ✅ | ✅ | ❌ |
| View All Employees | ✅ | ✅ | ✅ |
| Update Employees | ✅ | ✅ | ❌ |
| Delete Employees | ✅ | ❌ | ❌ |
| **Expense Management** | | | |
| View All Expenses | ✅ | ✅ | ❌ (Own only) |
| Submit Expenses | ✅ (Any) | ✅ (Any) | ✅ (Own only) |
| Approve Expenses | ✅ | ✅ | ❌ |
| Reject Expenses | ✅ | ✅ | ❌ |
| Reimburse Expenses | ✅ | ✅ | ❌ |

| Update Expenses | ✅ (Any) | ✅ (Any) | ✅ (Own pending only) |
| Delete Expenses | ✅ (Any) | ✅ (Any) | ✅ (Own pending only) |
| **Asset Management** | | | |
| Create Assets | ✅ | ✅ | ❌ |
| View All Assets | ✅ | ✅ | ❌ (Assigned only) |
| Update Assets | ✅ | ✅ | ❌ |
| Assign Assets | ✅ | ✅ | ❌ |
| Unassign Assets | ✅ | ✅ | ❌ |
| Delete Assets | ✅ | ❌ | ❌ |

---

## Key Differences Summary

### Admin vs HR
- **Admin can**: Create users, deactivate users, delete employees, delete assets
- **HR cannot**: Create users, deactivate users, delete employees, delete assets

### HR vs Employee
- **HR can**: Create/update employees, approve/reject expenses, manage assets, see all expenses
- **Employee cannot**: Create/update employees, approve/reject expenses, manage assets, see other employees' expenses

### Common to All Roles
- ✅ View all users in company
- ✅ View all employees in company
- ✅ Login and access system
- ✅ Reset own password
- ✅ View own profile

---

## Security Notes

1. **Tenant Isolation**: All roles can only access data from their own company
2. **Self-Protection**: Admins cannot deactivate themselves
3. **Data Scoping**: Employees can only see their own expenses and assigned assets
4. **Status Restrictions**: Employees can only modify expenses with `pending` status
5. **Role Assignment**: Admin role can only be assigned during company signup

---

## Role Assignment Rules

- **Admin**: Assigned automatically to the first user during company signup
- **HR**: Can be assigned by Admin when creating users
- **Employee**: Default role, can be assigned by Admin when creating users
- **Role Changes**: Currently, roles cannot be changed after user creation (future enhancement)

---

## Employee Expense Submission Workflow

### Current System Requirements

**To submit expenses, an employee MUST have:**
1. ✅ A user account (to authenticate)
2. ✅ An employee record linked to their user account (`user_id` must be set)

### Current Workflow

```text
Step 1: Admin/HR creates Employee Record
  → Employee exists in system (no user account yet)
  → Employee cannot login or submit expenses

Step 2: Admin invites Employee (creates User Account)
  → User account created
  → Employee record linked to user account (user_id set)
  → Employee can now login

Step 3: Employee logs in and submits expenses
  → Employee authenticates with email/password
  → Employee can submit expenses for reimbursement
```

### Important Notes

⚠️ **Employees without user accounts CANNOT submit expenses** because:
- Expense submission requires authentication (`current_user` dependency)
- The system needs to identify which employee is submitting (via `user_id` link)
- Without authentication, there's no way to verify identity or track submissions

### Current Capabilities

**HR/Admin can submit expenses on behalf of employees:**
- HR/Admin can submit expenses for any employee in their company
- This allows expenses to be submitted for employees who don't have accounts yet
- HR/Admin can use the `employee_id` field in the expense creation request

**Example:**
```json
POST /api/v1/expenses
{
  "employee_id": "uuid-of-employee-without-account",
  "title": "Business travel",
  "amount": "150.00",
  "expense_date": "2024-01-15"
}
```

### Recommended Workflow

**For employees who need to submit expenses:**

1. **Create Employee Record First** (Admin/HR)
   - Add employee to system with basic info
   - Employee record exists but no login access

2. **Invite Employee to Portal** (Admin)
   - Create user account via `/api/v1/users/create`
   - Link to existing employee record using `employee_id`
   - Employee receives credentials

3. **Employee Submits Expenses** (Employee)
   - Employee logs in with credentials
   - Employee can submit their own expenses
   - Expenses automatically linked to their employee record

**Alternative: HR/Admin submits on behalf:**
- If employee doesn't have account yet, HR/Admin can submit expenses for them
- HR/Admin must specify `employee_id` in the request
- Employee can later get account and see their expenses

### Future Enhancement Suggestions

1. **Email-based expense submission** (for employees without accounts)
   - Allow employees to submit via email
   - HR/Admin processes and creates expense records

2. **Public expense submission form**
   - Unauthenticated form with employee ID verification
   - Requires additional security measures

3. **Bulk expense import**
   - HR/Admin can import expenses from spreadsheet
   - Map to employees by employee_id

4. **Temporary access tokens**
   - Generate one-time tokens for employees to submit expenses
   - Tokens expire after use or time limit

---

## API Endpoint Access Summary

### Public Endpoints (No Authentication)
- `POST /api/v1/companies/signup` - Company registration
- `POST /api/v1/auth/forgot-password` - Request password reset
- `POST /api/v1/auth/reset-password` - Reset password

### Authenticated Endpoints (All Roles)
- `POST /api/v1/auth/token` - Login
- `GET /api/v1/users/me` - Current user info
- `GET /api/v1/users/` - List users (tenant-scoped)
- `GET /api/v1/employees` - List employees (tenant-scoped)

### Admin-Only Endpoints
- `POST /api/v1/users/create` - Create user
- `PUT /api/v1/users/{user_id}/deactivate` - Deactivate user
- `DELETE /api/v1/employees/{employee_id}` - Delete employee
- `DELETE /api/v1/assets/{asset_id}` - Delete asset

### Admin & HR Only Endpoints
- `POST /api/v1/employees` - Create employee
- `PUT /api/v1/employees/{employee_id}` - Update employee
- `POST /api/v1/assets` - Create asset
- `PATCH /api/v1/assets/{asset_id}` - Update asset
- `POST /api/v1/assets/{asset_id}/assign` - Assign asset
- `POST /api/v1/assets/{asset_id}/unassign` - Unassign asset
- `POST /api/v1/expenses/{expense_id}/approve` - Approve expense
- `POST /api/v1/expenses/{expense_id}/reject` - Reject expense
- `POST /api/v1/expenses/{expense_id}/reimburse` - Reimburse expense


### Employee Restricted Endpoints
- `GET /api/v1/expenses` - Only returns own expenses
- `POST /api/v1/expenses` - Can only submit for themselves
- `PATCH /api/v1/expenses/{expense_id}` - Can only update own pending expenses
- `DELETE /api/v1/expenses/{expense_id}` - Can only delete own pending expenses
- `GET /api/v1/assets` - Only returns assigned assets

