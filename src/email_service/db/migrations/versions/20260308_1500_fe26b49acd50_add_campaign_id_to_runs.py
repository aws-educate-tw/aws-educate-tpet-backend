"""add_campaign_id_to_runs

Revision ID: fe26b49acd50
Revises: e0b7bc7977c4
Create Date: 2026-03-08 15:00:12.667096

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "fe26b49acd50"
down_revision = "e0b7bc7977c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create campaign_id table
    op.add_column(
        "runs", sa.Column("campaign_id", sa.String(length=255), nullable=True)
    )


def downgrade() -> None:
    # Drop campaign_id table
    op.drop_column("runs", "campaign_id")
