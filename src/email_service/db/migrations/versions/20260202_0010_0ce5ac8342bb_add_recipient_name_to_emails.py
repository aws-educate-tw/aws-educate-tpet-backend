"""add_recipient_name_to_emails

Revision ID: 0ce5ac8342bb
Revises:
Create Date: 2026-02-02 00:10:00.204648

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0ce5ac8342bb"
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
