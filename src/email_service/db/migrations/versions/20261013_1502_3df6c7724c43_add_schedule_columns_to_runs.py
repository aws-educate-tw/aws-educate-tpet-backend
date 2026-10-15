"""add_schedule_columns_to_runs

Revision ID: 3df6c7724c43
Revises: fe26b49acd50
Create Date: 2026-10-13 15:02:28.379227

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3df6c7724c43'
down_revision = 'fe26b49acd50'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add schedule columns and run-level status to RUNS table.

    - status: run state (SCHEDULED / CANCELED / SENDING / SENT / FAILED / ACTIVE).
      Nullable for now so existing writers that do not set it yet keep working;
      it will be made NOT NULL in a follow-up migration.
    - scheduled_at: planned send time, NULL means send immediately
    - dispatched_at: time the run was actually picked up for sending
    - schedule_arn: EventBridge schedule ARN, NULL for immediate runs
    """
    op.add_column("runs", sa.Column("status", sa.String(length=50), nullable=True))
    op.add_column(
        "runs", sa.Column("scheduled_at", sa.TIMESTAMP(timezone=True), nullable=True)
    )
    op.add_column(
        "runs", sa.Column("dispatched_at", sa.TIMESTAMP(timezone=True), nullable=True)
    )
    op.add_column(
        "runs", sa.Column("schedule_arn", sa.String(length=255), nullable=True)
    )

    op.execute(
        """
        UPDATE runs
        SET status = CASE
            WHEN run_type = 'WEBHOOK' THEN 'ACTIVE'
            WHEN failed_email_count > 0 THEN 'FAILED'
            ELSE 'SENT'
        END
        WHERE status IS NULL
        """
    )

    op.create_index("idx_runs_status", "runs", ["status"])


def downgrade() -> None:
    """Remove schedule columns and status from RUNS table."""
    op.drop_index("idx_runs_status", "runs")
    op.drop_column("runs", "schedule_arn")
    op.drop_column("runs", "dispatched_at")
    op.drop_column("runs", "scheduled_at")
    op.drop_column("runs", "status")