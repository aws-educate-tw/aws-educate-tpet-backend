#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "alembic==1.18.3",
#     "sqlalchemy==2.0.46",
#     "sqlalchemy-aurora-data-api==0.5.0",
#     "boto3==1.42.39",
# ]
# ///
"""
Run Alembic database migrations using AWS RDS Data API.

This script runs Alembic migrations through the RDS Data API using the
sqlalchemy-aurora-data-api dialect, which tunnels SQL over HTTP.

Usage:
    uv run src/email_service/db/run_migration_via_rds_data_api.py

Environment Variables Required:
    - AWS_REGION: AWS region (e.g., us-east-1)
    - DB_CLUSTER_ARN: RDS cluster ARN (also used as aurora_cluster_arn)
    - DB_SECRET_ARN: Secrets Manager secret ARN for DB credentials
    - DB_NAME: Database name (default: email_service_db)
"""

import os
import sys
from pathlib import Path


def get_required_env(var_name: str, default: str | None = None) -> str:
    """Get required environment variable or exit."""
    value = os.getenv(var_name, default)
    if not value:
        print(f"ERROR: Environment variable {var_name} is required.")
        sys.exit(1)
    return value


def main():
    """Main execution function."""
    print("=" * 80)
    print("Alembic Migration via RDS Data API")
    print("=" * 80)

    # Get configuration from environment
    aws_region = get_required_env("AWS_REGION", "us-west-2")
    cluster_arn = get_required_env("DB_CLUSTER_ARN")
    secret_arn = get_required_env("DB_SECRET_ARN")
    database = get_required_env("DB_NAME", "email_service_db")

    print("\nConfiguration:")
    print(f"  AWS Region: {aws_region}")
    print(f"  Cluster ARN: {cluster_arn}")
    print(f"  Secret ARN: {secret_arn}")
    print(f"  Database: {database}")
    print()

    # Set environment variables for aurora_data_api
    # The package reads these if not provided in connect_args
    os.environ["AURORA_CLUSTER_ARN"] = cluster_arn
    os.environ["AURORA_SECRET_ARN"] = secret_arn
    os.environ["AWS_DEFAULT_REGION"] = aws_region

    # Import after setting env vars
    from alembic import command
    from alembic.config import Config

    # Create the database URL
    # Format: postgresql+auroradataapi://:@/database_name
    # The ARNs are passed via connect_args or environment variables
    database_url = f"postgresql+auroradataapi://:@/{database}"

    # Find the migrations directory
    script_dir = Path(__file__).parent
    migrations_dir = script_dir / "migrations"
    alembic_ini = migrations_dir / "alembic.ini"

    if not alembic_ini.exists():
        print(f"ERROR: alembic.ini not found at {alembic_ini}")
        sys.exit(1)

    print(f"Migrations directory: {migrations_dir}")
    print(f"Alembic config: {alembic_ini}")
    print()

    # Create Alembic config
    alembic_cfg = Config(str(alembic_ini))
    alembic_cfg.set_main_option("script_location", str(migrations_dir))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)

    # Also set the connect_args for the engine
    # We need to configure env.py to use these
    os.environ["DATABASE_URL"] = database_url

    try:
        # Step 1: Show current version
        print("Step 1: Checking current migration version...")
        try:
            command.current(alembic_cfg, verbose=True)
        except Exception as e:
            print(f"  (No version table yet or error: {e})")
        print()

        # Step 2: Run upgrade to head
        print("Step 2: Running migrations (upgrade to head)...")
        command.upgrade(alembic_cfg, "head")
        print()

        # Step 3: Show new version
        print("Step 3: Verifying migration version...")
        command.current(alembic_cfg, verbose=True)

        print("\n" + "=" * 80)
        print("Migration completed successfully!")
        print("=" * 80)

    except Exception as e:
        print("\n" + "=" * 80)
        print(f"Migration failed: {e}")
        import traceback

        traceback.print_exc()
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
