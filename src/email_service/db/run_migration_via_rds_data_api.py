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
    # Upgrade to latest version
    uv run src/email_service/db/run_migration_via_rds_data_api.py upgrade

    # Upgrade to specific revision
    uv run src/email_service/db/run_migration_via_rds_data_api.py upgrade abc123

    # Downgrade by one revision
    uv run src/email_service/db/run_migration_via_rds_data_api.py downgrade -1

    # Downgrade to specific revision
    uv run src/email_service/db/run_migration_via_rds_data_api.py downgrade abc123

    # Downgrade to base (undo all migrations)
    uv run src/email_service/db/run_migration_via_rds_data_api.py downgrade base

    # Show current version
    uv run src/email_service/db/run_migration_via_rds_data_api.py current

    # Show migration history
    uv run src/email_service/db/run_migration_via_rds_data_api.py history

Environment Variables Required:
    - AWS_REGION: AWS region (e.g., us-east-1)
    - DB_CLUSTER_ARN: RDS cluster ARN (also used as aurora_cluster_arn)
    - DB_SECRET_ARN: Secrets Manager secret ARN for DB credentials
    - DB_NAME: Database name (default: email_service_db)
"""

import argparse
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


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Alembic database migrations using AWS RDS Data API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s upgrade              # Upgrade to latest version (head)
  %(prog)s upgrade abc123       # Upgrade to specific revision
  %(prog)s downgrade -1         # Downgrade by one revision
  %(prog)s downgrade abc123     # Downgrade to specific revision
  %(prog)s downgrade base       # Downgrade to base (undo all migrations)
  %(prog)s current              # Show current version
  %(prog)s history              # Show migration history
        """,
    )
    parser.add_argument(
        "action",
        choices=["upgrade", "downgrade", "current", "history"],
        help="Migration action to perform",
    )
    parser.add_argument(
        "revision",
        nargs="?",
        default=None,
        help="Target revision (default: 'head' for upgrade, '-1' for downgrade)",
    )
    return parser.parse_args()


def main():
    """Main execution function."""
    args = parse_args()

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
    print(f"  Action: {args.action}")
    if args.revision:
        print(f"  Revision: {args.revision}")
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
        # Show current version first
        print("Current migration version:")
        try:
            command.current(alembic_cfg, verbose=True)
        except Exception as e:
            print(f"  (No version table yet or error: {e})")
        print()

        # Execute the requested action
        if args.action == "current":
            # Already shown above, nothing more to do
            pass

        elif args.action == "history":
            print("Migration history:")
            command.history(alembic_cfg, verbose=True)

        elif args.action == "upgrade":
            revision = args.revision or "head"
            print(f"Running upgrade to: {revision}")
            command.upgrade(alembic_cfg, revision)
            print()
            print("New migration version:")
            command.current(alembic_cfg, verbose=True)

        elif args.action == "downgrade":
            revision = args.revision or "-1"
            print(f"Running downgrade to: {revision}")
            command.downgrade(alembic_cfg, revision)
            print()
            print("New migration version:")
            command.current(alembic_cfg, verbose=True)

        print("\n" + "=" * 80)
        print(f"Action '{args.action}' completed successfully!")
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
