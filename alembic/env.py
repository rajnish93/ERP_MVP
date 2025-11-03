from logging.config import fileConfig

from sqlalchemy import engine_from_config, text, String
from sqlalchemy import pool

from alembic import context
from alembic.autogenerate import compare_metadata
from alembic.operations.ops import MigrationScript

# Import your models and Base
from app.core.database import Base
from app.core.config import settings
from app.core.types import EnumType
# Import all models so Alembic can detect them
from app.db.models import Company, User, Employee  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the database URL from settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


# Enum types are now stored as strings with check constraints
# No need for PostgreSQL enum type management


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # Enum types are now stored as strings with check constraints
    # No enum type management needed
    with connectable.connect() as connection:
        def process_revision_directives(context, revision, directives):
            """
            Prevent creating empty migration files when using --autogenerate,
            but allow empty migrations when created manually (for data migrations, etc.)
            """
            # Only skip empty migrations when using --autogenerate flag
            # Manual migrations (without --autogenerate) should always be created
            is_autogenerate = False
            if config.cmd_opts:
                # Check if --autogenerate flag is present
                cmd_args = getattr(config.cmd_opts, 'autogenerate', False)
                if cmd_args or (hasattr(config.cmd_opts, 'cmd') and 'autogenerate' in str(config.cmd_opts)):
                    is_autogenerate = True
            
            # Only prevent empty migrations when autogenerating
            if is_autogenerate and directives:
                script = directives[0]
                # Check if upgrade_ops is empty (no changes detected)
                if hasattr(script, 'upgrade_ops') and script.upgrade_ops.is_empty():
                    # Clear directives to prevent file creation
                    directives[:] = []
                    print("INFO: No schema changes detected. Skipping migration file creation.")
                    print("INFO: To create an empty migration manually, use: alembic revision -m 'message'")
                    return

        def render_item(type_, obj, autogen_context):
            """
            Custom render function to convert EnumType to String in migrations.
            This ensures migration files use sa.String() instead of app.core.types.EnumType or VARCHAR
            """
            # Only handle column type rendering
            if type_ == "type":
                # If this is an EnumType, render it as sa.String()
                if isinstance(obj, EnumType):
                    # Get the length from the EnumType instance
                    length = getattr(obj, 'length', 50)
                    # Return a string representation that will be written to the migration file
                    # This ensures it's rendered as sa.String() not VARCHAR
                    return f"sa.String(length={length})"
            
            # Return False to use default rendering for other types
            return False

        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            process_revision_directives=process_revision_directives,
            compare_type=True,
            compare_server_default=True,
            render_item=render_item,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

