"""add recipient_name to emails table

Revision ID: 001
Revises:
Create Date: 2026-01-25 17:07:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add recipient_name column to EMAILS table.

    This column stores a snapshot of the recipient's name at email creation time,
    extracted from template variables ({{Name}} or {{姓名}}).
    """
    op.add_column(
        "emails", sa.Column("recipient_name", sa.String(length=255), nullable=True)
    )


def downgrade() -> None:
    """Remove recipient_name column from EMAILS table."""
    op.drop_column("emails", "recipient_name")
