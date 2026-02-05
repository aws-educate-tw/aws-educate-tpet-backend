"""Alembic environment configuration for Email Service.

This environment supports two connection modes:
1. Standard PostgreSQL connection via DATABASE_URL (for local/Docker testing)
2. Aurora Data API connection via sqlalchemy-aurora-data-api (for AWS RDS)

The connection mode is automatically determined by the DATABASE_URL format:
- postgresql+auroradataapi://... -> Uses RDS Data API
- postgresql://... -> Uses standard PostgreSQL driver
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None


def get_url() -> str:
    """Get database URL from environment variables or config.

    Priority:
    1. Environment variable DATABASE_URL
    2. Config option sqlalchemy.url
    3. Default local development URL
    """
    # Check environment variable first
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    # Check if config has the URL set programmatically
    url = config.get_main_option("sqlalchemy.url")
    if url:
        return url

    # Default for local development
    return "postgresql://postgres:postgres@localhost:5432/email_service_db"


def get_connect_args() -> dict:
    """Get connection arguments for the SQLAlchemy engine.

    For Aurora Data API connections, this returns the cluster and secret ARNs.
    For standard connections, this returns an empty dict.
    """
    url = get_url()

    # Check if using Aurora Data API
    if "auroradataapi" in url:
        cluster_arn = os.getenv("AURORA_CLUSTER_ARN")
        secret_arn = os.getenv("AURORA_SECRET_ARN")

        if cluster_arn and secret_arn:
            return {
                "aurora_cluster_arn": cluster_arn,
                "secret_arn": secret_arn,
            }

    return {}


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_url()
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

    This function supports both:
    - Standard PostgreSQL connections
    - Aurora Data API connections (via sqlalchemy-aurora-data-api)
    """
    url = get_url()
    connect_args = get_connect_args()

    # Create engine with connect_args for Aurora Data API
    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
