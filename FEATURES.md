# FastAPI ERP MVP - Features Documentation

## Overview

A production-ready multi-tenant Enterprise Resource Planning (ERP) system built with FastAPI, SQLAlchemy 2.0, and PostgreSQL. The system provides comprehensive employee management, asset tracking, expense reimbursement, and user management capabilities with role-based access control.

## Architecture

### Technology Stack

- **Framework**: FastAPI 0.120.4
- **Database**: PostgreSQL with SQLAlchemy 2.0
- **Authentication**: JWT (JSON Web Tokens) with OAuth2 Password Flow
- **Password Hashing**: bcrypt (passlib)
- **Migrations**: Alembic
- **API Documentation**: OpenAPI/Swagger (automatically generated)

### Project Structure

```
app/
├── main.py                 # FastAPI application entry point
├── api/v1/endpoints/       # API route handlers
│   ├── auth.py            # Authentication endpoints
│   ├── companies.py       # Company signup
│   ├── users.py           # User management
│   ├── employees.py       # Employee CRUD operations
│   ├── expenses.py        # Expense reimbursement workflow
│   ├── assets.py          # Asset/device management
│   └── password_reset.py  # Password reset flow
├── core/                   # Core application logic
│   ├── config.py          # Settings and configuration
│   ├── database.py       # Database connection and session management
│   ├── security.py        # Password hashing, JWT tokens
│   ├── dependencies.py    # FastAPI dependencies (auth, RBAC)
│   └── types.py           # Custom SQLAlchemy types
├── db/models/             # SQLAlchemy database models
│   ├── company.py
│   ├── user.py
│   ├── employee.py
│   ├── expense.py
│   └── asset.py
└── schemas/               # Pydantic schemas for request/response
    ├── company.py
    ├── user.py
    ├── employee.py
    ├── expense.py
    └── asset.py
```

## Core Features

### 1. Multi-Tenant Architecture

- **Company-based isolation**: All data is scoped to company (tenant)
- **Automatic tenant filtering**: All queries automatically filter by `company_id`
- **Tenant isolation dependency**: `get_current_company_id()` ensures data isolation
- **Company signup**: Self-service company registration with admin user creation

### 2. Authentication & Authorization

#### Authentication
- **OAuth2 Password Flow**: Standard OAuth2 implementation
- **JWT Tokens**: Secure token-based authentication
- **Token expiration**: Configurable token expiry (default: 30 minutes)
- **Token storage**: Tokens include `company_id` for tenant isolation
- **Password security**: bcrypt hashing with 72-byte limit handling

#### Authorization - Role-Based Access Control (RBAC)
- **Three roles**: Admin, HR, Employee
- **Role-based dependencies**: `require_role()` function for endpoint protection
- **Permission checks**: Automatic role validation on protected endpoints
- **Role hierarchy**: Admin > HR > Employee

### 3. User Management

#### Features
- **User creation**: Admin can invite users (create user accounts)
- **User listing**: View all users in company (tenant isolation)
- **User deactivation**: Soft delete (set `is_active=False`)
- **Current user info**: `/users/me` endpoint for authenticated user
- **User-Employee linking**: Users can be linked to employee records

#### Endpoints
- `POST /api/v1/users/create` - Create new user (Admin only)
- `GET /api/v1/users/` - List all company users
- `GET /api/v1/users/me` - Get current user info
- `PUT /api/v1/users/{user_id}/deactivate` - Deactivate user (Admin only)

### 4. Employee Management

#### Features
- **Full CRUD operations**: Create, Read, Update, Delete employees
- **Optional user linking**: Employees can exist without user accounts
- **Employee ID**: Optional human-readable employee code
- **Department tracking**: Organize employees by department
- **Job role tracking**: Track employee job titles/roles
- **Joining date**: Track employee start dates
- **Soft delete**: Deactivation instead of hard delete
- **Search & filter**: Filter by department, role, status, search by name/ID

#### Endpoints
- `POST /api/v1/employees` - Create employee (Admin/HR only)
- `GET /api/v1/employees` - List employees with filters
- `GET /api/v1/employees/{employee_id}` - Get employee details
- `PUT /api/v1/employees/{employee_id}` - Update employee (Admin/HR only)
- `DELETE /api/v1/employees/{employee_id}` - Delete employee (Admin only)

#### Query Parameters
- `department` - Filter by department name
- `role` - Filter by job role
- `is_active` - Filter by active status
- `search` - Search by name or employee_id

### 5. Expense Reimbursement System

#### Workflow
1. **Submit**: Employee submits expense with status `pending`
2. **Review**: HR/Admin reviews expense
3. **Approve/Reject**: HR/Admin approves or rejects with reason
4. **Reimburse**: (Future) Mark as reimbursed after payment

#### Status Flow
```
pending → approved/rejected → reimbursed
```

#### Features
- **Expense submission**: Employees submit expenses for reimbursement
- **Approval workflow**: HR/Admin approve or reject expenses
- **Rejection reasons**: Required reason when rejecting
- **Amount tracking**: Decimal precision for financial amounts
- **Receipt URLs**: Optional receipt file links
- **Expense date**: Track when expense was incurred
- **Employee filtering**: HR/Admin can filter by employee
- **Date range filtering**: Filter by expense date range
- **Amount filtering**: Filter by min/max amount
- **Search**: Search by title or description
- **Own expense access**: Employees can only see their own expenses

#### Endpoints
- `POST /api/v1/expenses` - Submit expense (All authenticated users)
- `GET /api/v1/expenses` - List expenses with filters
- `GET /api/v1/expenses/{expense_id}` - Get expense details
- `PATCH /api/v1/expenses/{expense_id}` - Update expense
- `POST /api/v1/expenses/{expense_id}/approve` - Approve expense (Admin/HR only)
- `POST /api/v1/expenses/{expense_id}/reject` - Reject expense (Admin/HR only)
- `DELETE /api/v1/expenses/{expense_id}` - Delete expense

#### Query Parameters
- `status` - Filter by status (pending, approved, rejected, reimbursed)
- `employee_id` - Filter by employee (HR/Admin only)
- `start_date` - Filter by expense date (start)
- `end_date` - Filter by expense date (end)
- `min_amount` - Minimum amount filter
- `max_amount` - Maximum amount filter
- `search` - Search by title or description

### 6. Asset/Device Management

#### Features
- **Asset tracking**: Track company assets/devices
- **Asset types**: Laptop, Monitor, Mouse, Keyboard, Phone, Tablet, Other
- **Serial number tracking**: Unique serial numbers per company
- **Condition tracking**: Excellent, Good, Fair, Poor
- **Status management**: Available, Assigned, Maintenance, Retired
- **Employee assignment**: Assign assets to employees
- **Assignment history**: Track issue dates
- **Unassignment**: Return assets to available pool
- **Search & filter**: Filter by status, type, assignment status

#### Endpoints
- `POST /api/v1/assets` - Create asset (Admin/HR only)
- `GET /api/v1/assets` - List assets with filters
- `GET /api/v1/assets/{asset_id}` - Get asset details
- `PATCH /api/v1/assets/{asset_id}` - Update asset (Admin/HR only)
- `POST /api/v1/assets/{asset_id}/assign` - Assign asset to employee (Admin/HR only)
- `POST /api/v1/assets/{asset_id}/unassign` - Unassign asset (Admin/HR only)
- `DELETE /api/v1/assets/{asset_id}` - Delete asset (Admin only, unassigned only)

#### Query Parameters
- `status` - Filter by status
- `asset_type` - Filter by asset type
- `assigned` - Filter by assignment status (true/false)
- `search` - Search by name or serial number

### 7. Company Management

#### Features
- **Company signup**: Self-service company registration
- **Plan types**: Free, Pro, Enterprise
- **Admin user creation**: Automatic admin user creation on signup
- **Company activation**: Active/inactive status

#### Endpoints
- `POST /api/v1/companies/signup` - Register new company and admin user

### 8. Password Reset

#### Features
- **Forgot password**: Request password reset token
- **Token generation**: Secure random tokens (32 bytes, URL-safe)
- **Token expiration**: 15-minute expiry
- **One-time use**: Tokens invalidated after use
- **Company verification**: Token includes company_id for security

#### Endpoints
- `POST /api/v1/auth/forgot-password` - Request password reset
- `POST /api/v1/auth/reset-password` - Reset password with token

## Database Models

### Company Model
- **Fields**: id, name, email, plan_type, is_active, created_at, updated_at
- **Relationships**: Has many users, employees, assets, expenses
- **Constraints**: Unique email, plan_type enum

### User Model
- **Fields**: id, company_id, email, hashed_password, full_name, role, is_active, created_at, updated_at
- **Relationships**: Belongs to company, has one employee
- **Constraints**: Unique email globally, unique (company_id, email)
- **Indexes**: email, company_id, role

### Employee Model
- **Fields**: id, company_id, user_id (optional), name, department, role, joining_date, employee_id, phone, is_active, created_at, updated_at
- **Relationships**: Belongs to company, has one user (optional), has many assets, expenses
- **Constraints**: Unique user_id, unique employee_id
- **Indexes**: company_id, user_id, department, role

### Expense Model
- **Fields**: id, company_id, employee_id, title, amount, description, expense_date, status, receipt_url, approved_by, approved_at, rejection_reason, created_at, updated_at
- **Relationships**: Belongs to company, employee, approver (user)
- **Constraints**: Amount >= 0, status enum
- **Indexes**: company_id, employee_id, expense_date, status

### Asset Model
- **Fields**: id, company_id, name, asset_type, serial_number, status, condition, assigned_to, issue_date, created_at, updated_at
- **Relationships**: Belongs to company, assigned to employee (optional)
- **Constraints**: Unique (company_id, serial_number), status enum, condition enum
- **Indexes**: company_id, serial_number, status, assigned_to

## Security Features

### Authentication Security
- **JWT tokens**: Secure token-based authentication
- **Token expiration**: Configurable expiry times
- **Token validation**: Automatic token verification on protected routes
- **Company verification**: Token includes company_id for tenant isolation
- **Password hashing**: bcrypt with proper salt rounds
- **Password length**: Enforced minimum 8 characters, max 72 bytes (bcrypt limit)

### Authorization Security
- **Role-based access control**: Three-tier role system
- **Endpoint protection**: Automatic role checking via dependencies
- **Tenant isolation**: All queries filtered by company_id
- **User status checking**: Inactive users cannot access system
- **Self-protection**: Users cannot deactivate themselves

### Data Security
- **SQL injection protection**: SQLAlchemy ORM prevents SQL injection
- **Input validation**: Pydantic schemas validate all inputs
- **Error handling**: Custom error handlers prevent information leakage
- **CORS configuration**: Configurable CORS origins
- **Password reset security**: Time-limited, one-time use tokens

## API Features

### Request/Response Handling
- **Automatic validation**: Pydantic validates all request bodies
- **Custom error messages**: User-friendly validation error messages
- **Error formatting**: Structured error responses
- **Response models**: Type-safe response schemas

### Documentation
- **OpenAPI/Swagger**: Automatic API documentation at `/api/v1/docs`
- **Endpoint descriptions**: Detailed docstrings for all endpoints
- **Request/response examples**: Auto-generated examples
- **Interactive testing**: Test endpoints directly from Swagger UI

### Performance
- **Connection pooling**: SQLAlchemy connection pool (size: 5, overflow: 10)
- **Database indexing**: Strategic indexes on frequently queried fields
- **Query optimization**: Efficient queries with proper filtering
- **Lazy loading**: Relationships loaded only when needed

## Configuration

### Environment Variables
- `PROJECT_NAME` - Application name
- `VERSION` - Application version
- `API_V1_STR` - API version prefix (default: `/api/v1`)
- `BACKEND_CORS_ORIGINS` - CORS allowed origins
- `SECRET_KEY` - JWT secret key (change in production!)
- `ALGORITHM` - JWT algorithm (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Token expiry (default: 30)
- `POSTGRES_USER` - Database user
- `POSTGRES_PASSWORD` - Database password
- `POSTGRES_DB` - Database name
- `POSTGRES_HOST` - Database host
- `POSTGRES_PORT` - Database port

### Settings Management
- **Pydantic Settings**: Type-safe configuration management
- **Environment file**: `.env` file support
- **Default values**: Sensible defaults for development
- **CORS parsing**: Flexible CORS origin parsing (string/list/JSON)

## Dependencies & Utilities

### Core Dependencies
- **get_db()**: Database session dependency (auto-close, rollback on error)
- **get_current_user()**: Extract user from JWT token
- **get_current_active_user()**: Ensure user is active
- **get_current_company_id()**: Get user's company_id for tenant isolation
- **require_role()**: Role-based access control dependency factory

### Custom Types
- **EnumType**: Custom SQLAlchemy type for enum handling
- **Automatic conversion**: Converts between Python enums and database strings
- **Graceful handling**: Handles invalid enum values during migrations

## Error Handling

### Custom Exception Handlers
- **Validation errors**: Custom handler for request validation errors
- **User-friendly messages**: Clear, actionable error messages
- **Structured responses**: Consistent error response format
- **Field-level errors**: Detailed field-specific error information

### Error Types
- **401 Unauthorized**: Invalid or missing authentication
- **403 Forbidden**: Insufficient permissions or inactive account
- **404 Not Found**: Resource not found or not in user's company
- **422 Unprocessable Entity**: Validation errors
- **500 Internal Server Error**: Server errors with rollback

## Best Practices

### Code Organization
- **Separation of concerns**: Clear separation between routes, models, schemas
- **Dependency injection**: FastAPI dependencies for reusable logic
- **Type hints**: Full type annotations throughout codebase
- **Docstrings**: Comprehensive documentation for all functions

### Database Practices
- **Transactions**: Proper transaction management with rollback
- **Soft deletes**: Use `is_active` flags instead of hard deletes
- **Cascade deletes**: Proper cascade configuration for relationships
- **Indexes**: Strategic indexing for performance

### Security Practices
- **Never expose passwords**: Passwords never returned in responses
- **Token security**: Secure token generation and validation
- **Input validation**: All inputs validated before processing
- **Tenant isolation**: Always filter by company_id

## API Endpoints Summary

### Authentication
- `POST /api/v1/auth/token` - Login (OAuth2 Password Flow)

### Companies
- `POST /api/v1/companies/signup` - Company registration

### Users
- `POST /api/v1/users/create` - Create user (Admin only)
- `GET /api/v1/users/` - List users
- `GET /api/v1/users/me` - Current user info
- `PUT /api/v1/users/{user_id}/deactivate` - Deactivate user (Admin only)

### Employees
- `POST /api/v1/employees` - Create employee (Admin/HR only)
- `GET /api/v1/employees` - List employees
- `GET /api/v1/employees/{employee_id}` - Get employee
- `PUT /api/v1/employees/{employee_id}` - Update employee (Admin/HR only)
- `DELETE /api/v1/employees/{employee_id}` - Delete employee (Admin only)

### Expenses
- `POST /api/v1/expenses` - Submit expense
- `GET /api/v1/expenses` - List expenses
- `GET /api/v1/expenses/{expense_id}` - Get expense
- `PATCH /api/v1/expenses/{expense_id}` - Update expense
- `POST /api/v1/expenses/{expense_id}/approve` - Approve expense (Admin/HR only)
- `POST /api/v1/expenses/{expense_id}/reject` - Reject expense (Admin/HR only)
- `DELETE /api/v1/expenses/{expense_id}` - Delete expense

### Assets
- `POST /api/v1/assets` - Create asset (Admin/HR only)
- `GET /api/v1/assets` - List assets
- `GET /api/v1/assets/{asset_id}` - Get asset
- `PATCH /api/v1/assets/{asset_id}` - Update asset (Admin/HR only)
- `POST /api/v1/assets/{asset_id}/assign` - Assign asset (Admin/HR only)
- `POST /api/v1/assets/{asset_id}/unassign` - Unassign asset (Admin/HR only)
- `DELETE /api/v1/assets/{asset_id}` - Delete asset (Admin only)

### Password Reset
- `POST /api/v1/auth/forgot-password` - Request reset token
- `POST /api/v1/auth/reset-password` - Reset password

### Health Check
- `GET /health` - Health check endpoint

## Future Enhancements

### Planned Features
- [ ] File upload for expense receipts
- [ ] Email notifications for expense approvals/rejections
- [ ] Advanced reporting and analytics
- [ ] Bulk operations (bulk import, bulk update)
- [ ] Audit logging
- [ ] Two-factor authentication (2FA)
- [ ] API rate limiting
- [ ] Webhook support
- [ ] Export functionality (CSV, PDF)
- [ ] Advanced search with full-text search
- [ ] Real-time notifications (WebSocket)
- [ ] Mobile API endpoints
- [ ] GraphQL API option

## Development Notes

### Database Migrations
- Managed with Alembic
- Migration files in `alembic/versions/`
- Run migrations: `alembic upgrade head`
- Create migration: `alembic revision --autogenerate -m "description"`

### Testing
- Unit tests recommended for all endpoints
- Integration tests for workflows
- Test data creation script available in `scripts/create_test_data.py`

### Deployment
- Docker support with `Dockerfile` and `docker-compose.yml`
- Nginx reverse proxy configuration
- Production-ready with proper error handling
- Environment-based configuration

## License

MIT License - See LICENSE file for details

