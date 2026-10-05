"""add_participant_table_and_update_runs_for_rsvp

Revision ID: e0b7bc7977c4
Revises: 0ce5ac8342bb
Create Date: 2026-02-10 14:14:47.779880

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e0b7bc7977c4"
down_revision = "0ce5ac8342bb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add RSVP fields to RUNS table and create Participant table."""

    # 1. Modify RUNS table - Add RSVP event related fields
    op.add_column("runs", sa.Column("event_name", sa.String(255), nullable=True))
    op.add_column("runs", sa.Column("event_location", sa.String(500), nullable=True))
    op.add_column(
        "runs", sa.Column("event_time", sa.TIMESTAMP(timezone=True), nullable=True)
    )
    op.add_column(
        "runs",
        sa.Column("registration_deadline", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "runs",
        sa.Column(
            "participation_num", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column("runs", sa.Column("max_participants", sa.Integer(), nullable=True))

    # 2. Create Participant table
    op.create_table(
        "participant",
        sa.Column("participant_id", sa.String(255), primary_key=True),
        sa.Column("run_id", sa.String(255), nullable=False),
        sa.Column("email_id", sa.String(255), nullable=False),
        sa.Column(
            "rsvp_status", sa.String(50), nullable=False, server_default="PENDING"
        ),
        sa.Column("rsvp_responded_at", sa.TIMESTAMP(timezone=True), nullable=True),
        # Foreign key constraints
        sa.ForeignKeyConstraint(
            ["run_id"], ["runs.run_id"], name="fk_participant_run", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["email_id"],
            ["emails.email_id"],
            name="fk_participant_email",
            ondelete="CASCADE",
        ),
    )

    # 3. Create index for faster queries
    op.create_index("idx_participant_run_id", "participant", ["run_id"])


def downgrade() -> None:
    """Remove Participant table and RSVP fields from RUNS."""

    # 1. Drop index
    op.drop_index("idx_participant_run_id", "participant")

    # 2. Drop Participant table
    op.drop_table("participant")

    # 3. Drop newly added fields from RUNS table
    op.drop_column("runs", "max_participants")
    op.drop_column("runs", "participation_num")
    op.drop_column("runs", "registration_deadline")
    op.drop_column("runs", "event_time")
    op.drop_column("runs", "event_location")
    op.drop_column("runs", "event_name")
