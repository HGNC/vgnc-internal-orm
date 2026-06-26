import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from db_common import DeclarativeBase

# Add the project root to sys.path to ensure imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import ALL models to ensure they are registered into db_common.DeclarativeBase.metadata
# Since we've migrated to db_common, all models inherit from db_common.DeclarativeBase
# and are automatically registered in the shared metadata registry
from vgnc_internal_orm.models import (
    associations, assembly, chromosomes, genefam, species, supporting
)
# Note: orthology module excluded temporarily due to foreign key reference issues
# It uses fictional schema that doesn't match the real database

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use db_common.DeclarativeBase.metadata directly
# After T2 migration, all models inherit from db_common.DeclarativeBase,
# so the shared metadata registry contains all vgnc tables
target_metadata = DeclarativeBase.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# Support reading database URL from environment variable
# This allows for more flexible configuration in different environments
def get_database_url():
    """Get database URL from environment or config file."""
    # First try environment variable
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return database_url

    # Fall back to config file
    return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_database_url()
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
    # Override the database URL with our function that supports environment variables
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Add compare type and compare server defaults for more accurate autogeneration
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()