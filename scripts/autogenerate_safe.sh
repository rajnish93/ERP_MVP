#!/bin/bash
# Safe autogenerate script that only creates migrations if there are changes

set -e

# Check if there are changes first
if uv run python scripts/check_migration_changes.py 2>/dev/null; then
    echo "Schema changes detected. Creating migration..."
    uv run alembic revision --autogenerate -m "$1"
else
    echo "No schema changes detected. Skipping migration creation."
    exit 0
fi

