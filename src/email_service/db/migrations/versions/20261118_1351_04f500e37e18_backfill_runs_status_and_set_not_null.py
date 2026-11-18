"""backfill_runs_status_and_set_not_null

Revision ID: 04f500e37e18
Revises: 3df6c7724c43
Create Date: 2026-11-18 13:51:15.386555

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '04f500e37e18'
down_revision = '3df6c7724c43'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Backfill RUNS.status for rows still NULL, then make it NOT NULL.

    Rows created after SCRUM-674 but before the writers set status were left NULL.
    """
    # Step 1: Backfill status for rows that are still NULL
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

    # Step 2: Make status non-nullable
    op.alter_column(
        "runs", "status", existing_type=sa.String(length=50), nullable=False
    )


def downgrade() -> None:
    """Make RUNS.status nullable again (backfilled values are kept)."""
    op.alter_column(
        "runs", "status", existing_type=sa.String(length=50), nullable=True
    )