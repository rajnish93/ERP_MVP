#!/usr/bin/env python3
"""
Script to check if there are any pending migration changes.
Exits with code 0 if changes exist, 1 if no changes.
"""
import sys
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

# Import models to register with Base.metadata
from app.core.database import Base
from app.core.config import settings
from app.db.models import Company, User, Employee  # noqa: F401

def check_for_changes():
    """Check if there are any schema changes that need migration"""
    alembic_cfg = Config("alembic.ini")
    
    # Create engine and check for differences
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        script = ScriptDirectory.from_config(alembic_cfg)
        
        # Get current database revision
        current_rev = context.get_current_revision()
        head_rev = script.get_current_head()
        
        # If database is not at head, there are pending migrations
        if current_rev != head_rev:
            print(f"Database at {current_rev}, head is {head_rev}")
            return True
        
        # Check for autogenerate changes
        with context.begin_transaction():
            diff = context._autogen_context(script, target_metadata=Base.metadata)
            if diff:
                # There are changes
                return True
    
    return False

if __name__ == "__main__":
    try:
        has_changes = check_for_changes()
        if has_changes:
            sys.exit(0)  # Changes exist
        else:
            print("No migration changes detected")
            sys.exit(1)  # No changes
    except Exception as e:
        print(f"Error checking for changes: {e}", file=sys.stderr)
        sys.exit(2)

