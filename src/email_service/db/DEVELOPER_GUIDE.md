# Database Migration Developer Guide

This guide explains the complete workflow for adding new database columns to the Email Service, from PM requirements to production deployment.

---

## Workflow Overview

```text
PM Requirements → Engineer Assignment → Local Development → PR & Review → CI/CD Deployment
```

---

## Step 1: PM Opens Requirement & Engineer Opens DB Migration Ticket

### Example Scenario

**PM Request:**
> "The exported email records must include the recipient name stored in the emails table."

**PM Creates Issue/Ticket:**

- Title: `Include recipient name in exported email records`
- Description: Business justification and expected behavior
- Acceptance Criteria: What the field should contain

**Engineer Action:**

- The engineer must create a Jira ticket specifically for the DB migration and block the PM ticket:
  - Title: `Add recipient_name column to emails table`

---

## Step 2: Engineer Receives Assignment

### Before Starting

1. **Read the requirement** - Understand what column is needed
2. **Check existing schema** - Review `src/email_service/db/schema/init-schema.sql`
3. **Plan the migration** - Determine column type, nullable, default value

### Key Questions to Ask

| Question | Why It Matters |
|----------|----------------|
| Is it nullable? | Existing rows need a value or NULL |
| What's the data type? | VARCHAR(255), TEXT, INTEGER, etc. |
| Any default value? | For existing rows |
| Any indexes needed? | For query performance |

---

## Step 3: Create the Migration

### 3.1 Navigate to migrations directory

```bash
cd src/email_service/db/migrations
```

### 3.2 Create a new migration file

Use Alembic to generate the migration file automatically:

```bash
# Generate new migration file (Alembic will auto-generate revision ID and filename)
uvx alembic revision -m "add_recipient_name_to_emails"
```

This creates a file like `20260202_0008_416cef268615_add_recipient_name_to_emails.py` with a unique revision ID.

### 3.3 Edit the generated migration script

The generated file will look like this:

```python
"""add_recipient_name_to_emails

Revision ID: 0ce5ac8342bb
Revises:
Create Date: 2026-02-02 00:10:00.204648

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0ce5ac8342bb'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

```

Edit the `upgrade()` and `downgrade()` functions to add/remove the new column:

```python
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
```

### Key Points

| Field | Description |
|-------|-------------|
| `revision` | Unique ID (auto-generated UUID by Alembic) |
| `down_revision` | Previous migration ID (auto-linked by Alembic) |
| `upgrade()` | Code to apply the migration |
| `downgrade()` | Code to reverse the migration |

---

## Step 4: Update init-schema.sql

**Why?** New environments (preview, new dev) need the complete schema from scratch.

```bash
vim src/email_service/db/schema/init-schema.sql
```

Add the new column to the `emails` table definition:

```sql
CREATE TABLE IF NOT EXISTS EMAILS (
    email_id VARCHAR(255) PRIMARY KEY,
    run_id VARCHAR(255) NOT NULL,
    -- ... existing columns ...
    recipient_name VARCHAR(255),  -- NEW: Added for recipient name feature
    -- ... rest of columns ...
);
```

---

## Step 5: Test Locally

### Test with local-dev Aurora

```bash
# Wake up Aurora
../../../../scripts/wait_for_aurora_serverless.sh \
  "https://local-dev-email-service-internal-api-tpet.aws-educate.tw/local-dev/email-service/health" \
  30 \
  10

# Set environment variables
export AWS_REGION=us-west-2
export DB_CLUSTER_ARN=$(aws rds describe-db-clusters \
  --db-cluster-identifier local-dev-email-service-tpet-aurora-postgresql-v2 \
  --query 'DBClusters[0].DBClusterArn' --output text)
export DB_SECRET_ARN=$(aws rds describe-db-clusters \
  --db-cluster-identifier local-dev-email-service-tpet-aurora-postgresql-v2 \
  --query 'DBClusters[0].MasterUserSecret.SecretArn' --output text)

# Echo for verification
echo "DB_CLUSTER_ARN: $DB_CLUSTER_ARN"
echo "DB_SECRET_ARN: $DB_SECRET_ARN"

# Run migration (upgrade to latest version)
uv run ../run_migration_via_rds_data_api.py upgrade


# Verify alembic version
aws rds-data execute-statement \
  --resource-arn "$DB_CLUSTER_ARN" \
  --secret-arn "$DB_SECRET_ARN" \
  --database "$DB_NAME" \
  --sql "SELECT * FROM alembic_version;"

# Verify column exists
aws rds-data execute-statement \
  --resource-arn "$DB_CLUSTER_ARN" \
  --secret-arn "$DB_SECRET_ARN" \
  --database "email_service_db" \
  --sql "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'emails' AND column_name = 'recipient_name';"
```

---

## Step 6: Create DB Migration Pull Request

### PR Checklist

- [ ] Migration file created in `src/email_service/db/migrations/versions/`
- [ ] `init-schema.sql` updated with new column
- [ ] Migration tested locally (Docker or local-dev Aurora)

---

## Step 8: CI/CD Pipeline & Merge into dev branch

### What Happens Automatically

1. **PR Created** → Preview environment deployed
2. **Migration Detected** → CI/CD detects changes in `src/email_service/db/migrations`
3. **Approval Required** → GitHub Issue created for manual approval
4. **Approved** → Migration executes via `uv run src/email_service/db/run_migration_via_rds_data_api.py`
5. **PR Merged** → Dev/Prod environments run migration

### Approving Migration

When you see the GitHub Issue:

1. Review the migration files
2. Comment `approve` to approve
3. Or comment `deny` to reject

See example issue: [issue link](https://github.com/aws-educate-tw/aws-educate-tpet-backend/issues/147)

---

## Step 9: Implement Feature Code

After the migration is tested, you may have other Jira ticket that implement the feature code:

1. **Update Lambda handlers** that write to the emails table
2. **Update API responses** if the field is exposed

Example locations:

- `src/email_service/create_email/` - Writing email records
- `src/email_service/list_emails/` - Reading email records

## Step 10: Create PR for Feature Code

1. Create a new branch from `dev`
2. Implement the feature code
3. Create PR and get reviewed
4. Merge to `dev` branch

## Step 11: DONE, Just wait for other engineer release

After merging to `dev`, wait for the next scheduled deployment to `prod` by the engineer responsible for releases.

---

## Common Scenarios

### Adding a New Table

**Example:** Add an `email_attachments` table to store attachment metadata separately.

```python
"""add email_attachments table

Revision ID: 003
Revises: 002
Create Date: 2026-02-01 19:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Create email_attachments table."""
    op.create_table(
        "email_attachments",
        sa.Column("attachment_id", sa.String(255), primary_key=True),
        sa.Column("email_id", sa.String(255), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("content_type", sa.String(100), nullable=True),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["email_id"],
            ["emails.email_id"],
            name="fk_email_attachments_email_id",
            ondelete="CASCADE",
        ),
    )

    # Add indexes for common queries
    op.create_index(
        "idx_email_attachments_email_id",
        "email_attachments",
        ["email_id"],
    )

def downgrade() -> None:
    """Drop email_attachments table."""
    op.drop_index("idx_email_attachments_email_id", "email_attachments")
    op.drop_table("email_attachments")
```

**Remember to update `init-schema.sql`:**

```sql
-- Add to init-schema.sql
CREATE TABLE IF NOT EXISTS EMAIL_ATTACHMENTS (
    attachment_id VARCHAR(255) PRIMARY KEY,
    email_id VARCHAR(255) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_size INTEGER,
    content_type VARCHAR(100),
    s3_key VARCHAR(500) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,

    CONSTRAINT fk_email_attachments_email_id
        FOREIGN KEY (email_id)
        REFERENCES EMAILS(email_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_email_attachments_email_id
    ON EMAIL_ATTACHMENTS(email_id);
```

### Adding a Non-Nullable Column

```python
def upgrade() -> None:
    # Step 1: Add column as nullable
    op.add_column("emails", sa.Column("priority", sa.Integer(), nullable=True))

    # Step 2: Fill existing rows with default value
    op.execute("UPDATE emails SET priority = 0 WHERE priority IS NULL")

    # Step 3: Make it non-nullable
    op.alter_column("emails", "priority", nullable=False)
```

### Adding an Index

```python
def upgrade() -> None:
    op.add_column("emails", sa.Column("sender_company", sa.String(255), nullable=True))
    op.create_index("idx_emails_sender_company", "emails", ["sender_company"])

def downgrade() -> None:
    op.drop_index("idx_emails_sender_company", "emails")
    op.drop_column("emails", "sender_company")
```

### Renaming a Column

```python
def upgrade() -> None:
    op.alter_column("emails", "old_name", new_column_name="new_name")

def downgrade() -> None:
    op.alter_column("emails", "new_name", new_column_name="old_name")
```

### Creating a Junction Table (Many-to-Many)

**Example:** Emails can have multiple tags, and tags can belong to multiple emails.

```python
def upgrade() -> None:
    # Create tags table
    op.create_table(
        "email_tags",
        sa.Column("tag_id", sa.String(255), primary_key=True),
        sa.Column("tag_name", sa.String(100), nullable=False, unique=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )

    # Create junction table
    op.create_table(
        "email_tag_mappings",
        sa.Column("email_id", sa.String(255), nullable=False),
        sa.Column("tag_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("email_id", "tag_id"),
        sa.ForeignKeyConstraint(
            ["email_id"], ["emails.email_id"],
            name="fk_email_tag_mappings_email_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"], ["email_tags.tag_id"],
            name="fk_email_tag_mappings_tag_id",
            ondelete="CASCADE",
        ),
    )

    op.create_index("idx_email_tag_mappings_email_id", "email_tag_mappings", ["email_id"])
    op.create_index("idx_email_tag_mappings_tag_id", "email_tag_mappings", ["tag_id"])

def downgrade() -> None:
    op.drop_index("idx_email_tag_mappings_tag_id", "email_tag_mappings")
    op.drop_index("idx_email_tag_mappings_email_id", "email_tag_mappings")
    op.drop_table("email_tag_mappings")
    op.drop_table("email_tags")
```

---

## Troubleshooting

### Migration fails with "column already exists"

The migration is not idempotent. Alembic tracks versions, so this shouldn't happen normally. Check:

1. `alembic_version` table for current version
2. Ensure migration files are chained correctly (`down_revision`)

### Aurora Serverless times out

Run the health check first:

```bash
./scripts/wait_for_aurora_serverless.sh "HEALTH_URL" 30 10
```

### Need to rollback in production

```bash
# Check current version
aws rds-data execute-statement \
  --resource-arn "$DB_CLUSTER_ARN" \
  --secret-arn "$DB_SECRET_ARN" \
  --database "email_service_db" \
  --sql "SELECT * FROM alembic_version;"

# For manual rollback, you'll need to write a rollback script
# or use the downgrade() function locally
```

---

## Environment Summary

| Environment | Region | Method |
|-------------|--------|--------|
| local-dev | us-west-2 | Manual: `uv run src/email_service/db/run_migration_via_rds_data_api.py upgrade` |
| preview | us-west-1 | CI/CD (PR triggers) |
| dev | us-east-1 | CI/CD (dev branch push) |
| prod | ap-northeast-1 | CI/CD (main branch push) |

---

## Quick Reference

```bash
# Create new migration (use Alembic to auto-generate)
cd src/email_service/db/migrations
uvx alembic revision -m "add_your_column_description"

# Test locally with Docker
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/email_service_db"
cd src/email_service/db/migrations
uvx alembic upgrade head

# Test locally with Aurora
uv run src/email_service/db/run_migration_via_rds_data_api.py upgrade      # Upgrade to head
uv run src/email_service/db/run_migration_via_rds_data_api.py downgrade -1 # Downgrade one version
uv run src/email_service/db/run_migration_via_rds_data_api.py current      # Check current version
uv run src/email_service/db/run_migration_via_rds_data_api.py history      # View history

# Check current version
uvx alembic current

# View migration history
uvx alembic history
```

---

## Related Documentation

- [sqlalchemy-aurora-data-api](https://pypi.org/project/sqlalchemy-aurora-data-api/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [Alembic Operations Reference](https://alembic.sqlalchemy.org/en/latest/ops.html)
- [ALembic API Reference](https://alembic.sqlalchemy.org/en/latest/api/index.html)
