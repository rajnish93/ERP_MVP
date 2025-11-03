# Database Migrations with Alembic

This project uses Alembic for database schema management and migrations.

## Why Alembic?

- **Version Control**: Track all database schema changes
- **Collaboration**: Team members can apply the same migrations
- **Production Safety**: Controlled schema updates without data loss
- **Rollback**: Ability to revert schema changes if needed
- **Best Practice**: Industry standard for SQLAlchemy projects

## Initial Setup

1. **Create initial migration** (already done):
   ```bash
   alembic revision --autogenerate -m "Initial migration"
   ```

2. **Apply migrations**:
   ```bash
   alembic upgrade head
   ```

## Working with Migrations

### Create a new migration after model changes

```bash
# After modifying models in app/db/models/
alembic revision --autogenerate -m "Add new field to user table"
```

### Apply migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific revision
alembic upgrade <revision_id>
```

### Rollback migrations

```bash
# Rollback one step
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>
```

### Check current migration status

```bash
alembic current
alembic history
```

## Docker Integration

Migrations run automatically when the container starts:
1. Wait for PostgreSQL to be ready
2. Run `alembic upgrade head`
3. Start the FastAPI application

## Migration Files Location

- Migration files: `alembic/versions/`
- Configuration: `alembic.ini`
- Environment setup: `alembic/env.py`

## Important Notes

- Always review auto-generated migrations before applying
- Test migrations on development database first
- Never edit existing migration files after they've been applied
- Create new migrations for schema changes instead

